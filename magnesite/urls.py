# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import app.const as c

UNDER_CONSTRUCTION = False

urlpatterns = patterns('',
    url(r'^$', 'magnesite.search.views.index'),
    url(r'^ajax/online$', 'magnesite.ajax.views.online', name='online'),
    url(r'^search/$', 'magnesite.search.views.search', name='search'),
    url(r'^last/$', 'magnesite.search.views.last', name='last'),
    url(r'^search_results/$', 'magnesite.search.views.search_results', name="results"),
    url(r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve', name="static"),
)

if UNDER_CONSTRUCTION:
    urlpatterns = patterns('',
        (r'^$', 'magnesite.search.views.construction'),
        (r'^search/$', 'magnesite.search.views.construction'),
        (r'^search_results/$', 'magnesite.search.views.construction')
    )
