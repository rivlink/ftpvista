#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import configparser
import argparse
import socket
import os
import sys
import traceback
import shutil
from colorama import init as colorama_init, Fore
from datetime import timedelta
from multiprocessing import Queue
from ftpvista.index import Index, IndexUpdateCoordinator
from ftpvista.multiprocess import OwnedProcess
from ftpvista import persist as ftpvista_persist
from ftpvista.sniffer import *

os.environ['TZ'] = 'CET'


def sniffer_task(queue, blacklist, subnet, scanner_interval):
    # create an ARP sniffer for discovering the hosts
    # sniffer = ARPSniffer()
    sniffer = ARPScanner(subnet, scanner_interval)
    # Bind the sniffer to a filtering pipeline to discard uninteresting IP
    apipeline = build_machine_filter_pipeline(queue, blacklist, subnet, drop_duplicate_timeout=10*60)
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

    server = persist.get_server_by_ip(sserver, False)
    if server is not None:
        log.debug('Server found for deletion. Starting process.')
        persist.delete_server(server)
        log.info('Server %s successfully deleted', sserver)
    else:
        log.info('No server found corresponding to %s', sserver)


def clean_all(config, args):
    clean_db(config, args)
    clean_index(config)


def clean_db(config, args):
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
        init_django(config, args)
    else:
        log.info("No database : skipping.")


def init_django(config, args):
    sys.stdin = open(0)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ftpvistasite.settings")
    os.environ.setdefault("CONFIG_PATH", args.config_file)
    from django.core.management import execute_from_command_line
    print(Fore.BLUE + 'Django database' + Fore.BLUE)
    execute_from_command_line(['migrate', 'migrate'])
    print(Fore.BLUE + 'Django admin user' + Fore.BLUE)
    execute_from_command_line(['migrate', 'createsuperuser'])


def clean_index(config, _):
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
    handler = logging.FileHandler(config.get('logs', 'online_checker'), encoding='utf-8')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        handlers=[handler])
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


def main_process(config, ftpserver_queue):
    handler = logging.FileHandler(config.get('logs', 'main'), encoding='utf-8')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        handlers=[handler])

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
    update_coordinator = IndexUpdateCoordinator(persist, index, timedelta(hours=min_update_interval), max_depth)

    log.info('Init done, running the update coordinator ...')
    while True:
        # Wait for an FTP server to be detected and update it
        update_coordinator.update_server(ftpserver_queue.get())


def launch(config, func, args, category='indexer'):
    uid = config.getint(category, 'uid')
    gid = config.getint(category, 'gid')
    OwnedProcess(uid=uid, gid=gid, target=func, args=args).start()


def _q(text):
    result = input("%s [y/N] " % text)
    return result.upper() == 'Y'


def main(args):
    config = configparser.SafeConfigParser()
    config.read(args.config_file)

    if args.action == 'clean':
        question = Fore.YELLOW + 'Do you really want to clean ftpvista {clean: %s}%s (make sure there is no running instances of FTPVista) ?' % (args.subject, Fore.RESET)
        fct = None
        if args.subject == 'all':
            fct = clean_all
        elif args.subject == 'db':
            fct = clean_db
        elif args.subject == 'index':
            fct = clean_index
        else:
            raise Exception("Invalid value %s" % args.subject)
        if _q(question):
            launch(config, fct, (config, args))
        return 0
    elif args.action == 'delete':
        if _q(Fore.YELLOW + 'Do you really want to delete server %s ?' + Fore.RESET % args.server):
            launch(config, delete_server, (config, args.server))
        return 0
    elif args.action == 'init':
        launch(config, init_django, (config, args), 'online_checker')

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
    scanner_interval = config.getint('indexer', 'scanner_interval')
    subnet = config.get('indexer', 'subnet')

    try:
        if args.action == 'start':
            OwnedProcess(uid=uid, gid=gid, target=main_process, args=(config, ftpserver_queue)).start()
            OwnedProcess(target=sniffer_task, args=(ftpserver_queue, blacklist, subnet, scanner_interval)).start()
        elif args.action == 'start-oc':
            OwnedProcess(target=check_online, args=(config,)).start()
        OwnedProcess.joinall()
    except Exception:
        handler = logging.FileHandler(config.get('logs', 'main'), encoding='utf-8')
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                            handlers=[handler])
        log = logging.getLogger('ftpvista.main')
        log.error('Error in main : %s', traceback.format_exc())
        raise


def init():
    colorama_init()
    dirname = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="FTPVista 4.0")
    parser.add_argument("-c", "--config", dest="config_file", metavar="FILE", default=os.path.join(dirname, 'ftpvista.conf'), help="Path to the config file")
    subparsers = parser.add_subparsers(dest='action')
    # init
    subparsers.add_parser('init', help='Initialize FTPVista database')
    # start
    subparsers.add_parser('start', help='Start FTPVista')
    # start-oc
    subparsers.add_parser('start-oc', help='Start online checker')
    # clean
    parser_clean = subparsers.add_parser('clean', help='Empty the index, or the database, or everything !')
    parser_clean.add_argument("subject", choices=["db", "index", "all"], help="Empty the index, or the database, or everything !")
    # delete
    parser_delete = subparsers.add_parser('delete', help='Manually delete a server from the index')
    parser_delete.add_argument("server", help="IP of the server to delete")

    args = parser.parse_args()

    if os.getuid() != 0:
        print("You must be root in order to run FTPVista. Exiting.")
        exit(1)

    return main(args)

if __name__ == '__main__':
    init()
