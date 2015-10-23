# -*- coding: utf-8 -*-

import logging
import os
import os.path
from datetime import datetime
from io import BytesIO
from urllib.request import pathname2url

import pycurl
import struct
from . import tinytag
from whoosh import index
from whoosh.fields import Schema, ID, TEXT
from whoosh.query import Term
from whoosh.writing import AsyncWriter, IndexingError
from whoosh.analysis import CharsetFilter, StemmingAnalyzer
from whoosh.support.charset import accent_map
from . import pipeline
from .scanner import FTPScanner
from functools import reduce


class Index(object):
    def __init__(self, directory, persist):
        self.log = logging.getLogger('ftpvista.index')

        self._persist = persist
        if not os.path.exists(directory):
            self.log.info('Creating the index in %s' % directory)
            os.mkdir(directory)
            self._idx = index.create_in(directory, schema=self.get_schema())
        else:
            self.log.info('Opening the index in %s' % directory)
            self._idx = index.open_dir(directory)

        self._searcher = self._idx.searcher()
        self._writer = None
        self.open_writer()
        self._last_optimization = None

    def open_writer(self):
        # self._writer = BufferedWriter(self._idx, 120, 4000)
        self._writer = AsyncWriter(self._idx)

    def get_schema(self):
        analyzer = StemmingAnalyzer('([a-zA-Z0-9])+')
        my_analyzer = analyzer | CharsetFilter(accent_map)
        return Schema(
            server_id=ID(stored=True),
            has_id=ID(),
            path=TEXT(analyzer=my_analyzer, stored=True),
            name=TEXT(analyzer=my_analyzer, stored=True),
            ext=TEXT(analyzer=my_analyzer, stored=True),
            size=ID(stored=True),
            mtime=ID(stored=True, sortable=True),
            audio_album=TEXT(analyzer=my_analyzer, stored=True),
            audio_artist=TEXT(analyzer=my_analyzer, stored=True),
            audio_title=TEXT(analyzer=my_analyzer, stored=True),
            audio_track=ID(stored=True),
            audio_year=ID(stored=True)
        )

    def delete_all_docs(self, server):
        self.open_writer()
        self._writer.delete_by_term('server_id', str(server.get_server_id()))
        self._writer.commit()
        self.log.info('All documents of server %s deleted' % server.get_ip_addr())

    def incremental_server_update(self, server_id, current_files):
        """Prepares to incrementaly update the documents for the given server.

        server_id      -- Id of the server to update.
        current_files  -- a list of (path, size, mtime) tuples for each files
                          currently on the server.

        Delete all the outdated files from the index and returns a list
        of files needing to be reindexed.
        """

        def delete_doc(writer, serverid, path):
            writer.delete_by_query(Term('server_id', str(serverid)) & Term('path', path))

        # Build a {path => (size, mtime)} mapping for quick lookups
        to_index = {}
        for path, size, mtime in current_files:
            to_index[path] = (size, mtime)

        results = self._searcher.documents(server_id=str(server_id))
        if results:
            for fields in results:
                indexed_path = fields['path']

                if indexed_path not in to_index:
                    # This file was deleted from the server since it was indexed
                    delete_doc(self._writer, server_id, indexed_path)
                    self.log.debug("%s has been removed" % indexed_path)
                else:
                    size, mtime = to_index[indexed_path]
                    try:
                        if mtime > datetime.strptime(fields['mtime'], '%Y-%m-%d %H:%M:%S'):
                            # This file has been modified since it was indexed
                            delete_doc(self._writer, server_id, indexed_path)
                        else:
                            # up to date, no need to reindex
                            del to_index[indexed_path]
                    except ValueError:
                        delete_doc(self._writer, server_id, indexed_path)

        # return the remaining files
        return [(path, xsize, xmtime) for (path, (xsize, xmtime)) in to_index.items()]

    def add_document(self, server_id, name, path, size, mtime,
                     audio_album=None, audio_artist=None,
                     audio_title=None, audio_year=None):
        """Add a document with the specified fields in the index.

        Changes need to be commited.

        """

        # passing the optional arguments is quite a mess
        # let's build a dict for that purpose

        _, ext = os.path.splitext(name)
        ext = ext.lstrip('.')

        kwargs = {'server_id': server_id,
                  'name': name,
                  'ext': ext,
                  'path': path,
                  'size': size,
                  'mtime': mtime,
                  'has_id': 'a'}

        # Add the optional args
        if audio_album is not None:
            kwargs['audio_album'] = audio_album

        if audio_artist is not None:
            kwargs['audio_artist'] = audio_artist

        if audio_title is not None:
            kwargs['audio_title'] = audio_title

        if audio_year is not None:
            kwargs['audio_year'] = audio_year

        try:
            self._writer.add_document(**kwargs)
        except IndexingError:
            self.open_writer()
            self._writer.add_document(**kwargs)

    def commit(self, optimize=False):
        """ Commit the changes in the index and optimize it """
        self.log.info(' -- Begin of Commit -- ')
        try:
            self._writer.commit(optimize=optimize)
        except IndexingError:
            self.open_writer()
            self._writer.commit(optimize=optimize)
        self.log.info('Index commited')

        self._searcher = self._idx.searcher()
        self.log.info(' -- End of Commit -- ')

    def close(self):
        self.log.info(' -- Closing writer and index -- ')
        # self._writer.close()
        """ Close the index """
        self._idx.close()


