#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest

import sqlalchemy

from . import persist


TEST_DB_URI = 'sqlite://'
TEST_IP1 = '10.90.0.1'
TEST_IP2 = '10.90.0.2'


class TestFTPVistaPersist(unittest.TestCase):
    def setUp(self):
        self.persist = persist.FTPVistaPersist(TEST_DB_URI)
        self.persist.initialize_store()

        # insert one server
        self.server1 = self.persist.get_server_by_ip(TEST_IP1)

    def tearDown(self):
        sqlalchemy.orm.clear_mappers()

    def testGetServerByIpAddress(self):
        # TEST_IP1 is already in the DB
        self.assertEquals(self.server1, self.persist.get_server_by_ip(TEST_IP1))

        # The previous operation musnt insert a new record
        self.assertEquals(1, len(self.persist.get_servers()))

        # add a new server, the id must be different
        server2 = self.persist.get_server_by_ip(TEST_IP2)
        self.assertNotEquals(self.server1.id, server2.id)
        self.assertEquals(2, len(self.persist.get_servers()))

    def testGetAllServers(self):
        server2 = self.persist.get_server_by_ip(TEST_IP2)
        self.assertEquals(frozenset([self.server1, server2]),
                          frozenset(self.persist.get_servers()))


if __name__ == '__main__':
    unittest.main()
