# -*- coding: utf-8 -*-

import logging
import os, os.path
from datetime import datetime, timedelta
from StringIO import StringIO
from urllib import pathname2url

import pycurl
import id3reader
from whoosh import index
from whoosh.fields import Schema, ID, IDLIST, KEYWORD, TEXT
from whoosh.analysis import StandardAnalyzer
from whoosh.query import Term
from whoosh.writing import BatchWriter
from whoosh.analysis import CharsetFilter, StemmingAnalyzer
from whoosh.support.charset import accent_map

import persist as ftpvista_persist
import pipeline
from scanner import FTPScanner
from utils import to_unicode
import nmap_scanner

class Index (object):
    def __init__(self, dir):
        self.log = logging.getLogger('ftpvista.index')

        if not os.path.exists(dir):
            self.log.info('Creating the index in %s' % dir)
            os.mkdir(dir)
            self._idx = index.create_in(dir, schema=self.get_schema())
        else:
            self.log.info('Opening the index in %s' % dir)
            self._idx = index.open_dir(dir)

        self._searcher = self._idx.searcher()
        self._writer = self._idx.writer()#BatchWriter(self._idx, 30, 1000)

    def get_schema(self):
        analyzer = StemmingAnalyzer('([a-zA-Z0-9])+')
        my_analyzer = analyzer | CharsetFilter(accent_map)
        return Schema(server_id=ID(stored=True),
                      path=TEXT(analyzer=my_analyzer, stored=True),
                      name=TEXT(analyzer=my_analyzer, stored=True),
                      size=ID(stored=True),
                      mtime=ID(stored=True),
                      audio_album=TEXT(analyzer=my_analyzer,
                                       stored=True),
                      audio_performer=TEXT(analyzer=my_analyzer,
                                           stored=True),
                      audio_title=TEXT(analyzer=my_analyzer,
                                       stored=True),
                      audio_track=ID(stored=True),
                      audio_year=ID(stored=True)
                      )

    def incremental_server_update(self, server_id, current_files):
        """Prepares to incrementaly update the documents for the given server.

        server_id      -- Id of the server to update.
        current_files  -- a list of (path, size, mtime) tuples for each files
                          currently on the server.

        Delete all the outdated files from the index and returns a list
        of files needing to be reindexed.
        """

        def delete_doc(serverid, path):
            writer = self._idx.writer()
            writer.delete_by_query(Term('server_id', serverid) &
                                      Term('path', path))
            writer.commit()


        # Build a {path => (size, mtime)} mapping for quick lookups
        to_index = {}
        for path, size, mtime in current_files:
            to_index[path] = (size, mtime)

        results = self._searcher.documents(server_id=server_id)
        if results:
            for fields in results:
                indexed_path = fields['path']

                if indexed_path not in to_index:
                    # This file was deleted from the server since it was indexed
                    delete_doc(server_id, indexed_path)
                    self.log.debug("%s has been removed" % indexed_path)
                else:
                    size, mtime = to_index[indexed_path]
                    if mtime > datetime.strptime(fields['mtime'],
                                                 '%Y-%m-%d %H:%M:%S'):
                        # This file has been modified since it was indexed
                        delete_doc(server_id, indexed_path)
                    else:
                        # up to date, no need to reindex
                        del to_index[indexed_path]

        # return the remaining files
        return [(path, size, mtime)
                for (path, (size, mtime)) in to_index.iteritems()]

    def add_document(self, server_id, name, path, size, mtime,
                     audio_album = None, audio_performer = None,
                     audio_title = None, audio_year = None):
        """Add a document with the specified fields in the index.

        Changes need to be commited.

        """

        # passing the optional arguments is quite a mess
        # let's build a dict for that purpose
        kwargs = {'server_id' : server_id,
                  'name' : name,
                  'path' : path,
                  'size' : size,
                  'mtime': mtime}

        #add the optional args
        if audio_album is not None:
            kwargs['audio_album'] = audio_album

        if audio_performer is not None:
            kwargs['audio_performer'] = audio_performer

        if audio_title is not None:
            kwargs['audio_title'] = audio_title

        if audio_year is not None:
            kwargs['audio_year'] = audio_year
            
        self._writer.add_document(**kwargs)


    def commit(self):
        #self._writer = BatchWriter(self._idx, 30, 1000)
        """ Commit the changes in the index and optimize it """
        self.log.info(' -- Begin of Commit -- ')
        self._writer.commit()
        self._idx.optimize()
        self.log.info('Index commited and optimized')
        
        self._writer = self._idx.writer()
        self._searcher = self._idx.searcher()
        self.log.info(' -- End of Commit -- ')
        
    def close(self):
        """ Close the index """
        self._idx.close()

class FileIndexerContext (pipeline.Context):
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


