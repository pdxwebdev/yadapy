#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, re, logging
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from nodecommunicator import NodeCommunicator
from db.mongodb.manager import YadaServer
from db.mongodb.node import Node
from api.node import MongoApi

from lib.crypt import decrypt

### Protocol Implementation
Node.host = 'yadaproject.com'
Node.port = 27021
# This is just about the simplest possible protocol
YadaServer._data = {}
YadaServer._data['public_key'] = '84ce10c5-5970-4007-92a7-c1f00f0329c5'
ys = YadaServer()
nodeComm = NodeCommunicator(ys)
mongoapi = MongoApi(nodeComm)


class Echo(Protocol):
            
    def dataReceived(self, inbound):
        """
        As soon as any data is received, write it back.
        """
        try:

            response = nodeComm.handlePacket(inbound)
            returnData = json.dumps(response)
            
            self.transport.write(returnData)
        except:
            self.transport.write('Input not valid.')
        self.transport.loseConnection()

def main():
    f = Factory()
    f.protocol = Echo
    reactor.listenTCP(8901, f)
    reactor.run()

if __name__ == '__main__':
    main()