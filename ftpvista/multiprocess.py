# -*- coding: utf-8 -*-

from multiprocessing import Process
import os
import signal

class OwnedProcess(Process):
    """Define a process with a specific UID and GID
    """

    processes = []

    def __init__(self, uid=None, gid=None, group=None, target=None, name=None, args=(), kwargs={}):
        Process.__init__(self, group, target, name, args, kwargs)
        self.uid = uid
        self.gid = gid
        self.target = target
        self.args = args
        OwnedProcess.add(self)

    def run(self):
        if self.gid is not None:
            os.setgid(self.gid)
        if self.uid is not None:
            os.setuid(self.uid)
        self.target(*self.args)

    @staticmethod
    def add(process):
        OwnedProcess.processes.append(process)

    @staticmethod
    def joinall():
        for p in OwnedProcess.processes:
            p.join()

    @staticmethod
    def terminateall():
        for p in OwnedProcess.processes:
            if p.pid is not None:
                os.kill(p.pid, signal.SIGKILL)
