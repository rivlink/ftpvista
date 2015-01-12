# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import time

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.exc import ArgumentError
from sqlalchemy.dialects.mysql import TEXT
import id3reader

from utils import Servers, to_unicode
import ftp_tools

def never_date():
    """Helper that returns a DateTime object pointing to Epoch.
    This value is used as 'Never'."""
    return datetime.fromtimestamp(0)

def build_tables(meta):
    ftpservers = Table(
        'ftpservers', meta,
        Column('id', Integer, primary_key=True),
        Column('ip', String(15), nullable=False, unique=True),
        Column('first_seen', sqlalchemy.types.DateTime(timezone=True), nullable=False, default=datetime.now),
        Column('last_seen', sqlalchemy.types.DateTime(timezone=True), nullable=False, default=datetime.now),
        Column('last_scanned', sqlalchemy.types.DateTime(timezone=True), nullable=False, default=never_date),
        Column('nb_files', Integer, default=0),
        Column('files_size', Integer, default=0)
        )
    return ftpservers

class FTPServer(object):
    def __init__(self, ip_addr):
        self.ip = ip_addr

    def update_last_seen(self, time=None):
        """As default value is evaluated only once, and is shared between calls,
        the 'time' variable must be instanciated each time the method is called"""
        if time == None:
            time = datetime.now()
        self.last_seen = time

    def update_last_scanned(self, time=None):
        """Same as 'update_last_seen' method"""
        if time == None:
            time = datetime.now()
        self.last_scanned = time

    def get_server_id(self):
        return self.id

    def get_ip_addr(self):
        return self.ip

    def get_last_seen(self):
        return self.last_seen

    def get_last_scanned(self):
        return self.last_scanned

    def get_nb_files(self):
        return self.nb_files

    def set_nb_files(self, nb_files):
        self.nb_files = nb_files

    def get_files_size(self):
        return self.files_size

    def set_files_size(self, files_size):
        self.files_size = files_size

    def get_ip_with_name(self):
        return Servers.get_ip_with_name(self.ip)

    def is_online(self):
        return (self.last_seen + timedelta(seconds=310)) >= datetime.now()

    def get_online_class(self):
        if self.is_online():
            return "online"
        return "offline"

class FTPVistaPersist(object):
    def __init__(self, db_uri):
        self.log = logging.getLogger('ftpvista.persist')
        self.engine = create_engine(db_uri, connect_args={'check_same_thread':False})
        self.meta = MetaData(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.servers = build_tables(self.meta)

        self._tools = ftp_tools.FTPTools()
        self.index = None
        try:
            mapper(FTPServer, self.servers)
        except ArgumentError:
            pass

    def set_index(self, index):
        self.index = index

    def initialize_store(self):
        self.meta.create_all()

    def get_server_by_name(self, name):
        ip = Servers.get_ip_from_name(name)
        if ip is not None:
            return self.get_server_by_ip(ip, False)
        return None

    def get_server_by_ip(self, ip_addr, create=True):
        server = self.session.query(FTPServer).filter_by(ip=ip_addr).first()

        if create and server == None:
            server = FTPServer(ip_addr)
            self.session.add(server)
            self.session.commit()

        return server

    def get_server(self, server_id):
        server = self.session.query(FTPServer).filter_by(id=server_id).first()
        return server

    def get_servers(self):
        return self.session.query(FTPServer).all()

    def launch_online_checker(self, interval=300, purgeinterval=30):
        """ Launch a check every 'interval' (in seconds) to verify if servers in database are online.
            If a server have not been seen since 'purgeinterval' days, it is deleted from the index and the database.
        """
        self.log = logging.getLogger('ftpvista.nmaps')
        while True:
            self.check(purgeinterval)
            time.sleep(int(interval))

    def check(self, purgeinterval=None):
        servers = self.get_servers()
        if purgeinterval is not None:
            deltapurgeinterval = timedelta(days=int(purgeinterval))
        for server in servers:
            if self._tools.is_ftp_open(server.get_ip_addr()):
                last_seen = server.last_seen
                server.update_last_seen()
                self.log.info('Server %s is online. Last seen value was %s' % (server.get_ip_addr(), last_seen))
            elif purgeinterval is not None and (server.get_last_seen() + deltapurgeinterval) < datetime.now():
                self.delete_server(server)
        self.save()
        self.log.info('Online information saved !')

    def delete_server(self, server):
        """ Delete server files from index """
        self.index.delete_all_docs(server)
        """ Delete server from DB """
        self.session.query(FTPServer).filter_by(id=server.get_server_id()).delete()
        self.save()

    def save(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

