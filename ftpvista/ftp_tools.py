# -*- coding: utf-8 -*-

import socket
import logging


class FTPTools:
    def __init__(self):
        self.log = logging.getLogger('ftpvista.ftptools')

    def is_ftp_open(self, addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((addr, 21))
        return result == 0
