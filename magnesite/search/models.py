# -*- coding: utf-8 -*-
import sys
sys.path.append("/home/ftpvista/ftpvista3/ftpvista")
from django.db import models
from django.conf import settings

from whoosh import index as whoosh_index
from whoosh.qparser import *

from datetime import datetime, timedelta

from app.filenode import *

# Create your models here.
from persist import FTPVistaPersist

persist = FTPVistaPersist(settings.PERSIST_DB)


def search(query, limit=1000):
    index = whoosh_index.open_dir(settings.WHOOSH_IDX)
    is_online_cache = {}

    def is_online(server):
        if not is_online_cache.has_key(server):
            delta = datetime.today() - server.get_last_seen()
            is_online_cache[server] = delta < timedelta(minutes=10)

        return is_online_cache[server]
    
    def get_schema():
        charmap = charset_table_to_dict(default_charset)
        my_analyzer = StemmingAnalyzer | CharsetFilter(charmap)
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
    
    searcher = index.searcher()
    parser = MultifieldParser(["name", "path", "audio_performer", "audio_title",
                               "audio_album"],
                              schema=get_schema())
    parser.add_plugin(PhrasePlugin)
    parser.add_plugin(SingleQuotesPlugin)
    parser.add_plugin(MinusNotPlugin)
    parser.add_plugin(PrefixPlugin)
    parser.add_plugin(RangePlugin)
    parser.remove_plugin_class(WildcardPlugin)
    parser.remove_plugin_class(BoostPlugin)
    parser.remove_plugin_class(GroupPlugin)

    results = searcher.search(parser.parse(query), limit)
    
    for result in results:
        server_id = int(result['server_id'])
        server = persist.get_server(server_id)
        if server == None:
            continue
        server_ip = server.get_ip_addr()

        hit = { 'server_id' : server_id,
                'server_name' : server_ip,
                'is_online' : is_online(server),
                'name' : result['name'],
                'url' : 'ftp://%s%s' % (server_ip, result['path']),
                'size' : int(result['size']),
                'mtime' : datetime.strptime(result['mtime'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            }
        
        bIsAudio = False
        for extra in['audio_performer', 'audio_title', 'audio_album', 'audio_year']:
            if result.fields().has_key(extra):
                if result[extra] != None and result[extra] != "None": #FIXME: where does the None come from?
                    hit[extra] = result[extra]
                    bIsAudio = True
                else:
                    hit[extra] = ""
        
        if bIsAudio:
            yield AudioFileNode(server_ip, hit['url'], hit['name'], hit['mtime'], hit['size'], hit['is_online'], hit['audio_performer'], hit['audio_album'], hit['audio_title'], hit['audio_year'])
        else:
            yield FileNode(server_ip, hit['url'], hit['name'], hit['mtime'], hit['size'], hit['is_online'])


def get_servers():
    return persist.get_servers()
