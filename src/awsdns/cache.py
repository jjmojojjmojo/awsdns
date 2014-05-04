"""
AWSDNS - DNS for EC2 instances in Amazon Web Services

Semi-generic caching class.

TODO: persist to disk using something like shelve?
"""

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet import defer

import tx_logging

class ResolverCache(object):
    """
    Caches/retrieves entries by name (or IP address).
    
    Cleans up after itself - after a given amount of time, the value is removed.
    
    Uses a callback function to retrieve the value if it does not exist in the
    cache.
    
    Works like an associative array. If the value is not already cached, 
    the callback is invoked to retrieve it.
    
    Returns a deferred.
    
    Callback takes a single argument, the name to look up, and returns a tuple, 
    containing the name, the 'message' (the thing to cache) and a TTL value.
    
    autorefresh - set to True to automatically re-call the callback function 
                  whenever the cache item expires.
                  
    TODO: assumes the "usual" reactor - support other reactors.
    TODO: debugging log output
    """
    
    _cache = None
    callback = None
    autorefresh = False
    log = None
    
    def __init__(self, callback, autorefresh=False):
        self._cache = {}
        self.callback = callback
        self.autorefresh = autorefresh
        self.log = tx_logging.getLogger("awsdns:cache")
    
    def __getdeferred__(self, key):
        """
        Wrap the functionality of __getitem__ such that it can possibly return
        a deferred.
        """
        try:
            val = self._cache.__getitem__(key)
            self.log.debug("hit: %s" % (key,))
            return val
        except KeyError:
            self.log.debug("miss: %s" % (key,))
            d = defer.maybeDeferred(self.callback, key)
            d.addCallback(self.cache)
            return d
    
    def __getitem__(self, key):
        """
        Return a deferred - will be from the cache if it exists, will be the
        result of calling (and caching) the callback if not.
        """
        d = defer.maybeDeferred(self.__getdeferred__, key)
        
        return d
                
    def __setitem__(self, key, val):
        raise NotImplemented, "Assignment not supported. Please use cache() or attempt to get a value"
    
    def cache(self, info):
        """
        Set an item in the cache. Pass a single tuple containing the following
        members:
        
        name = the name of the entry (e.g. www.mysite.com, 1.1.168.192.in-arpa)
        message = a tuple of lists (the output of EC2Resolver.create_message)
        ttl = time to live, in seconds
        """
        name, message, ttl = info
        self._cache[name] = message
        
        def remove(name):
            self.log.debug("Removing %s" % (name,))
            del self._cache[name]
            return name
        
        def refresh(name):
            self.log.debug("Refreshing %s" % (name,))
            self.__getdeferred__(name)
            return name
        
        d = task.deferLater(reactor, ttl, remove, name)
        
        if self.autorefresh:
            d.addCallback(refresh)
        
        return message
