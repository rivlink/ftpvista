# -*- coding: utf-8 -*-
import locale
import os


class Servers:

    correspondences = None

    @staticmethod
    def fetch_correspondences():
        Servers.correspondences = list()
        directory = os.path.dirname(os.path.realpath(__file__))
        f = open(os.path.join(directory, '..', 'correspondences.ftp'), 'r')
        for line in f.readlines():
            Servers.correspondences.append(line.split('\t'))
        f.close()

    @staticmethod
    def get_correspondences():
        if Servers.correspondences is None:
            Servers.fetch_correspondences()
        return Servers.correspondences

    @staticmethod
    def get_ip_with_name(sIP):
        correspondences = Servers.get_correspondences()
        for ip, surnom in correspondences:
            if sIP == ip:
                return ip + " - " + surnom.strip()
        return sIP

    @staticmethod
    def get_ip_from_name(name):
        name = name.lower()
        correspondences = Servers.get_correspondences()
        for ip, surnom in correspondences:
            if name == surnom.strip().lower():
                return ip
        return None
