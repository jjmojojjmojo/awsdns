"""
AWSDNS - DNS for EC2 instances in Amazon Web Services

Main module - entry points
"""
import os, sys
import ConfigParser

from twisted.internet import reactor
from twisted.names import server, dns

from resolver import EC2Resolver

import logging
from twisted.python import log
from tx_logging.observers import LevelFileLogObserver

import util

def main():
    config = ConfigParser.ConfigParser()
    
    config.read(["/etc/awsdns.ini", os.path.abspath("./awsdns.ini"), os.path.expanduser("~/awsnds.ini")])
    
    # TODO: what happens if we use more than one DNS server?
    resolver = EC2Resolver(
        config,
        servers=[(config.get('awsdns', 'dns_server'), 53)]
    )
    
    f = server.DNSServerFactory(clients=[resolver])
    p = dns.DNSDatagramProtocol(f)
    
    reactor.listenUDP(53, p)
    reactor.listenTCP(53, f)
    
    try:
        loglevel = util.logging_constant(config.get('awsdns', 'loglevel'))
    except ConfigParser.NoOptionError:
        loglevel = logging.INFO
    
    try:
        logfile = config.get('awsdns', 'logfile')
        fh = open("awsdns.log", "a")
    except ConfigParser.NoOptionError:
        fh = sys.stdout
    
    observer = LevelFileLogObserver(fh, loglevel)
    
    log.addObserver(observer)
    
    reactor.run()
