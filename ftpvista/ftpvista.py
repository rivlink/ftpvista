#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ConfigParser
from datetime import timedelta
from multiprocessing import Process, Queue
import socket
import os
import time
import daemon
import lockfile

os.environ['TZ'] = 'CET'

from index import Index, IndexUpdateCoordinator
import persist as ftpvista_persist
import pipeline
import observer
from sniffer import *

class PutInQueueStage (pipeline.Stage):
    """Put all the recieved  IP addresses in the specified queue"""
    def __init__(self, queue):
        self._queue = queue

    def execute(self, ip_addr):
        self._queue.put(ip_addr)

def sniffer_task(queue, blacklist, valid_ip_pattern):
    # create an ARP sniffer for discovering the hosts
    sniffer = ARPSniffer()

    # Bind the sniffer to a filtering pipeline to discard unintersting IP
    pipeline = build_machine_filter_pipeline(blacklist, valid_ip_pattern,
                                             drop_duplicate_timeout=10*60)
    pipeline.append_stage(PutInQueueStage(queue))
    SnifferToPipelineAdapter(sniffer, pipeline)
    
    # Run sniffer, run ..
    sniffer.run()

def check_online(config_file='ftpvista.conf'):
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'logfile'))
    log = logging.getLogger('online_check')
    log.info('Starting online servers checker')
    
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')
    
    log.info('Setting uid=%d and gid=%d' % (uid, gid))
    os.setgid(gid)
    os.setuid(uid)
    
    db_uri = config.get('db', 'uri')
    persist = ftpvista_persist.FTPVistaPersist(db_uri)
    persist.initialize_store()
    
    persist.launch_online_checker()

def main(config_file='ftpvista.conf'):
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'logfile'))

    log = logging.getLogger('ftpvista')
    log.info('Starting FTPVista')

    # The detected FTP server IP will be put in this queue waiting the
    # update coordninator to handle them
    ftpserver_queue = Queue(100)

    # Configure the sniffer task and run it in a diffrent process
    blacklist = config.get('indexer', 'blacklist', '').split(',')
    valid_ip_pattern = config.get('indexer', 'valid_ip_pattern')
    sniffer_proc = Process(target=sniffer_task, args=(ftpserver_queue,
                                            blacklist, valid_ip_pattern))

    log.info('Launching the sniffer process')
    sniffer_proc.start()
    
    ## From now we can set the application to use a different user id and group id
    ## much better for security reasons
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')
    
    log.info('Setting uid=%d and gid=%d' % (uid, gid))
    os.setgid(gid)
    os.setuid(uid)


    # Set the socket connection timeout, so that people with
    # broken FTPs will time out quickly, rather than hang the scanner.
    socket.setdefaulttimeout(30.0)

    # Create the DB to store informations about the FTP servers
    db_uri = config.get('db', 'uri')
    persist = ftpvista_persist.FTPVistaPersist(db_uri)
    persist.initialize_store()

    # Full-text index for storing terms from the files found on the servers
    index_uri = config.get('index', 'uri')
    index = Index(index_uri)

    # This defines how and at which period to perform updates from the servers
    min_update_interval = config.getint('indexer', 'min_update_interval')
    
    update_coordinator = IndexUpdateCoordinator(
                           persist, index, timedelta(hours=min_update_interval))

    log.info('Init done, running the update coordinator ..')
    while True:
        # Wait for an FTP server to be detected and update it
        update_coordinator.update_server(ftpserver_queue.get())


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 3:
        """ Execute nmap to check if servers are online """
        if sys.argv[1] == "online":
            context = daemon.DaemonContext(
                pidfile = lockfile.FileLock('/var/run/ftpvista_online_checker.pid')
            )
            with context:
                check_online(sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main()
