# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render, render_to_response
from magnesite.search import models
from app.forms import LastForm, SearchForm
import app.const as c
import re

def construction(request):
    return render_to_response('construction.html')

def index(request):
    base_url = request.build_absolute_uri('/')[:-1]
    form = SearchForm({'os':True})
    lastform = LastForm()
    return render(request, 'index.html', {'base_url': base_url,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'form': form,
                                             'view': 'index',
                                             'lastform': lastform})


def get_all_extensions(filter_list):
    for filters in filter_list:
        for ext in c.EXT[filters]:
            yield ext

def search(request):
    base_url = request.build_absolute_uri('/')[:-1]
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        page = 1
    fileNodes = list()
    form = None
    lastform = LastForm()
    is_last_page = False

    if query:
        fileNodes = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list), pagenum=page))
        is_last_page = fileNodes.pop() #last element contains a boolean indicating if this is the last page
        form = SearchForm(request.GET)
    else:
        # Default values
        query = ""
        online_seulement = 1
        form = SearchForm({'os':True})

    return render(request, 'index.html', {'base_url': base_url,
                                             'query' : query,
                                             'aFileNodes': fileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'is_last_page': is_last_page,
                                             'form': form,
                                             'page': page,
                                             'view': 'search',
                                             'lastform': lastform})

def last(request):
    base_url = request.build_absolute_uri('/')[:-1]
    filter_list = request.GET.getlist('ft')
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        page = 1
    fileNodes = list()
    form = SearchForm({'os':True})
    lastform = LastForm(request.GET)

    fileNodes = list(models.search(None, exts=get_all_extensions(filter_list), pagenum=page, sortbytime=True))
    is_last_page = fileNodes.pop() #last element contains a boolean indicating if this is the last page
    
    return render(request, 'index.html', {'base_url': base_url,
                                             'aFileNodes': fileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'is_last_page': is_last_page,
                                             'page': page,
                                             'form': form,
                                             'view': last,
                                             'lastform': lastform})


def search_results(request):
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    hits = None
    is_last_page = False

    if query:
        hits = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list)))
        is_last_page = hits.pop() #last element contains a boolean indicating if this is the last page

    return render(request, 'search_results.html', {'aFileNodes': hits, 'is_last_page': is_last_page})
