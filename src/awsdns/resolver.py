"""
AWSDNS - DNS for EC2 instances in Amazon Web Services

Resolver - the "meat" of the server
"""

from twisted.internet.protocol import Factory, Protocol
from twisted.names import client, server, dns
from twisted.internet import defer, threads

import datetime

from twisted.python import log, failure

import boto.ec2

class EC2Resolver(client.Resolver):
    """
    Looks up given host by looking at the EC2 'Name' tag, if the it's a 
    forward lookup. Queries EC2 for the private_ip_address field if it's 
    a reverse lookup.
    """
    
    _ec2 = None
    
    aws_access_key_id = None
    aws_secret_access_key = None
    aws_region = None
    config = None
    
    def __init__(self, config, *args, **kwargs):
        self.config = config
        
        self.parse_config()
        
        self._ec2 = boto.ec2.connect_to_region(
            self.aws_region, 
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        client.Resolver.__init__(self, *args, **kwargs)
    
    def parse_config(self):
        """
        Parses the configuration, handles errors.
        """
        
        self.aws_region = self.config.get('awsdns', 'aws_region')
        self.aws_access_key_id = self.config.get('awsdns', 'aws_access_key_id')
        self.aws_secret_access_key = self.config.get('awsdns', 'aws_secret_access_key')
        
        self.forward_filter = self.config.get('awsdns', 'forward', 'tag:Name')
        self.reverse_filter = self.config.get('awsdns', 'reverse', 'private_ip_address')
        
        self.extra = self.config.get('awsdns', 'extra', '').split()
    
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
        
        print "OUTPUT FROM CREATE_MESSAGE type %s" % (record)
        
        if not instances:
            print "NO INSTANCES FOUND"
            return output
        
        for instance in instances[0].instances:
            
            value = self._tag_or_property(instance, prop)
            print "VALUE: %s %s" % (prop, value)
            if not value:
                continue
            
            if record == dns.A:
                payload = dns.Record_A(str(value))
            elif record == dns.PTR:
                payload = dns.Record_PTR(str(value))
            else:
                raise ValueError, "Record constant '%s' is not supported" % (record)
            
            answer = dns.RRHeader(name, type=record, payload=payload)
            
            output[0].append(answer)
            
            for extra_prop in self.extra:
                extra_value = self._tag_or_property(instance, extra_prop)
                
                if extra_value:
                    string = "%s = %s" % (extra_prop, extra_value)
                    extra = dns.Record_TXT(str(string))
                    extra_rr = dns.RRHeader(name, type=dns.TXT, payload=extra)
                    output[2].append(extra_rr)
        
        return output
    
    def _EC2Forward(self, name):
        """
        Do a 'forward' lookup - find an EC2 ip address for a given value of
        the Name tag.
        
        returns a deferred.
        
        TODO: make the tag configurable
        TODO: return public ip instead of private.
        TODO: refactor to avoid using deferToThread
        """
        d = threads.deferToThread(self._ec2.get_all_instances, filters={self.forward_filter: str(name)})
        d.addCallback(self.create_message, name, self.reverse_filter, record=dns.A)
        
        return d
        
    def _EC2Reverse(self, address):
        """
        Do a 'reverse' lookup - find an EC2 instance for a given ip address
        """
        # extract just the IP from the apra request
        parts = address.split('.')
        parts.reverse()
        ip = ".".join(parts[2:])
        
        d = threads.deferToThread(self._ec2.get_all_instances, filters={self.reverse_filter: ip})
        d.addCallback(self.create_message, address, self.forward_filter, record=dns.PTR)
        
        return d
        
    def filterAnswers(self, message):
        if message.trunc:
            return self.queryTCP(message.queries).addCallback(self.filterAnswers)
        else:
            if not message.answers:
                query = message.queries[0]
                
                if query.type == dns.A:
                    d = self._EC2Forward(str(query.name))
                    
                elif query.type == dns.PTR:
                    d = self._EC2Reverse(str(query.name))
                
                def merge_results(message_tup):
                    message_tup[0].extend(message.answers)
                    message_tup[1].extend(message.authority)
                    message_tup[2].extend(message.additional)
                    
                    return message_tup
                
                d.addCallback(merge_results)
                
                return d
            
        return (message.answers, message.authority, message.additional)