class FetchID3TagsStage (pipeline.Stage):
    """Pipeline stage to find the ID3 tags of audio files."""

    def __init__(self, server_addr, persist, extensions=['mp3'], fetch_size=2048):
        """
        :Parameters:
            -`server_addr`: the server IP address
            -`extensions`: list of file extensions for which to try to get tags
            -`fetch_size`: number of bytes to dowload (the tags are at the
                           begining of the files)
        """
        self.log = logging.getLogger('ftpvista.pipe.id3.%s' % \
                                     server_addr.replace('.', '_'))
        self._server_addr = server_addr
        self._extensions = extensions
        self._persist = persist

        self._buffer = StringIO()
        self._curl = pycurl.Curl()
        self._curl.setopt(pycurl.WRITEFUNCTION, self._data_callback)
        self._curl.setopt(pycurl.RANGE, '0-%d' % (fetch_size-1))

    def _data_callback(self, data):
        self._buffer.write(data)

    def _fetch_data(self, path):
        # Reset the buffer
        self._buffer = StringIO()
        self._curl.setopt(pycurl.URL, str('ftp://%s%s' % (self._server_addr,
                                                           pathname2url(path))))
        try:
            self._curl.perform()
            self._buffer.seek(0)
            return True
        except pycurl.error, e:
            errno, msg = e
            self.log.error('%s : %d %s' % (to_unicode(path), errno, msg))
            return False

    def execute(self, context):
        path = context.get_path()

        # if the file has a candidate extension
        if any(map(lambda x: path.endswith(x), self._extensions)):
            self.log.debug('Trying to get ID3 data for %s' % path)

            # Fetch the data from the server
            if self._fetch_data(path.encode('utf-8')):
                id3_map = {
                    'album': None,
                    'performer': None,
                    'title': None,
                    'track': None,
                    'year': None,
                    'genre': None
                }
                # Look for tags
                try:
                    id3r = id3reader.Reader(self._buffer)
                    for tag in ['album', 'performer', 'title', 'track', 'year', 'genre']:
                        value = to_unicode(id3r.getValue(tag))
                        if value is not None:
                            id3_map[tag] = value
                            # add the tag in the context object
                            context.set_extra_data('audio_%s' % tag, value)
    
                except (id3reader.Id3Error, UnicodeDecodeError), e:
                    self.log.error('%s : %r' % (path, e))
                
                # TODO: Il faut récupérer d'autres informations !
                # self._persist.add_track(id3_map['title'], unicode('ftp://%s%s' % (self._server_addr, pathname2url(path.encode('utf-8')))), id3_map['performer'], id3_map['genre'], id3_map['album'], year=id3_map['year'], trackno=id3_map['track'])

        # Whatever the outcome of this stage,
        # continue the execution of the pipeline
        return True


class WriteDataStage (pipeline.Stage):
    """ Pipeline stage object that writes the informations in the given index.
    """
    def __init__(self, server_addr, server_id, index):
        self.log = logging.getLogger('ftpvista.pipe.write.%s' % \
                                     server_addr.replace('.', '_'))

        self._server_id = server_id
        self._index = index

    def execute(self, context):
        def get_extra(key):
            if context.get_extra_data().has_key(key):
                return context.get_extra_data()[key]
            else:
                return None

        path = context.get_path()
        self.log.debug("Adding '%s' in the index" % path)
        self._index.add_document(
                            server_id = unicode(self._server_id),
                            name = os.path.basename(path),
                            path = path,
                            size = unicode(context.get_size()),
                            mtime = unicode(context.get_mtime()),
                            audio_performer = get_extra('audio_performer'),
                            audio_title = get_extra('audio_title'),
                            audio_album = get_extra('audio_album'),
                            audio_year = get_extra('audio_year'))

        return True


def build_indexer_pipeline(server_id, server_addr, index, persist):
    """Helper function to make a basic indexing pipeline"""
    pipe = pipeline.Pipeline()
    pipe.append_stage(FetchID3TagsStage(server_addr, persist))
    pipe.append_stage(WriteDataStage(server_addr, server_id, index))

    return pipe

class IndexUpdateCoordinator(object):
    """Coordinate the scanning and indexing of FTP servers."""

    def __init__(self, persist, index, min_update_interval):
        """Initialize an update coordinator.

        Args:
          persist: an instance of FTPVistaPersist.
          index: an instance of Index
          min_update_interval : a timedelta object, this is the minimum time
                                we want to wait between two updates.
        """
        self.log = logging.getLogger('ftpvista.coordinator')
        self._persist = persist
        self._index = index
        self._update_interval = min_update_interval

    def update_server(self, server_addr):
        """Update the server at the given address if an update is needed."""
        server = self._persist.get_server_by_ip(server_addr)
        
        if(datetime.now() - server.get_last_scanned()) >= self._update_interval:
            self._do_update(server)
        
        self._persist.save()

    def _do_update(self, server):
        server_addr = server.get_ip_addr()
        server_id = server.get_server_id()

        # list the files present on the server
        self.log.info('Starting to scan %s (server id : %d)' % (server_addr,
                                                                server_id))

        scanner = FTPScanner(server_addr)
        files = scanner.scan()
        if files == None:
            self.log.error('Impossible to scan any file, fuck it.')
            return

        # compute the size of all the files found
        size = reduce(lambda total_size, file: total_size + file[1], files, 0)
        self.log.info('Found %d files (%d G) on %s' % (len(files),
                                                       size/(1024**3) ,
                                                       server_addr))

        # Set new informatons about this server in the DB
        server.set_nb_files(len(files))
        server.set_files_size(size)

        # filter out the files already indexed and up to date
        files = self._index.incremental_server_update(unicode(server_id), files)

        # sort the files by path, may reduce the CWDs if needed to fetch infos
        # from the FTP server and makes the potential errors append always in
        # the same order.
        files = sorted(files, key=lambda file: file[0])

        # Index the files
        pipeline = build_indexer_pipeline(server_id, server_addr, self._index, self._persist)
        for path, size, mtime in files:
            ctx = FileIndexerContext(path, size, mtime)
            pipeline.execute(ctx)

        # Scan done, update the last scanned date
        server.update_last_scanned()

        # commit the changes
        self._persist.save()
        self._index.commit()

        self.log.info('Server %d (%s) updated' % (server_id, server_addr))