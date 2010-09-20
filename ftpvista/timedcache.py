# -*- coding: utf-8 -*-

import time
from collections import deque

#TODO: docstrings

class TimedCache:
    def __init__(self, timeout, time_func=time.time):
        self._timeout = timeout
        self._current_time = time_func
        self._objs = {}
        self._queue = deque()

    def __contains__(self, obj):
        self._remove_outdated()
        return obj in self._objs

    def _remove_outdated(self):
        if len(self._queue) > 0:
            if (self._current_time() - self._objs[self._queue[-1]]) \
                > self._timeout:
                del self._objs[self._queue.pop()]
                self._remove_outdated()

    def add(self, obj):
        if obj not in self:
            self._objs[obj] = self._current_time()
            self._queue.appendleft(obj)

    def clear(self):
        self._objs = {}
        self._queue.clear()