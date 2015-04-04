import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from lib.crypt import encrypt, decrypt
from uuid import uuid4
from node import Node, InvalidIdentity


class FriendNode(Node):
    
    def __init__(self, *args, **kwargs):
        
        if 'identityData' in kwargs:
            identityData = kwargs['identityData']
        else:
            identityData = args[0]
            kwargs['identityData'] = identityData
        
        try:
            newIdentity = args[1]
        except:
            newIdentity = None
        
        if type(kwargs['identityData']) == type(u'') or type(kwargs['identityData']) == type(''):
            identityData = self.getManagedNode(kwargs['identityData'])
        elif type(kwargs['identityData']) == type({}):
            identityData = kwargs['identityData']
        else:
            raise InvalidIdentity("A valid server Identity was not given nor was a public_key specified.")
        
        super(FriendNode, self).__init__(*args, **kwargs)
    
    def validIdentity(self, data):
        try:
            if 'public_key' in data \
            and 'private_key' in data \
            and 'modified' in data \
            and 'data' in data \
            and 'friends' in data['data'] \
            and 'identity' in data['data'] \
            and 'name' in data['data']['identity'] \
            and 'avatar' in data['data']['identity']:
                return True
            else:
                raise InvalidIdentity("invalid identity dictionary for identity")
        except InvalidIdentity:
            raise
        
class RoutedFriendNode(FriendNode):
    
    def __init__(self, *args, **kwargs):
        
        if 'identityData' in kwargs:
            identityData = kwargs['identityData']
        else:
            identityData = args[0]
            kwargs['identityData'] = identityData
        
        try:
            newIdentity = args[1]
        except:
            newIdentity = None
        
        if type(kwargs['identityData']) == type(u'') or type(kwargs['identityData']) == type(''):
            identityData = self.getFriend(kwargs['identityData'])
        elif type(kwargs['identityData']) == type({}):
            identityData = kwargs['identityData']
        else:
            raise InvalidIdentity("A valid server Identity was not given nor was a public_key specified.")
        
        super(RoutedFriendNode, self).__init__(*args, **kwargs)
        
        self.set('routed_public_key', kwargs['acceptor']['public_key'], True)
        self.set('source_indexer_key', kwargs['requester']['public_key'], True)
        if 'connector' in kwargs:
            self.set('public_key', kwargs['connector']['public_key'])
            self.set('private_key', kwargs['connector']['private_key'])
        self.setModifiedToNow()
    
    def validIdentity(self, data):
        try:
            if 'public_key' in data \
            and 'private_key' in data \
            and 'source_indexer_key' in data \
            and 'routed_public_key' in data \
            and 'modified' in data \
            and 'data' in data \
            and 'friends' in data['data'] \
            and 'identity' in data['data'] \
            and 'name' in data['data']['identity'] \
            and 'avatar' in data['data']['identity']:
                return True
            else:
                raise InvalidIdentity("invalid identity dictionary for identity")
        except InvalidIdentity:
            raise
