# -*- coding: utf-8 -*-

"""Some very basic tests for the TimedCache class.

    TODO : Need some white box testing.
"""

import unittest
from .timedcache import TimedCache


class FakeClock (object):
    """A Double for faking a clock."""

    def __init__(self, current_time=0):
        self.time = current_time

    def set_time(self, new_time):
        self.time = new_time

    def get_time(self):
        return self.time


class TimedCacheTestCase(unittest.TestCase):
    def setUp(self):
        self.timeout = 20
        self.clock = FakeClock()
        self.cache = TimedCache(self.timeout, time_func=self.clock.get_time)

        # tuples (value, time)
        self.test_values = [(1, 1000),
                            (2, 1001),
                            (3, 1015),
                            (4, 1020)]

        for value, time in self.test_values:
            self.clock.set_time(time)
            self.cache.add(value)

    def testContainsBeforeTimeout(self):
        """Testing for values that should be in the cache"""

        self.clock.set_time(1020)
        # At this time every value must still be in the cache
        for value, time in self.test_values:
            self.assert_(value in self.cache)

    def testRemovedAtTimeout(self):
        """Testing for values that should not be in the cache"""

        self.clock.set_time(1021)
        # nust have everything but the first value
        self.assert_(self.test_values[0][0] not in self.cache)
        for value, time in self.test_values[1:]:
            self.assert_(value in self.cache)

    def testClearedAfterTimeout(self):
        self.clock.set_time(1041)
        for value, time in self.test_values:
            self.assert_(value not in self.cache)

    def testAddSameValue(self):
        self.clock.set_time(1030)
        self.cache.add(1)   # has recently been deleted
        self.cache.add(3)   # still in the cache
        self.cache.add(5)   # no added before

        self.clock.set_time(1036)   # just after the first "3" timeout
        self.assert_(3 not in self.cache)
        self.assert_(1 in self.cache)
        self.assert_(5 in self.cache)

    def testClear(self):
        """ Whatever the time, this must remove all values"""
        self.cache.clear()
        for value, time in self.test_values:
            self.assert_(value not in self.cache)
