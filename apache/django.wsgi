import os
import sys

parentdir = os.path.normpath(os.path.dirname(os.path.realpath(__file__))+'/..')

paths = [parentdir, parentdir+'/ftpvista', parentdir+'/magnesite']
for newpath in paths:
    if newpath not in sys.path:
        sys.path.append(newpath)

os.environ['DJANGO_SETTINGS_MODULE'] = 'magnesite.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
