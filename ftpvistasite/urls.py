"""ftpvistasite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from ftpvistasite.search import views as searchviews
from ftpvistasite.ajax import views as ajaxviews

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', searchviews.index),
    url(r'^ajax/online$', ajaxviews.online, name='online'),
    url(r'^search/$', searchviews.search, name='search'),
    url(r'^last/$', searchviews.last, name='last'),
    url(r'^search_results/$', searchviews.search_results, name='results')
]

"""
if UNDER_CONSTRUCTION:
    urlpatterns = patterns('',
        (r'^$', 'magnesite.search.views.construction'),
        (r'^search/$', 'magnesite.search.views.construction'),
        (r'^search_results/$', 'magnesite.search.views.construction')
    )
"""
