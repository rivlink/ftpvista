# -*- coding: utf-8 -*-

import re

from scapy.all import sniff, ARP

import ConfigParser

import observer
import pipeline
from pipeline import Pipeline
from timedcache import TimedCache
import nmap_scanner

import ftpvista

class ARPSniffer (observer.Observable):
    """Finds the connected hosts by sniffing the ARP packets.

        This class uses the Observer/Observable design pattern :
        register an Observer to be notified whenever an IP is found.
    """

    def __init__(self):
        observer.Observable.__init__(self)

    def run(self):
        """Run the sniffer"""
        sniff(filter="arp", prn=self._arp_callback, store=0)

    def _arp_callback(self, pkt):
        if ARP in pkt:
            self.notify_observers(pkt[ARP].psrc)
            self.notify_observers(pkt[ARP].pdst)   # FIXME : is this necessary ?


class SnifferToPipelineAdapter (observer.Observer):
    """Adapter class.

      Connects a sniffer to a pipeline by executing it everytime the sniffer
      notifies for a ip address found.
    """

    def __init__(self, sniffer, pipeline):
        self._sniffer = sniffer
        self._pipeline = pipeline
        sniffer.add_observer(self)

    def update(self, observable, arg):
        if observable is self._sniffer:
            self._pipeline.execute(arg)


class BlacklistFilter (pipeline.Stage):
    """Filter out the addresses from the specified blacklist"""

    def __init__(self, blacklist):
        self._blacklist = set(blacklist)

    def execute(self, ip_addr):
        return ip_addr not in self._blacklist


class ValidAddressFilter (pipeline.Stage):
    """Filter out the addresses not matching a given pattern"""

    def __init__(self, pattern):
        self.VALID_IP_PATTERN = re.compile(pattern)

    def execute(self, ip_addr):
        return re.match(self.VALID_IP_PATTERN, ip_addr) is not None


class DropRecentDuplicateFilter (pipeline.Stage):
    """Filter out the addresses that were seen recently"""

    def __init__(self, timeout):
        self._cache = TimedCache(timeout)

    def execute(self, ip_addr):
        if ip_addr not in self._cache:
            self._cache.add(ip_addr)
            return True
        else:
            return False


class FTPServerFilter (pipeline.Stage):
    """Filter out the machines that dont have a running ftp server
       (that do not listen on the port 21 to be exact)
    """
    def __init__(self):
        self._scanner = nmap_scanner.FTPFilter()

    def execute(self, ip_addr):
        if self._scanner.is_ftp_open(ip_addr):
            persist = ftpvista.get_persist()
            server = persist.get_server_by_ip(ip_addr)
            server.update_last_seen()
            return True
        return False

def build_machine_filter_pipeline(blacklist, valid_addr_pattern,
                                  drop_duplicate_timeout):
    pipeline = Pipeline()
    pipeline.append_stage(BlacklistFilter(blacklist))
    pipeline.append_stage(ValidAddressFilter(valid_addr_pattern))
    pipeline.append_stage(DropRecentDuplicateFilter(drop_duplicate_timeout))
    pipeline.append_stage(FTPServerFilter())

    return pipeline


if __name__ == "__main__" :

    VALID_ADDR_PATTERN = '^10.0.0.1|(10.(6|8|82|83|10|11).\d{0,3}.\d{0,3})$'

    class EchoStage (pipeline.Stage):
        """Print the contexts reaching this stage"""

        def execute(self, ip_addr):
            print "Address : %s" % ip_addr
            return True


    sniffer = ARPSniffer()

    # setup the pipeline and bind it to the sniffer
    pipeline = build_machine_filter_pipeline([], VALID_ADDR_PATTERN, 10 * 60)
    pipeline.append_stage(EchoStage())
    SnifferToPipelineAdapter(sniffer, pipeline)

    # Run sniffer, run ..
    sniffer.run()
