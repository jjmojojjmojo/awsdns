"""
Prototype for the caching mechanism used to avoid redundant calls to AWS

TODO: also cache results from DNS?
"""

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet import defer
from twisted.internet import threads

import pprint, random
import time

class ResolverCache(object):
    """
    Caches/retrieves entries by name (or IP address).
    
    Cleans up after itself - after a given amount of time, the value is removed.
    
    Uses a callback function to retrieve the value if it does not exist in the
    cache.
    
    Callback takes a single argument, the name to look up, and returns a tuple, 
    containing the name, the 'message' (the thing to cache) and a TTL value.
    
    autorefresh - set to True to automatically recall the callback function 
                  whenever the cache item expires.
    """
    
    _cache = None
    callback = None
    autorefresh = False
    
    def __init__(self, callback, autorefresh=False):
        self._cache = {}
        self.callback = callback
        self.autorefresh = autorefresh
    
    def __getdeferred__(self, key):
        """
        Wrap the functionality of __getitem__ such that it can possibly return
        a deferred.
        """
        try:
            print "Found %s" % (key)
            val = self._cache.__getitem__(key)
            return val
        except KeyError:
            print "%s not found - calling callback" % (key) 
            d = defer.maybeDeferred(self.callback, key)
            
            d.addCallback(self.cache)
            return d
    
    def __getitem__(self, key):
        """
        Return a deferred - will be from the cache if it exists, will be the
        result of calling (and caching) the callback if not.
        """
        print "retrieving %s" % (key) 
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
        
        print "Setting %s with TTL %s" % (name, ttl)
        self._cache[name] = message
        
        def remove(name):
            del self._cache[name]
            return name
        
        def refresh(name):
            print "Refreshing entry for %s" % (name)
            self.__getdeferred__(name)
            return name
        
        d = task.deferLater(reactor, ttl, remove, name)
        
        def log(name):
            print "Removed %s from the cache." % (name)
            return name
        
        d.addCallback(log)
        
        if self.autorefresh:
            d.addCallback(refresh)
        
        
        return message
    
    


all_messages = [
    'fake1:56',
    'fake2:32',
    'fake3:32',
    'fake4:94',
    'loaded1:56',
    'loaded2:32',
    'loaded3:32',
    'loaded4:94',
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
    'fake1:56': [('fake1', '56'), 56],
    'fake2:32': [('fake2', '32'), 32],
    'fake3:32': [('fake3', '32'), 32],
    'fake4:94': [('fake4', '94'), 94],
    'loaded1:56': [('loaded1', '56'), 56], 
    'loaded2:32': [('loaded2', '32'), 32],
    'loaded3:32': [('loaded3', '32'), 32],
    'loaded4:94': [('loaded4', '94'), 94],
}

index = 0

def fake_message(key):
    print "In callback for %s" % (key)
    return key, fake_messages[key][0], fake_messages[key][1]

def fake_message_block(key):
    """
    Wrap fake_message in a function that blocks for a few seconds
    """
    def blocker(key):
        time.sleep(3)
        return fake_message(key)
        
    d = threads.deferToThread(blocker, key)
    return d

def fill_cache():
    """
    Fill the cache up with random data, with various TTLs
    """
    cache.cache(['loaded1:56',]+fake_messages['loaded1:56'])
    cache.cache(['loaded2:32',]+fake_messages['loaded2:32'])
    cache.cache(['loaded3:32',]+fake_messages['loaded3:32'])
    cache.cache(['loaded4:94',]+fake_messages['loaded4:94'])
    
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
        
        d = cache[name]
        
        def got(val):
            print "Got %s" % (val,)
            
        d.addCallback(got)
        
        self.index += 1
    
cache = ResolverCache(fake_message_block, True)
    
fill_cache()

l = task.LoopingCall(dump_cache)
l.start(10)
l2 = task.LoopingCall(AccessCache())
l2.start(0.5)

reactor.run()
