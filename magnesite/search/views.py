# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response
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
    return render_to_response('index.html', {'base_url': base_url,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'form': form,
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
    fileNodes = list()
    form = None
    lastform = LastForm()
    
    if query:
        fileNodes = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list)))
        form = SearchForm(request.GET)
    else:
        # Default values
        query = ""
        online_seulement = 1
        form = SearchForm({'os':True})

    return render_to_response('index.html', {'base_url': base_url,
                                             'query' : query,
                                             'aFileNodes': fileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'form': form,
                                             'lastform': lastform})

def last(request):
    base_url = request.build_absolute_uri('/')[:-1]
    filter_list = request.GET.getlist('ft')
    fileNodes = list()
    form = SearchForm({'os':True})
    lastform = LastForm(request.GET)

    fileNodes = list(models.search(None, exts=get_all_extensions(filter_list), sortbytime=True))
    
    return render_to_response('index.html', {'base_url': base_url,
                                             'aFileNodes': fileNodes,
                                             'sTrId': u'node-',
                                             'servers': models.get_servers(),
                                             'nb_files': models.get_nb_files(),
                                             'files_size': models.get_files_size(),
                                             'form': form,
                                             'lastform': lastform})


def search_results(request):
    query = request.GET.get('s', None)
    online_seulement = request.GET.has_key('os')
    filter_list = request.GET.getlist('ft')
    hits = None

    if query:
        hits = list(models.search(query, online=online_seulement, exts=get_all_extensions(filter_list)))

    return render_to_response('search_results.html', {'hits': hits})
