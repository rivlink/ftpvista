# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings

from whoosh import index as whoosh_index
from whoosh.qparser import *

from datetime import datetime, timedelta

# Create your models here.
import sys
sys.path.append("/home/ftpvista/ftpvista3/ftpvista")
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

    
    searcher = index.searcher()
    parser = MultifieldParser(["name", "path", "audio_performer", "audio_title",
                               "audio_album"],
                              schema=index.schema)

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
                'size' : int(result['size'])
                #TODO : mtime
            }

        for extra in['audio_performer', 'audio_title', 'audio_album', 'audio_year']:
            if result.has_key(extra):
               if result[extra] !=  None: #FIXME: where does the None come from?
                    hit[extra] = result[extra]

        yield hit


def get_servers():
    return persist.get_servers()

    
