    
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
        self.disseminate(requester, acceptor, 'INDEXER_REQUEST_UPDATE')
    
    def disseminateAcceptance(self, requester, acceptor):
        self.disseminate(requester, acceptor, 'INDEXER_REQUEST_ACCEPT')
        
    def disseminate(self, requester, acceptor, status):
    
        #### combine under current indexer context ####
        indexerRequestObject = self.node.friendRequest(requester, acceptor)
        
        #### where to send? ###
        contacted = []
        for node in indexerRequestObject.get('data/friends'):
            for nodeFriend in node['data']['friends']:
                #TODO: Make the type get passed around with second degree relationships
                if 'source_indexer_key' not in nodeFriend:# this is not good, needs to evaluate 'data/type' instead
                    #### is this indexer already friends with that indexer? ####
                    
                    remoteIndexerFriend = self.node.isMutual(nodeFriend)
                    if remoteIndexerFriend and remoteIndexerFriend['data']['identity']['ip_address']:
                        self.doRequest(remoteIndexerFriend, indexerRequestObject, contacted, status)
                    elif nodeFriend['data']['identity']['ip_address']:
                        #### if not, make friends ####
                        host = "%s:%s" % (
                            nodeFriend['data']['identity']['ip_address'][0]['address'], 
                            nodeFriend['data']['identity']['ip_address'][0]['port']
                        )
                        remoteIndexerFriend = self.requestFriend(host)
                    self.doRequest(remoteIndexerFriend, indexerRequestObject, contacted, status)
                        
    def doRequest(self, node, indexerRequestObject, contacted, status):
        host = "%s:%s" % (
            node['data']['identity']['ip_address'][0]['address'], 
            node['data']['identity']['ip_address'][0]['port']
        )
        if host not in contacted:
            contacted.append(host)
        
            #### send friend request packet ####
            data = b64decode(encrypt(node.get('private_key'), node.get('private_key'), json.dumps(indexerRequestObject.get())))
            self._doRequest(self.node.get(), node, data, status=status)
            #### end send friend request packet ####