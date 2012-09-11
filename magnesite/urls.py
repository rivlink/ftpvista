# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
import app.const as c

UNDER_CONSTRUCTION = False

urlpatterns = patterns('',
    (r'^'+c.sPrefix+'$', 'magnesite.search.views.index'),
    (r'^'+c.sPrefix+'ajax/online$', 'magnesite.ajax.views.online'),
    (r'^'+c.sPrefix+'search/$', 'magnesite.search.views.search'),
    (r'^'+c.sPrefix+'search_results/$', 'magnesite.search.views.search_results'),
    (r'^'+c.sPrefix+'js/(?P<path>.*)$', 'django.views.static.serve', {'document_root': c.path+'templates/js'}),
    (r'^'+c.sPrefix+'images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': c.path+'templates/images'}),
    (r'^'+c.sPrefix+'css/(?P<path>.*)$', 'django.views.static.serve', {'document_root': c.path+'templates/css'}),
    (r'^'+c.sPrefix+'resources/(?P<path>.*)$', 'django.views.static.serve', {'document_root': c.path+'resources'})
)

if UNDER_CONSTRUCTION:
    urlpatterns = patterns('',
        (r'^'+c.sPrefix+'$', 'magnesite.search.views.construction'),
        (r'^'+c.sPrefix+'search/$', 'magnesite.search.views.construction'),
        (r'^'+c.sPrefix+'search_results/$', 'magnesite.search.views.construction')
    )
