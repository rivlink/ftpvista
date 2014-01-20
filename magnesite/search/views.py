# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response
from magnesite.search import models
from app.search_filter import SearchFilterFileTypes

import app.const as c
import re

def filter_movie(hit):
    return filter_video(hit) and hit['size'] > 400 * 1024**2

def construction(request):
    return render_to_response('construction.html')

def index(request):
    base_url = request.build_absolute_uri('/')[:-1]
    return render_to_response('index.html', {'base_url': base_url,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'aFilterFileTypes': SearchFilterFileTypes.getFileTypes([str(c.VIDEOS), str(c.AUDIOS), str(c.IMAGES), str(c.ARCHIVES), str(c.DISKIMAGES)]),
                                             'isOnlineSelected': True,
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size()})


def get_all_extensions(filter_list):
    for filters in filter_list:
        for ext in c.EXT[filters]:
            yield ext

def search(request):
    base_url = request.build_absolute_uri('/')[:-1]
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    fileNodes = list()
    
    if query:
        fileNodes = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list)))
    else:
        # Default values
        query = ""
        online_seulement = 1
        filter_list = [str(c.VIDEOS), str(c.AUDIOS), str(c.IMAGES), str(c.ARCHIVES), str(c.DISKIMAGES)]
    
    return render_to_response('index.html', {'base_url': base_url,
                                             'query' : query,
                                             'aFileNodes': fileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'aFilterFileTypes': SearchFilterFileTypes.getFileTypes(filter_list),
                                             'isOnlineSelected': online_seulement,
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size()})


def search_results(request):
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    hits = None

    if query:
        hits = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list)))

    return render_to_response('search_results.html', {'hits': hits})
