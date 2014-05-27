"""
AWSDNS - DNS for EC2 instances in Amazon Web Services

Resolver - the "meat" of the server
"""

from twisted.internet.protocol import Factory, Protocol
from twisted.names import client, server, dns, error
from twisted.internet import defer, threads

import datetime

from twisted.python import log, failure

import boto.ec2

from awsdns.cache import ResolverCache

import ConfigParser

import tx_logging

class EC2Resolver(client.Resolver):
    """
    Looks up given host by looking at the EC2 'Name' tag, if the it's a 
    forward lookup. Queries EC2 for the private_ip_address field if it's 
    a reverse lookup (configurable via the config file)
    """
    
    _ec2 = None
    
    aws_access_key_id = None
    aws_secret_access_key = None
    aws_region = None
    config = None
    forward_cache = None
    reverse_cache = None
    ttl = None
    autorefresh = None
    log = None
    
    def __init__(self, config, *args, **kwargs):
        self.config = config
        
        self.parse_config()
        
        self._ec2 = boto.ec2.connect_to_region(
            self.aws_region, 
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        self.cache = ResolverCache(self._lookup_wrapper, self.autorefresh)
        
        self.log = tx_logging.getLogger("awsdns:resolver")
        
        client.Resolver.__init__(self, *args, **kwargs)
    
    def parse_config(self):
        """
        Parses the configuration, handles errors, sets defaults.
        """
        
        self.aws_region = self.config.get('awsdns', 'aws_region')
        self.aws_access_key_id = self.config.get('awsdns', 'aws_access_key_id')
        self.aws_secret_access_key = self.config.get('awsdns', 'aws_secret_access_key')
        
        try:
            self.forward_filter = self.config.get('awsdns', 'forward')
        except ConfigParser.NoOptionError:
            self.forward_filter = 'tag:Name'
            
        try:
            self.reverse_filter = self.config.get('awsdns', 'reverse')
        except ConfigParser.NoOptionError:
            self.forward_filter = 'private_ip_address'
        
        try:
            extra = self.config.get('awsdns', 'extra')
            self.extra = extra.split()
        except ConfigParser.NoOptionError:
            self.extra = []
        
        try:
            self.autorefresh = self.config.getboolean('awsdns', 'autorefresh')
        except ConfigParser.NoOptionError:
            self.autorefresh = False
        
        try:
            self.ttl = self.config.getint('awsdns', 'ttl')
        except ConfigParser.NoOptionError:
            self.ttl = 3600
    
    def _tag_or_property(self, instance, check, default=None):
        """
        Given an EC2 instance object, and a property or to check, return the value
        
        If check is a tag:XXXXXX filter, returns the tag value.
        
        Otherwise, assumes check is a property.
        
        Returns default if property or tag doesn't exist.
        """
        if check.startswith("tag:"):
            prefix, tag = check.split(":")
            return instance.tags.get(tag, default)
        else:
            return getattr(instance, check, default)
    
    def create_message(self, instances, name, prop, record=dns.A):
        """
        Construct a message to return to the client.
        
        instances is a reservation list (the output from ec2_connection.get_all_instances)
        name is the query value
        prop is the property to inspect on each instance to return
        record is a constant that indicates what type of record to create in the 
               payload.
        """
        output = ([], [], [])
        
        if not instances:
            self.log.debug("No instances found for '%s'" % (name))
            return output
        
        for instance in instances[0].instances:
            
            value = self._tag_or_property(instance, prop)
            self.log.debug("%s: %s %s" % (name, prop, value))
            if not value:
                continue
            
            if record == dns.A:
                payload = dns.Record_A(str(value))
            elif record == dns.PTR:
                payload = dns.Record_PTR(str(value))
            else:
                raise ValueError, "Record constant '%s' is not supported" % (record)
            
            answer = dns.RRHeader(name, type=record, payload=payload, ttl=self.ttl)
            
            output[0].append(answer)
            
            for extra_prop in self.extra:
                extra_value = self._tag_or_property(instance, extra_prop)
                self.log.debug("%s: %s = %s" % (name, extra_prop, extra_value))
                if extra_value:
                    string = "%s = %s" % (extra_prop, extra_value)
                    extra = dns.Record_TXT(str(string))
                    extra_rr = dns.RRHeader(name, type=dns.TXT, payload=extra, ttl=self.ttl)
                    output[2].append(extra_rr)
        
        return output

        
    def _reverse_ip(self, name):
        """
        Given a in-arpa name, return the IP in the correct order.
        """
        parts = name.split('.')
        parts.reverse()
        ip = ".".join(parts[2:])
        
        return ip
        
    def _lookup_wrapper(self, info):
        name, cls, type = info
        
        d = client.Resolver._lookup(self, name, cls, type, None)
        
        def relookup(failure):
            failure.trap(error.DNSNameError)
            
            if type == dns.PTR:
                ip = self._reverse_ip(name)
                d = threads.deferToThread(self._ec2.get_all_instances, filters={self.reverse_filter: ip})
                d.addCallback(self.create_message, name, self.forward_filter, record=dns.PTR)
            elif type == dns.A:
                d = threads.deferToThread(self._ec2.get_all_instances, filters={self.forward_filter: str(name)})
                d.addCallback(self.create_message, name, self.reverse_filter, record=dns.A)
            else:
                raise ValueError, "Record constant '%s' is not supported" % (type)
                
            return d
            
        def format(message):
            """ 
            Format the output of _lookup so it fits the cache format
            """ 
            return (info, message, self.ttl)
            
        d.addErrback(relookup)
        d.addCallback(format)
        
        return d
        
    def _lookup(self, name, cls, type, timeout):
        self.log.debug("NAME: %s, CLS: %s, TYPE: %s, TIMEOUT: %s" % (name, cls, type, timeout))   
        
        d = self.cache[(name, cls, type)]
        
        return d
