#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

import unittest
import logging
from datetime import datetime

import scanner


TEST_IP = '10.90.0.1'
DIR_LISTING_OUTPUTS = {
    '/': '''
drwxr-xr-x   8 ftp      ftp          4096 Mar  5 01:07 divers
drwxr-xr-x  13 ftp      ftp          4096 Mar  6 18:48 hda
drwxr-xr-x   2 ftp      ftp          4096 Jul 11  2006 hdb
drwx------   2 ftp      ftp          4096 Mar  7 15:28 testA
-rw-------   1 ftp      ftp          6386 Mar  7 15:28 testB.txt
-rw-r--r--   1 ftp      ftp          6334 Mar  7 15:28 testC.txt
-rw-r--r--   1 ftp      ftp          4392 Mar  2 18:34 testD.bin
'''.strip().splitlines(),
    '/divers': '',
    '/hda': '''
drwxr-xr-x  13 ftp      ftp          4096 Mar  6 18:48 hda2
-rw-r--r--   1 ftp      ftp          6330 Mar  7 00:17 test.txt
'''.strip().splitlines(),
    '/hda/hda2': '''
-rw-r--r--   1 ftp      ftp          6339 Jul 11  2006 test.txt
'''.strip().splitlines(),
    '/hdb': '',
    }


def this_year():
    """Utility to get the current year"""
    return datetime.now().year

INTERESTING_FILES = {
    '/testC.txt' : (6334, datetime(this_year(), 3, 7, 15, 28)),
    '/testD.bin' : (4392, datetime(this_year(), 3, 2, 18, 34)),
    '/hda/test.txt' : (6330, datetime(this_year(), 3, 7, 00, 17)),
    '/testD.bin' : (4392, datetime(this_year(), 3, 2, 18, 34)),
    '/hda/hda2/test.txt' : (6339, datetime(2006, 7, 11, 0, 0))
}

def expected_file_tuple(path):
    """Returns a tuple repsenting the file at the given path"""
    size, date = INTERESTING_FILES[path]
    return (path, size, date)




class MockFTP(object):
    def __init__(self, host):
        assert host == TEST_IP
        self.logged_in = False
        self._cwd = '/'

    def login(self):
        self.logged_in = True

    def set_pasv(self, on):
        pass

    def cwd(self, dir):
        self._cwd = dir

    def dir(self, callback):
        assert self.logged_in
        assert self._cwd in DIR_LISTING_OUTPUTS
        for l in DIR_LISTING_OUTPUTS[self._cwd]:
            callback(l)

    def quit(self):
        self.logged_in = False
        pass



class TestFTPScanner(unittest.TestCase):
    def setUp(self):
        self.ftp = scanner.FTPScanner(TEST_IP, ftp_class=MockFTP)

    def testParsePermissions(self):
        data_set = (
            ('----------', (False, False)),
            ('-------r--', (False, True)),
            ('d---------', (True, False)),
            ('d------r--', (True, False)),
            ('d--------x', (True, False)),
            ('d------r-x', (True, True)),
            ('lrwxrwxrwx', (False, False)),
            )

        for permissions, expected_result in data_set:
            result = self.ftp.parse_permissions(permissions)
            self.assertEquals(result, expected_result)


    def testParseDate(self):
        data_set = (
            # with the year
            ('Nov 14  2008', datetime(2008, 11, 14)),

            # without the year field
            ('Jan 10 19:50', datetime(this_year(), 1, 10, 19, 50)),

            # Invalid inputs
            ('14/02/2010', None),
            ('caca', None),
            ('', None)
            )

        for date, expected_result in data_set:
            result = self.ftp.parse_date(date)
            self.assertEquals(result, expected_result)


    def testListRootDirectory(self):
        self.ftp.connect()
        files, dirs = self.ftp.list_files('/')
        self.ftp.disconnect()

        self.assertEquals(files, [expected_file_tuple('/testC.txt'),
                                  expected_file_tuple('/testD.bin')])
        self.assertEquals(dirs, ['/divers', '/hda', '/hdb'])

    def testFullScan(self):
        expected_files = set([
            expected_file_tuple('/testC.txt'),
            expected_file_tuple('/testD.bin'),
            expected_file_tuple('/hda/test.txt'),
            expected_file_tuple('/hda/hda2/test.txt'),
            ])
        self.assertEquals(set(self.ftp.scan()), expected_files)

    def testScanHandlesIgnoredPaths(self):
        expected_files = set([
            expected_file_tuple('/testC.txt'),
            expected_file_tuple('/testD.bin'),
            ])
        self.assertEquals(set(self.ftp.scan(['/hda'])), expected_files)


if __name__ == '__main__':
    logging.basicConfig(level=100)
    unittest.main()
