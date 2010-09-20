# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *


urlpatterns = patterns('',
    (r'^$', 'mysite.search.views.index'),
    (r'^search/$', 'mysite.search.views.search'),
    (r'^search_results/$', 'mysite.search.views.search_results')
)
