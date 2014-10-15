#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, logging, re, os, sys
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from nodecommunicator import NodeCommunicator
from db.mongodb.manager import YadaServer
from db.mongodb.node import Node
from api.node import MongoApi
from pymongo import Connection
from lib.crypt import decrypt

### Protocol Implementation
Node.host = 'localhost'
Node.port = 27017
Node.conn = Connection(Node.host, Node.port)
Node.db = Node.conn.yadaserver
Node.col = Node.db.identities
# This is just about the simplest possible protocol
YadaServer._data = {}
YadaServer._data['public_key'] = '84ce10c5-5970-4007-92a7-c1f00f0329c5'
ys = YadaServer()
nodeComm = NodeCommunicator(ys)

def loadInboundJson(inbound):
    jsonDict = {}
    try:
        
        jsonDict = json.loads(inbound)
        if type(jsonDict['data']) == type("") or type(jsonDict['data']) == type(u""):
            jsonDict['data'] = jsonDict['data'].replace(' ', '+')
    except:
        logging.debug('loadInboundJson error in parsing json')
    return jsonDict

def getProfileFromInbound(jsonDict):
    try:
        return Node.col.find({'public_key':jsonDict['public_key']},{"public_key": 1,"private_key": 1,"modified": 1, 'data.friends': 1, 'data.identity.name': 1, 'data.identity.avatar': 1, 'data.identity.ip_address': 1})[0]
    except:
        return None

class Echo(Protocol):
            
    def dataReceived(self, inbound):
        """
        As soon as any data is received, write it back.
        """
        node = YadaServer()
        nodeComm = NodeCommunicator(node)
        mongoapi = MongoApi(nodeComm)
        try:
            jsonDict = loadInboundJson(inbound)
            data = getProfileFromInbound(jsonDict)
            decrypted = {}
            if data:
                try:
                    decrypted.update(json.loads(decrypt(data['private_key'], data['private_key'], jsonDict['data'])))
                except:
                    decrypted = jsonDict['data']
            
            response = getattr(mongoapi, jsonDict['METHOD'])(data, decrypted)
            jsonResponse = json.dumps(response)
            self.transport.write(jsonResponse)
        except Exception as ex:
            logging.exception(ex)
            self.transport.write('Input not valid.')
        self.transport.loseConnection()


def main():
    f = Factory()
    f.protocol = Echo
    reactor.listenTCP(8900, f)
    reactor.run()

if __name__ == '__main__':
    fpid = os.fork()
    if fpid != 0:
        print 'A new child ',  os.getpid()
        sys.exit(0)
    main()