class FileIndexerContext(pipeline.Context):
    """ A pipeline Context object to store the informations about a file"""
    def __init__(self, file_path, size, mtime):
        self._path = file_path
        self._size = size
        self._mtime = mtime
        self._extra_data = {}

    def get_path(self):
        return self._path

    def get_size(self):
        return self._size

    def get_mtime(self):
        return self._mtime

    def set_extra_data(self, key, value):
        self._extra_data[key] = value

    def get_extra_data(self):
        return self._extra_data


class FetchID3TagsStage(pipeline.Stage):
    """Pipeline stage to find the ID3 tags of audio files."""

    def __init__(self, server_addr, persist=None, extensions=['mp3']):
        """
        :Parameters:
            -`server_addr`: the server IP address
            -`extensions`: list of file extensions for which to try to get tags
        """
        self.log = logging.getLogger('ftpvista.pipe.id3.%s' % server_addr.replace('.', '_'))
        self._server_addr = server_addr
        self._extensions = extensions
        self._persist = persist
        self._buffer = BytesIO()
        self._curl = pycurl.Curl()

    def _fetch_range(self, arange):
        self._buffer = BytesIO()
        self._curl.setopt(pycurl.WRITEDATA, self._buffer)
        self._curl.setopt(pycurl.RANGE, arange)
        self._curl.perform()

    def _calc_size(self, bytestr, bits_per_byte):
        # length of some mp3 header fields is described
        # by "7-bit-bytes" or sometimes 8-bit bytes...
        ret = 0
        for b in bytestr:
            ret <<= bits_per_byte
            ret += b
        return ret

    def _get_tag_size(self):
        self._fetch_range('0-9')
        header = struct.unpack('3sBBB4B', self._buffer.getbuffer())
        if header[0] in [b'ID3', b'3DI']:
            return self._calc_size(header[4:9], 7)
        return None

    def _fetch_data(self, path, size):
        self._curl.setopt(pycurl.URL, 'ftp://{}{}'.format(self._server_addr, pathname2url(path)))
        try:
            tagsize = self._get_tag_size()
            if tagsize is not None:
                # Tags are at the beginning of the file, so download some more bytes
                self._fetch_range('0-%d' % (tagsize+10))
            else:
                # Tags are perhaps at the end of file then
                self._fetch_range('%d-%d' % (size-10, size))
                tagsize = self._get_tag_size()
                if tagsize is not None:
                    self._fetch_range('%d-%d' % (size-tagsize, size-10))
                else:
                    # See if there is ID3v1
                    self._fetch_range('%d-%d' % (size-128, size))
                    if self._buffer.getvalue()[0:3] == b'TAG':
                        id3v1 = self._buffer.getvalue()
                        self._fetch_range('%d-%d' % (size-138, size-129))
                        tagsize = self._get_tag_size()
                        # See if there is ID3v2 before ID3v1
                        if tagsize is not None:
                            self._fetch_range('%d-%d' % (size-tagsize-148, size-129))
                            self._buffer.write(id3v1)  # Concat ID3v1 to ID3v2
            self._buffer.seek(0)
            return True
        except pycurl.error as e:
            self.log.exception('_fetch_data error', e)
            return False

    def execute(self, context):
        path = context.get_path()
        size = context.get_size()

        # if the file has a candidate extension
        if any([path.lower().endswith(x) for x in self._extensions]):
            self.log.debug('Trying to get ID3 data for %s' % path)

            # Fetch the data from the server
            if self._fetch_data(path, size):
                id3_map = {
                    'album': None,
                    'artist': None,
                    'title': None,
                    'track': None,
                    'year': None,
                    'genre': None
                }
                # Look for tags
                try:
                    tags = tinytag.ID3(self._buffer, None)
                    tags.load(tags=True, duration=False, image=False)
                    for tag in ['album', 'artist', 'title', 'track', 'year', 'genre']:
                        value = getattr(tags, tag)
                        if value is not None:
                            id3_map[tag] = value
                            # add the tag in the context object
                            context.set_extra_data('audio_%s' % tag, value)
                except (UnicodeDecodeError, struct.error) as e:
                    self.log.error('%s : %r' % (path, e))

        # Whatever the outcome of this stage,
        # continue the execution of the pipeline
        return True


