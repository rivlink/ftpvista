# -*- coding: utf-8 -*-
MOST_POPULAR_ENCODINGS = ['utf_8', 'ascii', 'iso8859_2']

import locale
import os

def to_unicode(text, charset=None):
    """Convert a `str` object to an `unicode` object.

    If `charset` is given, we simply assume that encoding for the text,
    but we'll use the "replace" mode so that the decoding will always
    succeed.
    If `charset` is ''not'' specified, we'll make some guesses, first
    trying the UTF-8 encoding, then trying the locale preferred encoding,
    in "replace" mode. This differs from the `unicode` builtin, which
    by default uses the locale preferred encoding, in 'strict' mode,
    and is therefore prompt to raise `UnicodeDecodeError`s.

    Because of the "replace" mode, the original content might be altered.
    If this is not what is wanted, one could map the original byte content
    by using an encoding which maps each byte of the input to an unicode
    character, e.g. by doing `unicode(text, 'iso-8859-1')`.
    """
    if not isinstance(text, str):
        if isinstance(text, Exception):
            # two possibilities for storing unicode strings in exception data:
            try:
                # custom __str__ method on the exception (e.g. PermissionError)
                return unicode(text)
            except UnicodeError:
                # unicode arguments given to the exception (e.g. parse_date)
                return ' '.join([to_unicode(arg) for arg in text.args])
        return unicode(text)
    if charset:
        return unicode(text, charset, 'replace')
    else:
        try:
            for encoding in MOST_POPULAR_ENCODINGS:
                return unicode(text, encoding)
        except UnicodeError:
            pass

        return unicode(text, locale.getpreferredencoding(), 'replace')

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
        if Servers.correspondences == None:
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

