    
import logging, os, json, time, copy, time, datetime, re, urllib, httplib, socket, requests
from base64 import b64encode, b64decode
from uuid import uuid4
from lib.crypt import encrypt, decrypt
from node import Node
from manager import YadaServer
from nodecommunicator import NodeCommunicator
from indexer import Indexer

timeout = 1
socket.setdefaulttimeout(timeout)

class IndexerCommunicator(NodeCommunicator):

    impersonate = False
    
    def __init__(self, node):
        super(IndexerCommunicator, self).__init__(node)
    
    def disseminateRequest(self, requester, acceptor):
    
        #### combine under current indexer context ####
        indexerRequestObject = self.node.friendRequest(requester, acceptor)
        
        #### where to send? ###
        for node in indexerRequestUpdate.get('data/friends'):
            for nodeFriend in node['data/friends']:
                if nodeFriend['data']['type'] == 'indexer':
                    #### is this indexer already friends with that indexer? ####
                    mutual = self.node.isMutual(nodeFriend)
                    if not mutual:
                        #### if not, make friends ####
                        if nodeFriend['data/identity/ip_address']:
                            mutual = self.requestFriend(
                                "%s:%s" % (
                                    nodeFriend['data/identity/ip_address'][0]['address'], 
                                    nodeFriend['data/identity/ip_address'][0]['port']
                                )
                            )
                    
                    #### send friend request packet ####
                    data = b64decode(encrypt(remoteIndexerfriend.get('private_key'), remoteIndexerfriend.get('private_key'), json.dumps(indexerRequestObject)))
                    self._doRequest(self.node.get(), remoteIndexerfriend, status='INDEXER_REQUEST_UPDATE')
                    #### end send friend request packet ####