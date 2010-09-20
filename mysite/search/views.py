# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response

from mysite.search import models

#TODO : CD image
def filter_online(hit):
    return hit['is_online']    

def filter_video(hit):
    return hit['name'].endswith(('.avi', '.mpg', '.mkv', '.wmv', '.mp4'))

def filter_audio(hit):
    return hit['name'].endswith(('.ogg', '.mp3', '.wma'))

def filter_movie(hit):
    return filter_video(hit) and hit['size'] > 400 * 1024**2

filters = { 'online' : filter_online,
            'video' : filter_video,
            'audio' : filter_audio,
            'movie' : filter_movie
          }


def index(request):

    servers = []
    def has_files(server):
        return server.get_nb_files() > 0

    for server in filter(has_files, models.get_servers()):
        servers.append({ 'ip' : server.get_ip_addr(),
                         'nb_files' : server.get_nb_files(),
                         'files_size' : server.get_files_size(),
                         'last_seen' : server.get_last_seen(),
                        })

    
    return render_to_response('search/index.html', {'servers' : servers})


def search(request):
    query = request.GET.get('query', None)
    include_offline = request.GET.has_key('include_offline')

    if query:
        hits = models.search(query)
        
        if not include_offline:
            hits = filter(filter_online, hits)
            
    return render_to_response('search/index.html', {'query' : query, 'hits' : list(hits)})


def search_results(request):
    query = request.GET.get('query', None)
    include_offline = request.GET.has_key('include_offline')
    movie_filter = request.GET.has_key('movie_filter')
    audio_filter = request.GET.has_key('audio_filter')

    if query:
        hits = models.search(query)
        
        for name, f in filters.iteritems():
            if request.GET.has_key('%s_filter' % name):
                if request.GET.get('%s_filter' % name) != '0':
                    hits = filter(f, hits)

    return render_to_response('search/search_results.html', {'hits' : list(hits)})