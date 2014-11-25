#!/usr/bin/env python

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, re, logging, os, sys, hashlib, base64, traceback
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from yadapy.nodecommunicator import NodeCommunicator
from yadapy.db.mongodb.manager import YadaServer
from yadapy.db.mongodb.node import Node
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

class MyServerProtocol(WebSocketServerProtocol):    
    def onConnect(self, request):
        print 'connected!'
        f = open('/home/phablet/yadaserver.log', 'a')
        f.write('connected2\n')
        f.close()
         
    def onMessage(self, inbound, isBinary):
        """
        As soon as any data is received, write it back.
        """
        print 'got data!'
	f = open('/home/phablet/yadaserver.log', 'a')
        try:
            inboundObj = json.loads(inbound)
            if "METHOD" in inboundObj and inboundObj['METHOD'] == "CREATE_IDENTITY":
                f.write('got identity message')
                f.close()
                n = Node({}, {"name": ""})
                n._data['idlabel'] = inboundObj['DATA']
                n.save()
                return

            if "METHOD" in inboundObj and inboundObj['METHOD'] == "UPDATE_IDENTITY":
                f.write('got update identity message')
                f.close()
                print inboundObj
                n = Node(inboundObj['DATA'])
                n.save()
                return

        except:
	    pass
        try:
            f.write('|---|%s|---|\n' % inbound)
            #f.write(json.dumps(inbound))
	    #response = nodeComm.handlePacket(inbound)
            #returnData = json.dumps(response)
            """
		This is generally where a qr scanner would forward the object to postFriend api endpoint.
		instead, we're going to 
	    """
            print "about to start notify.py"
            call (['python', '/home/phablet/notify.py', inbound])
            self.sendMessage('OK')
        except:
	    exc_type, exc_value, exc_traceback = sys.exc_info()
	    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    	    f.write(''.join('!! ' + line for line in lines))
            self.transport.write('Input not valid.')
            f.close()

def main():
    f = WebSocketServerFactory("ws://localhost:8901", debug = False)
    f.protocol = MyServerProtocol
    reactor.listenTCP(8901, f)
    print "running server"
    reactor.run()

if __name__ == '__main__':
    main()
