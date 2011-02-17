# -*- coding: utf-8 -*-
"""
    harvester.py
    ~~~~~~~~~~~~

    Basic OAI-PMH harvesting utilities.

    :copyright: Copyright 2011 Mathias Loesch.
"""
import time
from time import sleep
import hashlib
import pickle
from itertools import chain
import urllib2 
from urllib2 import HTTPError, URLError, Request
from urllib import urlencode
from StringIO import StringIO

from oval import __version__ as ovalversion

CACHE = {}
    
# Caching
def is_obsolete(entry, duration):
    return time.time() - entry['time'] > duration
    
    
def compute_key(function, args, kw):
    key = pickle.dumps((function.func_name, args, kw))
    return hashlib.sha1(key).hexdigest()
    
def memoize(duration=10):
    def _memoize(function):
        def __memoize(*args, **kw):
            key = compute_key(function, args, kw)
            
            #do we have it?
            if (key in CACHE and
                not is_obsolete(CACHE[key], duration)):
                return CACHE[key]['value']
            #computing
            result = function(*args, **kw)
            CACHE[key] = {
                            'value': result,
                            'time': time.time()
            }
            return result
        return __memoize
    return _memoize
    
@memoize(60)
def request_oai(base_url, verb, retries=5,**kw):
    """
        Perform request to base_url with verb and OAI args. Return file like.
        Note that "from" is a reserved word in Python; use "_from" instead.
    """
    params = kw
    params['verb'] = verb
    # from is a reserved word in Python; use _from instead
    if "_from" in params.keys():
        params['from'] = params['_from']
        del params['_from']
    data = urlencode(params)
    request = Request(base_url)
    request.add_header('User-Agent', 'oval/%s' % ovalversion)
    request.add_data(data)
    #url = base_url + urlencode(params)
    for i in range(retries):
        try:
            remote = urllib2.urlopen(request).read()
            return StringIO(remote)
            break
        except HTTPError, e:
            if e.code == 503:
                try:
                    wait_time = int(e.hdrs.get('Retry-After'))
                except TypeError:
                    wait_time = None
                if wait_time == None:
                    sleep(100)
                else:
                    sleep(wait_time)
            else:
                raise
        except Exception:
            raise