# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response

from magnesite.search import models

from app.search_filter import SearchFilterFileTypes
import app.const as c

import re

#TODO : CD image
def filter_online(fileNode):
    return fileNode.isOnline()  

def filter_video(fileNode):
    return fileNode.getFilename().lower().endswith(('.avi', '.mpg', '.mkv', '.wmv', '.mp4', '.mov', '.3gp', '.3gp2', '.mpeg', '.mpg', '.mpg2', '.ogm'))

def filter_audio(fileNode):
    return fileNode.getFilename().lower().endswith(('.mp3', '.wma', '.cda', '.ogg', '.flac', '.aac', '.aiff', '.m4a', '.wav'))

def filter_image(fileNode):
    return fileNode.getFilename().lower().endswith(('.jpep', '.jpg', '.gif', '.png', '.bmp', '.tiff', '.psd'))
    
def filter_diskimage(fileNode):
    return fileNode.getFilename().lower().endswith(('.iso', '.bin', '.cue', '.img', '.mds', '.mdf', '.nrg'))
    
def filter_archive(fileNode):
    return re.search('\.(rar|tar|tgz|tz|yz|zz|xz|war|jar|ace|zip|7z|gz(ip){0,1}|bz(ip){0,1}(2){0,1}|r(\d){1,}|deb|rpm)$', fileNode.getFilename(), re.I) != None
    
def filter_movie(hit):
    return filter_video(hit) and hit['size'] > 400 * 1024**2


filters = { 'online' : filter_online,
            'video' : filter_video,
            'audio' : filter_audio,
            'movie' : filter_movie
          }

def construction(request):
    return render_to_response('construction.html')

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
    
    return render_to_response('index.html', {'sPrefix' : c.sPrefix,
                                             'servers' : servers,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'aFilterFileTypes': SearchFilterFileTypes.getFileTypes()})


def search(request):
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    filteredFileNodes = list()
    
    if query:
        fileNodes = models.search(query)
        
        if online_seulement:
            fileNodes = filter(filter_online, fileNodes)
        
        if len(filter_list) > 0 and len(filter_list) < 5:
            for fileNode in fileNodes: 
                if filter_list.count(str(c.VIDEOS)) == 1:
                    if filter_video(fileNode):
                        filteredFileNodes.append(fileNode)
                if filter_list.count(str(c.AUDIOS)) == 1:
                    if filter_audio(fileNode):
                        filteredFileNodes.append(fileNode)
                if filter_list.count(str(c.IMAGES)) == 1:
                    if filter_image(fileNode):
                        filteredFileNodes.append(fileNode)
                if filter_list.count(str(c.ARCHIVES)) == 1:
                    if filter_archive(fileNode):
                        filteredFileNodes.append(fileNode)
                if filter_list.count(str(c.DISKIMAGES)) == 1:
                    if filter_diskimage(fileNode):
                        filteredFileNodes.append(fileNode)
        else:
            filteredFileNodes = list(fileNodes)
    else:
        query = ""
    
    return render_to_response('index.html', {'sPrefix' : c.sPrefix,
                                             'query' : query,
                                             'aFileNodes': filteredFileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'aFilterFileTypes': SearchFilterFileTypes.getFileTypes()})


def search_results(request):
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    movie_filter = request.GET.has_key('movie_filter')
    audio_filter = request.GET.has_key('audio_filter')

    if query:
        hits = models.search(query)
        
        for name, f in filters.iteritems():
            if request.GET.has_key('%s_filter' % name):
                if request.GET.get('%s_filter' % name) != '0':
                    hits = filter(f, hits)

    return render_to_response('search_results.html', {'hits' : list(hits)})
