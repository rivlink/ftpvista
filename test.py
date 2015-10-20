#!/usr/bin/env python3
from ftpvista.test import test_id3stage
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import sys


def start_ftp_server():
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous("ftpvista/test")
    handler = FTPHandler
    handler.authorizer = authorizer
    server = FTPServer(("127.0.0.1", 2121), handler)
    server.serve_forever()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'server':
        start_ftp_server()
    else:
        print("Launching test sequence")
        test_id3stage.test("127.0.0.1:2121", "ftpvista/test")
