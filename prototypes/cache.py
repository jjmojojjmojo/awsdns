"""
Prototype for the caching mechanism used to avoid redundant calls to AWS

TODO: also cache results from DNS?
"""

from twisted.internet import reactor
from twisted.internet import task

import pprint, random

class ResolverCache(object):
    """
    Caches/retrieves entries by name (or IP address).
    
    Cleans up after itself - after a given amount of time, the value is removed.
    
    Uses a callback function to retrieve the value if it does not exist in the
    cache.
    
    Callback takes a single argument, the name to look up, and returns a tuple, 
    containing the name, the 'message' (the thing to cache) and a TTL value.
    """
    
    _cache = None
    callback = None
    
    def __init__(self, callback):
        self._cache = {}
        self.callback = callback
    
    def __getitem__(self, key):
        print "retrieving %s" % (key) 
        try:
            val = self._cache.__getitem__(key)
        except KeyError:
            print "Not found - calling callback"
            name, val, ttl = self.callback(key)
            self.cache(name, val, ttl)
            
        return val
                
    def __setitem__(self, key, val):
        raise NotImplemented, "Assignment not supported. Please use cache() or attempt to get a value"
    
    def cache(self, name, message, ttl):
        """
        Set an item in the cache.
        
        name = the name of the entry (e.g. www.mysite.com, 1.1.168.192.in-arpa)
        message = a tuple of lists (the output of EC2Resolver.create_message)
        ttl = time to live, in seconds
        """
        print "Setting %s with TTL %s" % (name, ttl)
        self._cache[name] = message
        
        def remove(name):
            del self._cache[name]
            return name
        
        d = task.deferLater(reactor, ttl, remove, name)
        
        def log(name):
            print "Removed %s from the cache." % (name)
        
        d.addCallback(log)
        
    
    


all_messages = [
    'fake1:56',
    'fake2:32',
    'fake3:32',
    'fake4:94',
    'loaded1:56',
    'loaded2:32',
    'loaded3:32',
    'loaded4:94',
]

random.shuffle(all_messages)

fake_messages = {
    'fake1:56': (('hi', 'mom'), 56),
    'fake2:32': (('hi', 'mom'), 32),
    'fake3:32': (('hi', 'mom'), 32),
    'fake4:94': (('hi', 'mom'), 94),
    'loaded1:56': (('hi', 'mom'), 56), 
    'loaded2:32': (('hi', 'mom'), 32),
    'loaded3:32': (('hi', 'mom'), 32),
    'loaded4:94': (('hi', 'mom'), 94),
}

index = 0

def fake_message(key):
    print "In callback for %s" % (key)
    return key, fake_messages[key][0], fake_messages[key][1]

def fill_cache():
    """
    Fill the cache up with random data, with various TTLs
    """
    cache.cache('loaded1:56', ('hi', 'mom'), 56)
    cache.cache('loaded2:32', ('hi', 'mom'), 32)
    cache.cache('loaded3:32', ('hi', 'mom'), 32)
    cache.cache('loaded4:94', ('hi', 'mom'), 94)
    
def dump_cache():
    """
    Display what's in the cache
    """
    print "DUMPING CACHE: ",
    pprint.pprint(cache._cache)
    
    
class AccessCache(object):
    index = 0
    
    def __call__(self):
        """
        Test accessing the cache and adding new stuff to it.
        """
        if self.index >= len(all_messages):
            self.index = 0
        
        name = all_messages[self.index]
        
        print "Grabbing '%s'" % (name)
        print cache[name]
        self.index += 1
    
cache = ResolverCache(fake_message)
    
fill_cache()

l = task.LoopingCall(dump_cache)
l.start(10)
l2 = task.LoopingCall(AccessCache())
l2.start(8)

reactor.run()
