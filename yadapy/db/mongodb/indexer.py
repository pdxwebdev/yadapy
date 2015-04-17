import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib, inspect
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange
from pymongo import Connection
from node import Node
from yadapy.indexer import Indexer
try:
    from pymongo.objectid import ObjectId
except:
    from bson.objectid import ObjectId

 
class Indexer(Indexer, Node):
    conn = None
    host = None
    port = None
    def __init__(self, *args, **kwargs):
        
        if 'host' in kwargs:
            self.host = kwargs['host'] 
        if 'port' in kwargs:
            self.port = kwargs['port']

        if 'public_key' in kwargs:
            args = [x for x in args]
            args.insert(0, self.getProfileIdentity(kwargs['public_key']))
            
        super(Node, self).__init__(*args, **kwargs)
        
        self.set('data/type', 'indexer', True)