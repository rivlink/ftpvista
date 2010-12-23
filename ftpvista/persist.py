# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import time

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref
from sqlalchemy.orm.exc import NoResultFound

from utils import Servers
import nmap_scanner

def never_date():
    """Helper that returns a DateTime object pointing to Epoch.

    This value is used as 'Never'."""
    return datetime.fromtimestamp(0)

def build_player_tables(meta):
    artist = Table(
        'artist', meta,
        Column('id', Integer, primarey_key=True),
        Column('name', String(100), nullable=False, unique=True),
        mysql_engine='InnoDB'
    )
    album = Table(
        'album', meta,
        Column('id', Integer, primarey_key=True),
        Column('artist_id', Integer, ForeignKey("artist.id"), nullable=False),
        Column('name', String(100), nullable=False),
        mysql_engine='InnoDB'
    )
    genre = Table(
        'genre', meta,
        Column('id', Integer, primarey_key=True),
        Column('name', String(100), nullable=False, unique=True),
        mysql_engine='InnoDB'
    )
    track = Table(
        'track', meta,
        Column('id', Integer, primarey_key=True),
        Column('uripath', String(255), nullable=False),
        Column('genre_id', Integer, ForeignKey("genre.id")),
        Column('album_id', Integer, ForeignKey("album.id")),
        Column('name', String(100), unique=True, nullable=False),
        Column('duration', Integer),
        Column('year', Integer),
        Column('bitrate', String(10)),
        Column('frequency', String(10)),
        Column('lyrics', sqlalchemy.dialects.mysql.base.TEXT),
        Column('trackno', Integer),
        mysql_engine='InnoDB'
    )
    return artist, album, genre, track

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

class Artist:
    def __init__(self, name):
        self.name = name

class Album:

    def __init__(self, name, artist_id):
        self.name = name
        self.artist_id = artist_id

class Genre:
    def __init__(self, name):
        self.name = name

class Track:

    def __init__(self, name, uripath, genre_id, album_id, duration=0, year=0, bitrate='', frequency='', lyrics='', trackno=''):
        self.name = name
        self.uripath = uripath
        self.album_id = album_id
        self.genre_id = genre_id
        self.duration = duration
        self.year = year
        self.bitrate = bitrate
        self.frequency = frequency
        self.lyrics = lyrics
        self.trackno = trackno

    def get_genre_id(name):


    def get_album_id(name, artist):


class FTPServer (object):
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
        return (self.last_seen + timedelta(minutes=10)) >= datetime.now()

    def get_online_class(self):
        if self.is_online():
            return "online"
        return "offline"

class FTPVistaPersist(object):
    def __init__(self, db_uri, rivplayer_uri):
        self.engine = create_engine(db_uri)
        self.engine_player = create_engine(rivplayer_uri)
        self.meta = MetaData(self.engine)
        self.meta_player = MetaData(self.engine_player)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        Session_player = sessionmaker(bind=self.engine_player)
        self.session_player = Session_player()

        self.servers = build_tables(self.meta)

        self.artist, self.album, self.genre, self.track = build_player_tables(self.meta_player)

        try:
            mapper(FTPServer, self.servers)
            mapper(Artist, self.artist)
            mapper(Album, self.album)
            mapper(Genre, self.genre)
            mapper(Track, self.track)
        except ArgumentError:
            pass

    def initialize_store(self):
        self.meta.create_all()

    def add_track(self, name, uripath, artist, genre, album, duration=0, year=0, bitrate='', frequency='', lyrics='', trackno=''):
        try:
            artist_id, = self.session_player.Query(Artist.id).filter_by(name=artist).one()
        except NoResultFound, e:
            new_artist = Artist(artist)
            self.session_player.add(new_artist)
            self.session_player.commit()
            artist_id = new_artist.id

        try:
            album_id, = self.session_player.Query(Album.id).filter(name=album).filter(artist_id=artist_id).one()
        except NoResultFound, e:
            new_album = Album(album, artist_id)
            self.session_player.add(new_album)
            self.session_player.commit()
            album_id = new_album.id

        try:
            genre_id, = self.session_player.Query(Genre.id).filter(Genre.name==genre).one()
        except NoResultFound, e:
            new_genre = Genre(genre)
            self.session_player.add(new_genre)
            self.session_player.commit()
            genre_id = new_genre.id

        self.session_player.add(Track(name, uripath, genre_id, album_id, duration, year, bitrate, frequency, lyrics, trackno))
        self.session_player.commit()

    def get_server_by_ip(self, ip_addr):
        server = self.session.query(FTPServer).filter_by(ip=ip_addr).first()

        if server == None:
            server = FTPServer(ip_addr)
            self.session.add(server)
            self.session.commit()

        return server

    def get_server(self, server_id):
        server = self.session.query(FTPServer).filter_by(id=server_id).first()
        return server

    def get_servers(self):
        return self.session.query(FTPServer).all()

    def launch_online_checker(self, interval=300):
        """Launch a check every 'interval' (in seconds) to verify if servers in database are online"""
        self.log = logging.getLogger('online_check.nmaps')
        self._scanner = nmap_scanner.FTPFilter()

        while True:
            self.check()
            time.sleep(int(interval))

    def check(self):
        servers = self.get_servers()
        for server in servers:
            if self._scanner.is_ftp_open(server.get_ip_addr()):
                last_seen = server.last_seen
                server.update_last_seen()
                self.log.info('Server %s is online. Last seen value was %s' % (server.get_ip_addr(), last_seen))
        self.save()
        self.log.info('Online information saved !')

    def save(self):
        self.session.commit()