class WriteDataStage(pipeline.Stage):
    """ Pipeline stage object that writes the informations in the given index.
    """
    def __init__(self, server_addr, server_id, myindex):
        self.log = logging.getLogger('ftpvista.pipe.write.%s' % server_addr.replace('.', '_'))

        self._server_id = server_id
        self._index = myindex

    def execute(self, context):
        def get_extra(key):
            if key in context.get_extra_data():
                return context.get_extra_data()[key]
            else:
                return None

        path = context.get_path()
        self.log.debug("Adding '%s' in the index", path)
        self._index.add_document(
            server_id=str(self._server_id),
            name=os.path.basename(path),
            path=path,
            size=str(context.get_size()),
            mtime=str(context.get_mtime()),
            audio_artist=get_extra('audio_artist'),
            audio_title=get_extra('audio_title'),
            audio_album=get_extra('audio_album'),
            audio_year=get_extra('audio_year')
        )

        return True


def build_indexer_pipeline(server_id, server_addr, myindex, persist):
    """Helper function to make a basic indexing pipeline"""
    pipe = pipeline.Pipeline()
    pipe.append_stage(FetchID3TagsStage(server_addr, persist))
    pipe.append_stage(WriteDataStage(server_addr, server_id, myindex))

    return pipe


class IndexUpdateCoordinator(object):
    """Coordinate the scanning and indexing of FTP servers."""

    def __init__(self, persist, myindex, min_update_interval, max_depth):
        """Initialize an update coordinator.

        Args:
          persist: an instance of FTPVistaPersist.
          index: an instance of Index
          min_update_interval : a timedelta object, this is the minimum time
                                we want to wait between two updates.
        """
        self.log = logging.getLogger('ftpvista.coordinator')
        self._persist = persist
        self._index = myindex
        self._update_interval = min_update_interval
        self._max_depth = max_depth

    def update_server(self, server_addr):
        """Update the server at the given address if an update is needed."""
        server = self._persist.get_server_by_ip(server_addr)
        if(datetime.now() - server.get_last_scanned()) >= self._update_interval:
            self._do_update(server)

    def _do_update(self, server):
        server_addr = server.get_ip_addr()
        server_id = server.get_server_id()

        # list the files present on the server
        self.log.info('Starting to scan %s (server id : %d)' % (server_addr, server_id))

        scanner = FTPScanner(server_addr)
        files = scanner.scan(max_depth=self._max_depth)
        if files is None:
            self.log.error('Impossible to scan any file, f**k it.')
            return
        if len(files) == 0:
            self.log.info('No file in this FTP, we can skip it.')
            self._persist.rollback()
            return
        # compute the size of all the files found
        size = reduce(lambda total_size, file: total_size + file[1], files, 0)
        self.log.info('Found %d files (%d G) on %s' % (len(files),
                                                       size / (1073741824),  # 1073741824 = 1024 ** 3
                                                       server_addr))

        # Set new informatons about this server in the DB
        server.set_nb_files(len(files))
        server.set_files_size(size)

        # filter out the files already indexed and up to date
        files = self._index.incremental_server_update(server_id, files)

        # sort the files by path, may reduce the CWDs if needed to fetch infos
        # from the FTP server and makes the potential errors append always in
        # the same order.
        files = sorted(files, key=lambda file: file[0])

        # Index the files
        mypipeline = build_indexer_pipeline(server_id, server_addr, self._index, self._persist)
        # Reopen writer
        # self._index.open_writer()
        for path, size, mtime in files:
            ctx = FileIndexerContext(path, size, mtime)
            mypipeline.execute(ctx)

        # Scan done, update the last scanned date
        server.update_last_scanned()

        # commit the changes
        self._persist.save()
        self._index.commit(optimize=True)

        self.log.info('Server %d (%s) updated' % (server_id, server_addr))
