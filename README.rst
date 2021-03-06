============================================================================
AWSDNS - Really Simple DNS For Virtual Private Clouds In Amazon Web Services
============================================================================

A simple, highly configurable DNS server that queries AWS for information when
it can't resolve a name.

Inspired by http://notmysock.org/blog/hacks/a-twisted-dns-story.html

.. warning::
   This application is under heavy development, and shouldn't be used in a production environment! :)


Installation
============
This package is distributed as a python egg. For evaluation purposes, you'll likely want to use the development buildout. See `Using The Buildout`_ below for details.

To install into your system, run the following command (assuming you have a unix-like os, only tested under Ubuntu 13.10):

::
    
    $ sudo python setup.py install
    
At this point you'll have an executable called "awsdns" that you can run.

Init.d
------
TODO - instructions/example script for running on boot.

Using This DNS Server In Your VPC
=================================
TODO - it's possible to set up an instance and use your own DNS server, so that all of the instances brought up will use it by default.

Config File
===========
The configuration file (awsdns.ini) can be located in one of the following locations:

* the current working directory.
* /etc/
* your home directory (~/)

More documentation is coming, but here's an example file:

::
    
    [awsdns]
    dns_server = x.x.x.x        
    aws_access_key_id = YYYYYYYYYYYYYYYYYYYY
    aws_secret_access_key = ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
    aws_region = us-east-1
    forward = tag:Name
    reverse = private_ip_address
    extra = 
        tag:Class
        id
        key_pair
    loglevel = debug
    autorefresh = false
    

The aws_* options should be self-explanatory. 

The forward, reverse and extra options correspond to either tags (prefixed with "tag:") or names of EC2 instance attributes. 

Note that attributes correspond to attributes returned by boto, as outlined here: http://boto.readthedocs.org/en/latest/ref/ec2.html#module-boto.ec2.instance

dns_server
    A DNS server to use for initial lookups - AWS is only consulted if the initial lookup returns 0 results.

forward
    The tag/attribute to search by, when doing a *forward* lookup. Defaults to 'tag:Name', the defacto standard way of naming an EC2 instance.
    
reverse
    The tag/attribute to search by, when doing a *reverse* lookup. Expected to be an IP address. Defaults to 'private_ip_address' - the only other useful value here might be 'ip_address', the public IP.
    
extra
    A list, separated by whitespace, of tags/attributes to return in the 'extra' section of any response. These will be returned as TXT records, loosly conforming to `RFC 1464 <www.rfc-base.org/txt/rfc-1464.txt>`_.
    
loglevel
    One of 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG' (case insensitive). Sets the level of logging output. Logging is done to STDOUT. Defaults to 'info'.
    
autorefresh
    Boolean. Set to *true* to automatically refresh (hit AWS again) values when they expire. If *false*, expired values are only refreshed when they are requested again. This was implemented due to the considerable delay that the AWS API can impart to a request. This way, subsequent requests for the same data will always be up to date and take roughly the same amount of time.
    
ttl
    Integer. Number of seconds to cache information from AWS once it's been retrieved.
    
Using The Buildout
==================
For evaluation or development purposes, this repository comes with a zc.buildout sandbox. 

To use, run the following commands (note you may need to install the python-dev and build-essential packages or equivalent prior to running these commands):

::
    
    $ python bootstrap.py
    $ bin/buildout
    
At that point the executable will be in the bin directory.

Example Output
==============
Using the example config above, here's some example output.

Forward
-------
::
    
    $ dig @gtk-dev2 bootstrapper-test
    
    ; <<>> DiG 9.8.3-P1 <<>> @gtk-dev2 bootstrapper-test
    ; (1 server found)
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 40769
    ;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 1, ADDITIONAL: 2
    
    ;; QUESTION SECTION:
    ;bootstrapper-test.		IN	A
    
    ;; ANSWER SECTION:
    bootstrapper-test.	0	IN	A	172.31.31.48
    
    ;; AUTHORITY SECTION:
    .			66115	IN	SOA	a.root-servers.net. nstld.verisign-grs.com. 2014042901 1800 900 604800 86400
    
    ;; ADDITIONAL SECTION:
    bootstrapper-test.	0	IN	TXT	"tag:Class = test"
    bootstrapper-test.	0	IN	TXT	"id = i-d20eee82"
    
    ;; Query time: 499 msec
    ;; SERVER: 192.168.1.109#53(192.168.1.109)
    ;; WHEN: Tue Apr 29 18:59:44 2014
    ;; MSG SIZE  rcvd: 183
    
