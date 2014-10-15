#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, re, logging, os, sys
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from nodecommunicator import NodeCommunicator
from db.mongodb.manager import YadaServer
from db.mongodb.node import Node
from api.node import MongoApi
from pymongo import Connection
from lib.crypt import decrypt
from subprocess import call

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
mongoapi = MongoApi(nodeComm)

class Echo(Protocol):
    def connectionMade(self):
        f = open('/home/phablet/yadaserver.log', 'w')
        f.write('connected2')
        f.close()
	self.transport.write("Welcome!")
	call (['python', '/home/phablet/notify.py'])
            
    def dataReceived(self, inbound):
        """
        As soon as any data is received, write it back.
        """
        try:
	    f = open('/home/phablet/yadaserver.log', 'w')
            f.write(inbound)
	    response = nodeComm.handlePacket(inbound)
            returnData = json.dumps(response)
            
            self.transport.write(returnData)
        except:
	    f.write('got something but failed')
            self.transport.write('Input not valid.')
            f.close()
        self.transport.loseConnection()

def main():
    f = Factory()
    f.protocol = Echo
    reactor.listenTCP(8901, f)
    reactor.run()

if __name__ == '__main__':
    fpid = os.fork()
    if fpid != 0:
	print 'A new child ',  os.getpid()
	sys.exit(0)
    main()
