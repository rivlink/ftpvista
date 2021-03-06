# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from whoosh import index as whoosh_index, sorting
from whoosh.qparser import *
from whoosh.query import Or, And, Term, NullQuery
from datetime import datetime, timedelta
from ftpvistasite.app.filenode import *
from ftpvista.persist import FTPVistaPersist

persist = FTPVistaPersist(settings.PERSIST_DB)


def search(query, online=False, exts=None, pagenum=1, pagelen=100, sortbytime=False):
    index = whoosh_index.open_dir(settings.WHOOSH_IDX)
    is_online_cache = {}
    searchfilter = None

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=settings.LOG_PATH)

    log = logging.getLogger('ftpvista_search')
    log.debug('Search query : %s' % query)

    persist.expire_all()

    def is_online(server):
        if server not in is_online_cache:
            datetime_today = datetime.today()
            delta = datetime_today - server.get_last_seen()
            is_online_cache[server] = delta < timedelta(seconds=310)

            log.debug("datetime.today() : %s" % datetime_today)
            log.debug("server.get_last_seen() : %s" % server.get_last_seen())
            log.debug("delta : %s" % delta)

        return is_online_cache[server]

    searcher = index.searcher()
    parser = MultifieldParser(["name", "path", "audio_artist", "audio_title",
                               "audio_album"],
                              schema=index.schema)
    parser.add_plugin(PhrasePlugin)
    parser.add_plugin(SingleQuotePlugin)
    parser.add_plugin(PrefixPlugin)
    parser.add_plugin(RangePlugin)
    parser.remove_plugin_class(WildcardPlugin)
    parser.remove_plugin_class(BoostPlugin)
    parser.remove_plugin_class(GroupPlugin)

    if online:
        online_servers_id = []
        for server in persist.get_servers():
            if is_online(server):
                online_servers_id.append(Term("server_id", str(server.get_server_id())))
        if len(online_servers_id) > 0:
            searchfilter = Or(online_servers_id)
        else:
            searchfilter = NullQuery()

    if exts is not None:
        extensionfilter = []
        for extension in exts:
            extensionfilter.append(Term("ext", extension))
        if len(extensionfilter) > 0:
            if searchfilter is not None:
                searchfilter = And([searchfilter, Or(extensionfilter)])
            else:
                searchfilter = Or(extensionfilter)

    finalquery = Term("has_id", "a")  # Quicker than Every Query. See doc.
    if query is not None:
        finalquery = parser.parse(query)
    if searchfilter is not None:
        finalquery = And([finalquery, searchfilter])

    if sortbytime:
        facet = sorting.FieldFacet("mtime", reverse=True)
        results = searcher.search_page(finalquery, pagenum, pagelen=pagelen, sortedby=facet)
    else:
        results = searcher.search_page(finalquery, pagenum, pagelen=pagelen)

    for result in results:
        server_id = int(result['server_id'])
        server = persist.get_server(server_id)
        if server is None:
            continue
        server_ip = server.get_ip_addr()

        hit = {'server_id': server_id,
               'server_name': server_ip,
               'is_online': is_online(server),
               'name': result['name'],
               'url': 'ftp://%s%s' % (server_ip, result['path']),
               'size': int(result['size']),
               'mtime': ''}
        if result['mtime'] is not None and result['mtime'] != 'None':
            hit['mtime'] = datetime.strptime(result['mtime'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")

        bIsAudio = False
        for extra in['audio_artist', 'audio_title', 'audio_album', 'audio_year']:
            if extra in result.fields():
                if result[extra] is not None and result[extra] != "None":  # FIXME: where does the None come from?
                    hit[extra] = result[extra]
                    bIsAudio = True
                else:
                    hit[extra] = ""
            else:
                    hit[extra] = ""

        if bIsAudio:
            yield AudioFileNode(server_ip, hit['url'], hit['name'], hit['mtime'], hit['size'], hit['is_online'], hit['audio_artist'], hit['audio_album'], hit['audio_title'], hit['audio_year'])
        else:
            yield FileNode(server_ip, hit['url'], hit['name'], hit['mtime'], hit['size'], hit['is_online'])
    yield results.is_last_page()


def get_nb_files():
    nb_files = 0
    for server in persist.get_servers():
        nb_files += server.get_nb_files()
    return nb_files


def get_files_size():
    files_size = 0
    for server in persist.get_servers():
        files_size += server.get_files_size()
    return files_size


def get_servers():
    persist.expire_all()
    return persist.get_servers()