Reverse
-------
::
    
    $ dig @gtk-dev2 -x 172.31.31.48
    
    ; <<>> DiG 9.8.3-P1 <<>> @gtk-dev2 -x 172.31.31.48
    ; (1 server found)
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 314
    ;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 1, ADDITIONAL: 2
    
    ;; QUESTION SECTION:
    ;48.31.31.172.in-addr.arpa.	IN	PTR
    
    ;; ANSWER SECTION:
    48.31.31.172.in-addr.arpa. 0	IN	PTR	bootstrapper-test.
    
    ;; AUTHORITY SECTION:
    31.172.in-addr.arpa.	10800	IN	SOA	localhost. nobody.invalid. 1 3600 1200 604800 10800
    
    ;; ADDITIONAL SECTION:
    48.31.31.172.in-addr.arpa. 0	IN	TXT	"tag:Class = test"
    48.31.31.172.in-addr.arpa. 0	IN	TXT	"id = i-d20eee82"
    
    ;; Query time: 818 msec
    ;; SERVER: 192.168.1.109#53(192.168.1.109)
    ;; WHEN: Tue Apr 29 19:00:49 2014
    ;; MSG SIZE  rcvd: 190
    
TODO/Gotchas
============

This section contains notes about the current state of the application.



DeferToThread Used
------------------
boto is a blocking library for most tasks. As a stop-gap, deferToThread is used to get around this. A seemingly defunct library, txaws, is available in PyPi, but it doesn't work with the current AWS API.

Before this can be used in production, this needs to be addressed. Specifically, txaws needs to be updated and utilized, or an alternative, non-blocking call to the EC2 API needs to be written.

Load Testing
------------
This server needs to be tested under heavy load.

Cache Manager
-------------
There's utility in being able to manage the cache through a CLI interface or web UI/RESTful API. This way very long TTL values can be used, and refreshed on demand when things are known to have changed.

Caching Of Missing Values
-------------------------
This is just something to keep in mind - the way the cache works, it will cache empty results from EC2. This is good, when a bunch of requests are made for an instance that cannot be found. 

This is bad, however, if lots of independent requests are made for instances that cannot be found - the amount of memory each request takes up is small (it varies depending on how much metadata is returned, but is still quite small), but memory use will grow with lots of bad entries.

What's worse, there is internal throttling and limits put on the AWS API. 

For example, a simple command line such as the following:

::
    
    $ for i in {1..5000}; do dig @192.168.1.109 test2$i; done
    
Will create 5000 bad entries in the cache, and every single request will result in a call out to the API.

Pre-population
--------------
It's possible to warm-up the cache when the program starts by making a single call to the AWS API. This will slow startup (how much depends on the number of instances in your account/region), but would prevent any delays in initial requests.

ELB Support
-----------
It would be useful to also search for the DNS name (which is typically hard to remember) of an ELB, by making a DNS request for the short internal EC2 name. The returned record would be a CNAME.

TODO/Gotchas - FIXED
====================
Authority Record
----------------
The SOA is sent with every request. This is likely unnecessary.

Addressed
~~~~~~~~~
Removed in 0.2 (unreleased)

Caching
-------
AWS API calls can be slow. Caching needs to be implemented ASAP. A front-loading mechanism, which would scan AWS and pre-populate the cache on boot would also be useful.

Done!
~~~~~
Implemented in version 0.2 (unreleased). Pre-population not implemented yet.

Logging
-------
The application should utilize logging, and provide debugging output.

Done!
~~~~~
Implemented in version 0.2 (unreleased).

First pass of debugging output is very minimal.
