#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import configparser
import argparse
import socket
import os
import sys
import traceback
import shutil
from datetime import timedelta
from multiprocessing import Queue
from ftpvista.index import Index, IndexUpdateCoordinator
from ftpvista.multiprocess import OwnedProcess
from ftpvista import persist as ftpvista_persist
from ftpvista import pipeline
from ftpvista import observer
from ftpvista.sniffer import *

os.environ['TZ'] = 'CET'


def sniffer_task(queue, blacklist, valid_ip_pattern, subnet, scanner_interval):
    # create an ARP sniffer for discovering the hosts
    # sniffer = ARPSniffer()
    sniffer = ARPScanner(subnet, scanner_interval)
    # Bind the sniffer to a filtering pipeline to discard uninteresting IP
    apipeline = build_machine_filter_pipeline(queue, blacklist, valid_ip_pattern, drop_duplicate_timeout=10*60)
    SnifferToPipelineAdapter(sniffer, apipeline)

    # Run sniffer, run ..
    sniffer.run()


def delete_server(config, sserver):
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(message)s')
    log = logging.getLogger('ftpvista.delete_server')
    log.debug('Looking to delete server %s', sserver)

    persist = get_persist(config)
    index = get_index(config, persist)
    persist.set_index(index)

    server = persist.get_server_by_name(sserver)
    if server is None:
        server = persist.get_server_by_ip(sserver, False)
    if server is not None:
        log.debug('Server found for deletion. Starting process.')
        persist.delete_server(server)
        log.info('Server %s successfully deleted', sserver)
    else:
        log.info('No server found corresponding to %s', sserver)


def clean_all(config):
    clean_db(config)
    clean_index(config)


def clean_db(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(message)s')
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
                        format='[%(asctime)s] %(message)s')
    log = logging.getLogger('ftpvista.clean_index')
    log.info('Starting FTPVista cleaning : index')

    index_uri = config.get('index', 'uri')
    if os.path.isdir(index_uri):
        shutil.rmtree(index_uri)
        log.info("Index deleted")
    else:
        log.info("Index not found : skipping.")


def check_online(config):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        filename=config.get('logs', 'online_checker'))
    log = logging.getLogger('ftpvista')
    log.info('Starting online servers checker')

    db_uri = config.get('db', 'uri')
    persist = ftpvista_persist.FTPVistaPersist(db_uri)
    persist.initialize_store()

    index_uri = config.get('index', 'uri')
    index = Index(index_uri, persist)
    persist.set_index(index)

    update_interval = int(config.get('online_checker', 'update_interval'))
    purge_interval = int(config.get('online_checker', 'purge_interval'))

    persist.launch_online_checker(update_interval, purge_interval)


def get_persist(config):
    db_uri = config.get('db', 'uri')
    persist = ftpvista_persist.FTPVistaPersist(db_uri)
    persist.initialize_store()
    return persist


def get_index(config, persist):
    index_uri = config.get('index', 'uri')
    return Index(index_uri, persist)


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
    persist = get_persist(config)

    # Full-text index for storing terms from the files found on the servers
    index = get_index(config, persist)

    # This defines how and at which period to perform updates from the servers
    min_update_interval = config.getint('indexer', 'min_update_interval')

    max_depth = config.getint('indexer', 'max_depth')
    update_coordinator = IndexUpdateCoordinator(
                           persist, index, timedelta(hours=min_update_interval), max_depth)

    log.info('Init done, running the update coordinator ...')
    while True:
        # Wait for an FTP server to be detected and update it
        update_coordinator.update_server(ftpserver_queue.get())


def sigterm_handler(signum, frame):
    close_daemon()


def launch(config, func, args):
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')
    OwnedProcess(uid=uid, gid=gid, target=func, args=args).start()


def main(args):
    config = configparser.SafeConfigParser()
    config.read(args.config_file)

    # From now we can set the application to use a different user id and group id
    # much better for security reasons
    uid = config.getint('indexer', 'uid')
    gid = config.getint('indexer', 'gid')

    # The detected FTP server IP will be put in this queue waiting the
    # update coordinator to handle them
    ftpserver_queue = Queue(100)

    # Configure the sniffer task and run it in a different thread
    blacklist = config.get('indexer', 'blacklist')
    if blacklist is not None:
        blacklist = blacklist.split(',')
    else:
        blacklist = []
    valid_ip_pattern = config.get('indexer', 'valid_ip_pattern')
    scanner_interval = config.getint('indexer', 'scanner_interval')
    subnet = config.get('indexer', 'subnet')

    if args.action == 'clean':
        question = 'Do you really want to clean ftpvista {clean: %s} (make sure there is no running instances of FTPVista) ? [y/N] : ' % args.subject
        fct = None
        if args.subject == 'all':
            fct = clean_all
        elif args.subject == 'db':
            fct = clean_db
        elif args.subject == 'index':
            fct = clean_index
        else:
            raise Exception("Invalid value %s" % args.subject)
        result = input(question)
        if result.upper() == 'Y':
            launch(config, fct, (config,))
        return 0
    elif args.action == 'delete':
        question = 'Do you really want to delete server %s ? [y/N] : ' % args.server
        result = input(question)
        if result.upper() == 'Y':
            launch(config, delete_server, (config, args.server))
        return 0

    try:
        if args.action == 'start':
            OwnedProcess(uid=uid, gid=gid, target=main_daemonized, args=(config, ftpserver_queue)).start()
            OwnedProcess(target=sniffer_task, args=(ftpserver_queue, blacklist, valid_ip_pattern, subnet, scanner_interval)).start()
        elif args.action == 'start-oc':
            OwnedProcess(target=check_online, args=(config,)).start()
        OwnedProcess.joinall()
    except Exception as e:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                            filename=config.get('logs', 'main'))
        log = logging.getLogger('ftpvista.main')
        log.error('Error in main : %s', traceback.format_exc())
        close_daemon()
        raise


def init():
    parser = argparse.ArgumentParser(description="FTPVista 4.0")

    parser.add_argument("-c", "--config", dest="config_file", metavar="FILE", default='/home/ftpvista/ftpvista3/ftpvista.conf', help="Path to the config file")
    subparsers = parser.add_subparsers(dest='action')
    parser_start = subparsers.add_parser('start', help='Start FTPVista')
    parser_start_oc = subparsers.add_parser('start-oc', help='Start Online checker')
    parser_clean = subparsers.add_parser('clean', help='Empty the index, or the database, or everything !')
    parser_clean.add_argument("subject", choices=["db", "index", "all"], help="Empty the index, or the database, or everything !")
    parser_delete = subparsers.add_parser('delete', help='Manually delete a server from the index')
    parser_delete.add_argument("server", help="IP (or name from correspondences file) of the server to delete")

    args = parser.parse_args()
    main(args)

if __name__ == '__main__':
    init()