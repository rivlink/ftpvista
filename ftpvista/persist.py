# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import time

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.declarative import declarative_base
from os import path
import re
import id3reader
from urllib import url2pathname

from utils import Servers, to_unicode
import nmap_scanner

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

Base = declarative_base()

class Artist(Base):
    __tablename__ = 'artist'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(254), nullable=False, unique=True)
    
    def __init__(self, name):
        self.name = name

class Album(Base):
    __tablename__ = 'album'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey("artist.id"), nullable=False)
    name = Column(String(254), nullable=False)
    
    def __init__(self, name, artist_id):
        self.name = name
        self.artist_id = artist_id

class Genre(Base):
    __tablename__ = 'genre'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(254), nullable=False, unique=True)
    
    def __init__(self, name):
        self.name = name

class Track(Base):
    __tablename__ = 'track'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    uripath = Column(String(254), nullable=False)
    genre_id = Column(Integer, ForeignKey("genre.id"))
    album_id = Column(Integer, ForeignKey("album.id"))
    name = Column(String(254), nullable=False)
    duration = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    bitrate = Column(String(10), nullable=True)
    frequency = Column(String(10), nullable=True)
    lyrics = Column(sqlalchemy.types.Text, nullable=True)
    trackno = Column(Integer, nullable=True)
    
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

#    def get_genre_id(name):


#    def get_album_id(name, artist):


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
        return (self.last_seen + timedelta(seconds=310)) >= datetime.now()

    def get_online_class(self):
        if self.is_online():
            return "online"
        return "offline"

class FTPVistaPersist(object):
    def __init__(self, db_uri, rivplayer_uri=None):
        self.log = logging.getLogger('ftpvista.persist')
        self.engine = create_engine(db_uri)
        self.meta = MetaData(self.engine)
        if rivplayer_uri is not None:
            self.engine_player = create_engine(rivplayer_uri)
        else:
            self.engine_player = None

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        if rivplayer_uri is not None:
            Session_player = sessionmaker(bind=self.engine_player)
            self.session_player = Session_player()
        else:
            self.session_player = None

        self.servers = build_tables(self.meta)

        try:
            mapper(FTPServer, self.servers)
        except ArgumentError:
            pass
    
    def set_index(self, index):
        self.index = index

    def initialize_store(self):
        self.meta.create_all()
        if self.engine_player is not None:
            Base.metadata.create_all(self.engine_player)
    
    def _clean_tag(self, tag, allow_none = False, type = 'string', default = None, max_len = 254):
        if default is None and allow_none is False:
            if type == 'string':
                default = 'Inconnu'
            elif type == 'integer':
                default = 0
        if tag is None or tag == 'None':
            if allow_none is False:
                return default
            else:
                return None
        tag = to_unicode(tag).strip()
        if tag == '':
            return default
        if type == 'integer' and re.match('\d{1,32}', tag) is None:
            return default
        return tag[:max_len].strip()
        
    
    def add_track(self, name, uripath, artist, genre, album, duration=0, year=0, bitrate='', frequency='', lyrics='', trackno=''):
        name = self._clean_tag(name, default=url2pathname(path.basename(uripath).rsplit('.', 1)[0]))
        artist = self._clean_tag(artist)
        genre = self._clean_tag(genre)
        album = self._clean_tag(album)
        duration = self._clean_tag(duration, type='integer')
        year = self._clean_tag(year, type='integer', max_len=4)
        bitrate = self._clean_tag(bitrate, allow_none=True)
        frequency = self._clean_tag(frequency, allow_none=True)
        lyrics = self._clean_tag(lyrics, allow_none=True, max_len=4096)
        trackno = self._clean_tag(trackno, type='integer')
        
        match = re.match('\((\d{1,3})\)', genre)
        if match is not None:
            id3v1_genre_id = int(match.group(1))
            if id3v1_genre_id >=0 and id3v1_genre_id <= 147:
                genre = id3reader._genres[id3v1_genre_id]
        
        try:
            self.log.debug(u'Adding Music ! Name : ' + to_unicode(name) + u' - Path : ' + to_unicode(uripath) + u' - Artist : ' + to_unicode(artist) + u' - Genre : ' + to_unicode(genre) + u' - Album : ' + to_unicode(album))
        except UnicodeDecodeError:
            pass
        
        try:
            artist_id, = self.session_player.query(Artist.id).filter_by(name=artist).one()
        except NoResultFound, e:
            new_artist = Artist(artist)
            self.session_player.add(new_artist)
            self.session_player.commit()
            artist_id = new_artist.id

        try:
            album_id, = self.session_player.query(Album.id).filter_by(name=album).filter_by(artist_id=artist_id).one()
        except NoResultFound, e:
            new_album = Album(album, artist_id)
            self.session_player.add(new_album)
            self.session_player.commit()
            album_id = new_album.id

        try:
            genre_id, = self.session_player.query(Genre.id).filter(Genre.name==genre).one()
        except NoResultFound, e:
            new_genre = Genre(genre)
            self.session_player.add(new_genre)
            self.session_player.commit()
            genre_id = new_genre.id
            
        try:
            track_id, = self.session_player.query(Track.id).filter(Track.uripath==uripath).one()
        except NoResultFound, e:
            self.session_player.add(Track(name, uripath, genre_id, album_id, duration, year, bitrate, frequency, lyrics, trackno))
            self.session_player.commit()
    
    def del_track(self, uripath):
        self.session_player.query(Track).filter_by(uripath=uripath).delete()
        self.session_player.commit()
    
    def truncate_all(self):
        self.session_player.query(Track).delete()
        self.session_player.query(Album).delete()
        self.session_player.query(Genre).delete()
        self.session_player.query(Artist).delete()
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

    def launch_online_checker(self, interval=300, purgeinterval=30):
        """ Launch a check every 'interval' (in seconds) to verify if servers in database are online.
            If a server have not been seen since 'purgeinterval' days, it is deleted from the index and the database.
        """
        self.log = logging.getLogger('ftpvista.nmaps')
        self._scanner = nmap_scanner.FTPFilter()
        while True:
            self.check(purgeinterval)
            time.sleep(int(interval))

    def check(self, purgeinterval=None):
        servers = self.get_servers()
        if purgeinterval is not None:
            deltapurgeinterval = timedelta(days=int(purgeinterval))
        for server in servers:
            if self._scanner.is_ftp_open(server.get_ip_addr()):
                last_seen = server.last_seen
                server.update_last_seen()
                self.log.info('Server %s is online. Last seen value was %s' % (server.get_ip_addr(), last_seen))
            elif purgeinterval is not None and (server.get_last_seen() + deltapurgeinterval) < datetime.now():
                self.delete_server(server)
        self.save()
        self.log.info('Online information saved !')

    def delete_server(self, server):
        if self.session_player is not None:
            """Delete tracks from player DB """
            self.session_player.query(Track).filter(Track.uripath.startswith('ftp://%s' % server.get_ip_addr())).delete()
            self.session_player.commit()
        """ Delete server files from index """
        self.index.delete_all_docs(server)
        """ Delete server from DB """
        self.session.query(FTPServer).filter_by(id=server.get_server_id()).delete()
        self.save()

    def save(self):
        self.session.commit()