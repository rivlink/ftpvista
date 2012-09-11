# -*- coding: utf-8 -*-
# Create your views here.

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response
from magnesite.search import models

def online(request):
    return render_to_response('online.html', {'servers': models.get_servers()})

