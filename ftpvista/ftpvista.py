#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ConfigParser
from datetime import timedelta
from optparse import OptionParser
from multiprocessing import Queue
import socket
import os
import time
import daemon
import lockfile
import signal
import sys
import traceback
import shutil

os.environ['TZ'] = 'CET'

from index import Index, IndexUpdateCoordinator
from multiprocess import OwnedProcess
import persist as ftpvista_persist
import pipeline
import observer
from sniffer import *

class HandleMain():
    flock = None
    context = None
    pidfile = None

def sniffer_task(queue, blacklist, valid_ip_pattern, subnet, scanner_interval):
    # create an ARP sniffer for discovering the hosts
    # sniffer = ARPSniffer()
    sniffer = ARPScanner(subnet, scanner_interval)
    # Bind the sniffer to a filtering pipeline to discard uninteresting IP
    pipeline = build_machine_filter_pipeline(queue, blacklist, valid_ip_pattern,
                                             drop_duplicate_timeout=10*60)
    SnifferToPipelineAdapter(sniffer, pipeline)
    
    # Run sniffer, run ..
    sniffer.run()

def clean_all(config):
    clean_player(config)
    clean_db(config)
    clean_index(config)
    
def clean_db(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'main'))
    log = logging.getLogger('ftpvista.clean_db')
    log.info('Starting FTPVista cleaning : db')
    
    db_uri = config.get('db', 'uri')
    uri_strip = "/" + db_uri.lstrip('sqlite://')
    if os.path.isfile(uri_strip):
        persist = ftpvista_persist.FTPVistaPersist(db_uri)
        persist.initialize_store()
        os.remove(uri_strip)
        log.info("Database deleted")
    else:
        log.info("No database : skipping.")

def clean_index(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'main'))
    log = logging.getLogger('ftpvista.clean_index')
    log.info('Starting FTPVista cleaning : index')
    
    index_uri = config.get('index', 'uri')
    if os.path.isdir(index_uri):
        shutil.rmtree(index_uri)
        log.info("Index deleted")
    else:
        log.info("Index not found : skipping.")

def clean_player(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'main'))
    log = logging.getLogger('ftpvista.clean_player')
    log.info('Starting FTPVista cleaning : player')
    
    db_uri = config.get('db', 'uri')
    rivplayer_uri = config.get('db', 'rivplayer_uri')
    if rivplayer_uri == 'None' or rivplayer_uri == '':
        rivplayer_uri = None
    if rivplayer_uri is None:
        log.info("No music database: skipping.")
    else:
        persist = ftpvista_persist.FTPVistaPersist(db_uri, rivplayer_uri)
        persist.initialize_store()
        persist.truncate_all()
        log.info("Player database cleaned")

def check_online(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'online_checker'))
    log = logging.getLogger('ftpvista')
    log.info('Starting online servers checker')
    
    db_uri = config.get('db', 'uri')
    rivplayer_uri = config.get('db', 'rivplayer_uri')
    if rivplayer_uri == 'None' or rivplayer_uri == '':
        rivplayer_uri = None
    persist = ftpvista_persist.FTPVistaPersist(db_uri, rivplayer_uri)
    persist.initialize_store()
    
    index_uri = config.get('index', 'uri')
    index = Index(index_uri, persist)
    persist.set_index(index)
    
    update_interval = int(config.get('online_checker', 'update_interval'))
    purge_interval = int(config.get('online_checker', 'purge_interval'))
    
    persist.launch_online_checker(update_interval, purge_interval)

def main_daemonized(config, ftpserver_queue):
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'main'))

    log = logging.getLogger('ftpvista')
    log.info('Starting FTPVista')

    # Set the socket connection timeout, so that people with
    # broken FTPs will time out quickly, rather than hang the scanner.
    socket.setdefaulttimeout(30.0)

    # Create the DB to store informations about the FTP servers
    db_uri = config.get('db', 'uri')
    rivplayer_uri = config.get('db', 'rivplayer_uri')
    if rivplayer_uri == 'None' or rivplayer_uri == '':
        rivplayer_uri = None
    persist = ftpvista_persist.FTPVistaPersist(db_uri, rivplayer_uri)
    persist.initialize_store()

    # Full-text index for storing terms from the files found on the servers
    index_uri = config.get('index', 'uri')
    index = Index(index_uri, persist)

    # This defines how and at which period to perform updates from the servers
    min_update_interval = config.getint('indexer', 'min_update_interval')
    
    max_depth = config.get('indexer', 'max_depth')
    update_coordinator = IndexUpdateCoordinator(
                           persist, index, timedelta(hours=min_update_interval), max_depth)
    
    log.info('Init done, running the update coordinator ...')
    while True:
        # Wait for an FTP server to be detected and update it
        update_coordinator.update_server(ftpserver_queue.get())

