#!/usr/bin/env python2.4
# -*- coding: utf-8 -*-

"""Use Nmap to search a network for open FTP servers.
"""

import re
import subprocess
import logging

SUDO = '/usr/bin/sudo'
NMAP = '/usr/bin/nmap'

UP_FTP_RE = re.compile(r'^Host: (\d+.\d+.\d+.\d+)\W+Ports: 21/open')

class FTPFilter(object):
    def __init__(self, use_sudo=False, nmap_binary=NMAP,
                 sudo_binary=SUDO) :
        self.log = logging.getLogger('ftpvista.nmap')
        self.use_sudo = use_sudo
        self.nmap_binary = nmap_binary
        self.sudo_binary = sudo_binary

    def is_ftp_open(self, addr) :
        if self.use_sudo:
            cmdline = 'sudo %s -n -sS -p21 -T4 -oG - %s' % (self.nmap_binary,
                                                            addr)
            executable = self.sudo_binary
        else:
            cmdline = 'nmap -n -sT -p21 -T4 -oG - %s' % addr
            executable = self.nmap_binary

        self.log.debug('Executing `%s`' % cmdline)
        nmap = subprocess.Popen(cmdline.split(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, executable=executable)

        for l in nmap.stdout:
            if UP_FTP_RE.match(l.strip()) :
                self.log.debug('FTP Exists !')
                return True
        return False


def ftp_network_scan(ip_range, use_sudo=False,
                     nmap_binary=NMAP, sudo_binary=SUDO):
    """List all active FTP servers on the given IP set.

    It is highly recommended to run this through sudo, as running it
    unprivileged will basically DoS the ARP tables, as well as take a
    very fucking long time."""

    if use_sudo:
        cmdline = 'sudo %s -n -sS -p21 -T4 -oG - --min-hostgroup=2048 %s' % (
            nmap_binary, ip_range)
        executable = sudo_binary
    else:
        cmdline = 'nmap -n -sT -p21 -T4 -oG - --max-hostgroup=16 %s' % ip_range
        executable = nmap_binary

    log.debug('Executing `%s`' % cmdline)
    nmap = subprocess.Popen(cmdline.split(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, executable=executable)

    ftps = []

    for l in nmap.stdout:
        log.debug('NMAP: %s' % l)
        m = UP_FTP_RE.match(l.strip())
        if m:
            ftps.append(m.group(1))

    return ftps
