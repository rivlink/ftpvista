#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ConfigParser
from datetime import timedelta
from Queue import Queue
from threading import Thread
from optparse import OptionParser
import socket
import os
import time
import daemon
import lockfile
import signal
import sys

os.environ['TZ'] = 'CET'

from index import Index, IndexUpdateCoordinator
import persist as ftpvista_persist
import pipeline
import observer
from sniffer import *

flock = None
context = None
pidfile = None

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

def check_online(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'online_checker'))
    log_checker = logging.getLogger('online_check')
    log_checker.info('Starting online servers checker')
    
    db_uri = config.get('db', 'uri')
    persist = ftpvista_persist.FTPVistaPersist(db_uri)
    persist.initialize_store()
    
    persist.launch_online_checker()

def main_daemonized(config):
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'main'))

    log = logging.getLogger('ftpvista')
    log.info('Starting FTPVista')
    
    # The detected FTP server IP will be put in this queue waiting the
    # update coordinator to handle them
    ftpserver_queue = Queue(100)

    # Configure the sniffer task and run it in a different thread
    blacklist = config.get('indexer', 'blacklist', '').split(',')
    valid_ip_pattern = config.get('indexer', 'valid_ip_pattern')
    sniffer_proc = Thread(target=sniffer_task, args=(ftpserver_queue,
                                            blacklist, valid_ip_pattern))
    
    log.info('Launching the sniffer thread')
    sniffer_proc.start()
    
    """
    ## From now we can set the application to use a different user id and group id
    ## much better for security reasons
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')
    
    log.info('Setting uid=%d and gid=%d' % (uid, gid))
    os.setgid(gid)
    os.setuid(uid)
    """

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

def sigterm_handler(signum, frame):
    close_daemon()

def close_daemon():
    global flock
    global context
    destroy_pid_file()
    flock.release()
    context.close()
    os._exit(os.EX_OK)

def cleanup_and_close():
    pass

def create_pid_file(pid_file):
    global pidfile
    pidfile = pid_file
    f = open(pidfile, 'w')
    f.write(str(os.getpid()))
    
def destroy_pid_file():
    global pidfile
    os.remove(pidfile)

def main(options):
    global flock
    global context
    
    config = ConfigParser.SafeConfigParser()
    config.read(options.config_file)
    
    """Daemonize FTPVista"""
    if options.daemon:
        #Context
        context = daemon.DaemonContext(
            working_directory = config.get('indexer', 'working_directory')
        )
        
        #Mapping signals to methods
        context.signal_map = {
            signal.SIGTERM: 'sigterm_handler',
            signal.SIGHUP: 'sigterm_handler',
            signal.SIGINT: 'sigterm_handler',
            #signal.SIGUSR1: reload_program_config,
        }
        context.detach_process = True
        context.sigterm_handler = sigterm_handler
        context.open()
    
    if options.only_check_online:
        create_pid_file(config.get('online_checker', 'pid'))
        flock = lockfile.FileLock(config.get('online_checker', 'pid'))
        if flock.is_locked():
            print ("Already launched ... exiting")
            sys.exit(3)
        flock.acquire()
        check_online(config)
    else:
        create_pid_file(config.get('indexer', 'pid'))
        flock = lockfile.FileLock(config.get('indexer', 'pid'))
        if flock.is_locked():
            print ("Already launched ... exiting")
            sys.exit(2)
        flock.acquire()
        main_daemonized(config)

if __name__ == '__main__':
    parser = OptionParser(version="FTPVista 3.0")
    
    parser.add_option("-c", "--config", dest="config_file", metavar="FILE", default='/home/ftpvista/ftpvista3/ftpvista.conf', help="Path to the config file")
    parser.add_option("-d", "--daemon", action="store_true", dest="daemon", default=True, help="Run FTPVista as a Daemon")
    parser.add_option("--no-daemon", action="store_false", dest="daemon", help="Don't run FTPVista as a Daemon")
    parser.add_option("-n", "--check-online", action="store_true", dest="check_online", default=True, help="Launch FTPVista with online server checking")
    parser.add_option("--no-check-online", action="store_false", dest="check_online", help="Launch FTPVista without online server checking")
    parser.add_option("-o", "--only-check-online", action="store_true", dest="only_check_online", help="Launch only online server checking module")
    
    (options, args) = parser.parse_args()
    
    if options.only_check_online and not options.check_online:
        parser.error("--only-check-online (-o) is active, --no-check-online ignored")
    
    main(options)