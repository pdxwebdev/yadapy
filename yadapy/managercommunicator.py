import logging, os, json, time, copy, time, datetime, re, urllib, httplib, socket, requests
from base64 import b64encode, b64decode
from uuid import uuid4
from lib.crypt import encrypt, decrypt
from node import Node
from manager import YadaServer
from nodecommunicator import NodeCommunicator

timeout = 1
socket.setdefaulttimeout(timeout)

class ManagerCommunicator(NodeCommunicator):

    impersonate = False
    
    def __init__(self, node, manager = None):
        super(self, ManagerCommunicator).__init__(node, manager)

    def routeRequestThroughNode(self, destNode, destinationPublicKey, name='new friend', avatar=''):
        
        newFriend = Node({}, {'name':'Just created for the new keys'})
        
        selectedFriend = Node({}, {"name" : name, 'avatar': avatar})
                
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        sourceNodeCopy.add('data/friends', selectedFriend.get())
        sourceNodeCopy.set('routed_public_key', destinationPublicKey, True)

        selectedFriend.set('routed_public_key', destinationPublicKey, True)
        selectedFriend.set('public_key', newFriend.get('public_key'))
        selectedFriend.set('private_key', newFriend.get('private_key'))
        selectedFriend.setModifiedToNow()
        selectedFriend.set('source_indexer_key', destNode.get('public_key'), True)
        
        self.node.addFriend(selectedFriend.get())
        self.node.add('data/friends', selectedFriend.get())
        self.updateRelationship(destNode)
        
        sourceNodeCopy.set('public_key', newFriend.get('public_key'))
        sourceNodeCopy.set('private_key', newFriend.get('private_key'))
        
        sourceNodeCopy.set('source_indexer_key', destNode.get('public_key'), True)
        sourceNodeCopy.replaceIdentityOfFriendsWithPubKeys()
        
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(sourceNodeCopy.get())))
        
        return self._doRequest(destNode, destNode, data, status="ROUTED_FRIEND_REQUEST")