def sigterm_handler(signum, frame):
    close_daemon()

def close_daemon():
    destroy_pid_file()
    if HandleMain.flock is not None:
        HandleMain.flock.release()
    if HandleMain.context is not None:
        HandleMain.context.close()
    OwnedProcess.terminateall()
    os._exit(os.EX_OK)

def cleanup_and_close():
    pass

def create_pid_file(pid_file):
    HandleMain.pidfile = pid_file
    f = open(HandleMain.pidfile, 'w')
    f.write(str(os.getpid()))
    
def destroy_pid_file():
    if HandleMain.pidfile is not None:
        os.remove(HandleMain.pidfile)

def main(options):
    config = ConfigParser.SafeConfigParser()
    config.read(options.config_file)
    
    ## From now we can set the application to use a different user id and group id
    ## much better for security reasons
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')
    
    # The detected FTP server IP will be put in this queue waiting the
    # update coordinator to handle them
    ftpserver_queue = Queue(100)

    # Configure the sniffer task and run it in a different thread
    blacklist = str(config.get('indexer', 'blacklist', '')).split(',')
    valid_ip_pattern = config.get('indexer', 'valid_ip_pattern')
    scanner_interval = config.getint('indexer', 'scanner_interval')
    subnet = config.get('indexer', 'subnet')

    if options.clean:
        s = 'Do you really want to clean ftpvista {clean: %s} (make sure there is no running instances of FTPVista) ? [y/N] : ' % options.clean
        fct = None
        if options.clean == 'all':
            fct = clean_all
        elif options.clean == 'db':
            fct = clean_db
        elif options.clean == 'player':
            fct = clean_player
        elif options.clean == 'index':
            fct = clean_index
        else:
            raise Exception ("Invalid value %s for parameter --clean" % options.clean)
        result = raw_input(s)
        if result.upper() == 'Y':
            fct(config)
        return 0
    
    """Daemonize FTPVista"""
    if options.daemon:
        #Context
        HandleMain.context = daemon.DaemonContext(
            working_directory = config.get('indexer', 'working_directory')
        )
        
        #Mapping signals to methods
        HandleMain.context.signal_map = {
            signal.SIGTERM: sigterm_handler,
            signal.SIGHUP: sigterm_handler,
            signal.SIGINT: sigterm_handler,
            #signal.SIGUSR1: reload_program_config,
        }
        HandleMain.context.detach_process = True
        HandleMain.context.sigterm_handler = sigterm_handler
        HandleMain.context.open()
    else:
        signal.signal(signal.SIGTERM, sigterm_handler)
        signal.signal(signal.SIGHUP, sigterm_handler)
        signal.signal(signal.SIGINT, sigterm_handler)

    try:
        if options.only_check_online:
            if options.daemon:
                create_pid_file(config.get('online_checker', 'pid'))
                HandleMain.flock = lockfile.FileLock(config.get('online_checker', 'pid'))
                if HandleMain.flock.is_locked():
                    print ("Already launched ... exiting")
                    sys.exit(3)
                HandleMain.flock.acquire()
            OwnedProcess(target=check_online, args=(config,)).start()
        else:
            if options.daemon:
                create_pid_file(config.get('indexer', 'pid'))
                HandleMain.flock = lockfile.FileLock(config.get('indexer', 'pid'))
                if HandleMain.flock.is_locked():
                    print ("Already launched ... exiting")
                    sys.exit(2)
                HandleMain.flock.acquire()
            OwnedProcess(uid=uid, gid=gid, target=main_daemonized, args=(config, ftpserver_queue)).start()
            OwnedProcess(target=sniffer_task, args=(ftpserver_queue, blacklist, valid_ip_pattern, subnet, scanner_interval)).start()
        OwnedProcess.joinall()
    except Exception as e:
        logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
            filename=config.get('logs', 'main'))
        log = logging.getLogger('ftpvista.main')
        log.error('Error in main : %s', traceback.format_exc())
        close_daemon()
        raise

if __name__ == '__main__':
    parser = OptionParser(version="FTPVista 3.0")
    
    parser.add_option("-c", "--config", dest="config_file", metavar="FILE", default='/home/ftpvista/ftpvista3/ftpvista.conf', help="Path to the config file")
    parser.add_option("-d", "--daemon", action="store_true", dest="daemon", default=True, help="Run FTPVista as a Daemon")
    parser.add_option("--no-daemon", action="store_false", dest="daemon", help="Don't run FTPVista as a Daemon")
    parser.add_option("-o", "--only-check-online", action="store_true", dest="only_check_online", help="Launch only online server checking module")
    parser.add_option("--clean", choices=["db","player","index","all"], help="Empty the index, or one of the database, or everything !")
    
    (options, args) = parser.parse_args()
    
    main(options)
