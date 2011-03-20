# -*- coding: utf-8 -*-
"""FTP scanning layer, used to sweep FTP servers for data.
"""

import ftplib
import os.path
import logging
import socket
import re
from datetime import datetime

from utils import to_unicode

class TooDeepError(Exception):
    def __init__(self, depth, path):
        self.depth = depth
        self.path = path

    def __str__(self):
        return 'Too deep (%d levels!). Stopping at %s' % (self.depth, self.path)


class FTPScanner(object):
    def __init__(self, host, ftp_class=ftplib.FTP):
        self.host = host
        self.ftp_class = ftp_class
        self.log = logging.getLogger('ftpvista.scanner.%s'
                                     % self.host.replace('.', '_'))

        self.DATE_WITH_YEAR_PATTERN = re.compile(r'''
                                                 [a-zA-Z]{3}\s{1,2}
                                                 [0-9]{1,2}\s{1,2}
                                                 [0-9]{4}''',
                                                 re.VERBOSE)

        self.DATE_WITH_TIME_PATTERN = re.compile(r'''
                                                 [a-zA-Z]{3}\s{1,2}
                                                 [0-9]{1,2}\s{1,2}
                                                 [0-9]{2}:[0-9]{2}''',
                                                 re.VERBOSE)

	
    def parse_permissions(self, permissions):
        """Determine whether permissions are interesting.
        
            - Updated 2010-10-13 - by Magne
            Permissions of user "other" (3 first bits of permission) do not corresponds
            to permissions of the anonymous user logged into the FTP.
            To check if a directory is readable, we must try to open it (yeah it sucks !).
            To check if a file is readable, we must try to download it (in order to avoid to long
            scans, this check is not completed, and all files listed are supposed to be readable).

        If the permissions represent a directory, return (True,
        enterable), where enterable is always True.

        If the permissions represent a file, return (False, readable),
        where readable is always True.

        If the permissions represent a symlink, return (False, False),
        indicating that it should be ignored.
        """
        
        if permissions[0] == 'l':
            return False, False

        return (permissions[0] == 'd'), True

    def parse_date(self, date):
        if re.match(self.DATE_WITH_YEAR_PATTERN, date):
            return datetime.strptime(date, '%b %d %Y')

        elif re.match(self.DATE_WITH_TIME_PATTERN, date):
            date = datetime.strptime(date, '%b %d %H:%M')

            # the default value for the year is 1900
            return date.replace(datetime.now().year)

        else:
            self.log.warn('Unknown date format : %r', date)
            return None


    def connect(self):
        self.ftp = self.ftp_class(self.host)
        self.ftp.login()
        self.ftp.set_pasv(True)

    def disconnect(self):
        self.ftp.quit()

    def list_files(self, dir):
        extra_dirs = []
        files = []

        def parse_line(line):
            try:
                data = line.split(None, 8)
                permissions, _, uid, gid, size, date1, date2, date3, filename = data
            except ValueError:
                return
            is_dir, interesting = self.parse_permissions(permissions)
            full_path = os.path.join(dir, filename)

            if interesting:
                if is_dir:
                    extra_dirs.append(full_path)
                else:
                    try:
                        size = int(size)
                    except ValueError:
                        return
                    # FIXME : and what if the date is invalid ?
                    # TODO : splitting the string and then joining it sux balls
                    date = self.parse_date(' '.join([date1, date2, date3]))

                    files.append((to_unicode(full_path), size, date))
            else:
                self.log.warning('Path %s not indexed due '
                                 'to permission/type problems.' % full_path)

        self.ftp.cwd(dir)
        self.ftp.dir(parse_line)

        return files, extra_dirs

    def _scan(self, ignores, max_depth):
        ignores = ignores or []
        ignores = set(ignores)

        self.connect()

        dirs = set([('/', 0)])          # (path, depth) we need to process
        visited = set()                 # paths already processed
        files = []

        while len(dirs) > 0:
            try:
                cwd, depth = dirs.pop()
                visited.add(cwd)

                if cwd in ignores:
                    self.log.info('Skipping %s' % cwd)
                    continue
                
                if cwd in visited:
                     self.log.warn('Loop detected, %s was already visited'% cwd)
                    continue
                
                cwd_files, cwd_dirs = self.list_files(cwd)

                if depth < max_depth:
                    for d in cwd_dirs:
                        dirs.add((d, depth+1))
                else:
                    self.log.error('The path is too deep (%d levels)' % depth)
                    self.log.error('Stopping at %s' % cwd)
                    self.log.error('Probably an ill-configured server.')
                    raise TooDeepError(depth, cwd)
                    
                files.extend(cwd_files)

                self.log.debug('%d directories left to scan' % len(dirs))
            except ftplib.all_errors, e:
                self.log.error("Okay, got an exception here.")
                self.log.error("Trying to reconnect and continue.")
                self.log.error("Error: %s" % e)
                self.log.error(e.__class__)
                self.connect()

        self.disconnect()
        return files

    def scan(self, ignores=None, max_depth=50):
        self.log.info('Starting FTP scan.')
        try:
            files = self._scan(ignores, max_depth)
            self.log.info('Scan complete.')
            return files
        except ftplib.error_perm, e:
            self.log.error('Permission error during scan, '
                            'probably couldn\'t log in.')
            self.log.error('Error was: %s' % e)
            self.log.error('Scan terminated.')
        except ftplib.all_errors, e:
            self.log.error('Error while scanning FTP: %s' % e)
            self.log.error('Scan terminated.')
