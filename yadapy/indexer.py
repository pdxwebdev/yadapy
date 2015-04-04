import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from lib.crypt import encrypt, decrypt
from uuid import uuid4
from node import Node, InvalidIdentity
from friendnode import RoutedFriendNode


class Indexer(Node):
    
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
        
        super(Indexer, self).__init__(*args, **kwargs)
        
        self.set('data/type', 'indexer', True)

    def validIdentity(self, data):
        try:
            if 'public_key' in data \
            and 'private_key' in data \
            and 'modified' in data \
            and 'data' in data \
            and 'type' in data['data'] \
            and data['data']['type'] == 'indexer' \
            and 'friends' in data['data'] \
            and 'identity' in data['data'] \
            and 'messages' in data['data'] \
            and 'name' in data['data']['identity']:
                return True
            else:
                raise InvalidIdentity("invalid identity dictionary for identity")
        except InvalidIdentity:
            raise
    
    def friendRequest(self, requester, acceptor):
        newFriendship = Node({}, {'name':'Just created for the new keys'})
        #### new friend routine: requester ####
        newRequester = RoutedFriendNode(requester, requester=requester, acceptor=acceptor)
        #### end new friend routine ####
        
        #### new friend routine: acceptor ####
        newAcceptor = RoutedFriendNode(acceptor, requester=requester, acceptor=acceptor, connector=node)
        #### end new friend routine ####
        selfCopy = copy.deepcopy(self.get())
        selfCopy._data['data']['friends'] = []
        selfCopy.add('friends', newRequester)
        selfCopy.add('friends', newRequester)
        return selfCopy
        
        