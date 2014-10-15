#!/usr/bin/env python

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, re, logging, os, sys, hashlib, base64, traceback
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

#class Echo(Protocol):
class MyServerProtocol(WebSocketServerProtocol):    
    #def connectionMade(self):
    def onConnect(self, request):
        f = open('/home/phablet/yadaserver.log', 'a')
        f.write('connected2\n')
        f.close()
	#call (['python', '/home/phablet/notify.py'])
         
    #def dataReceived(self, inbound):
    def onMessage(self, inbound, isBinary):
        """
        As soon as any data is received, write it back.
        """
	f = open('/home/phablet/yadaserver.log', 'a')
	if 'websocket' in inbound:
            headers = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", inbound))
	    key = headers['Sec-WebSocket-Key']
	    f.write('|---|%s|---|\n' % key)
	    newhash = base64.b64encode(hashlib.sha1(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
	    
	    self.transport.write("""HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: %s



""" % newhash)
	    return
	try:
            f.write('|---|%s|---|\n' % inbound)
	    inbound = json.loads(base64.b64decode(inbound))
	    f.write(json.dumps(inbound))
	    response = nodeComm.handlePacket(inbound)
            returnData = json.dumps(response)
            
            self.transport.write(returnData)
        except:
	    exc_type, exc_value, exc_traceback = sys.exc_info()
	    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    	    f.write(''.join('!! ' + line for line in lines))
            self.transport.write('Input not valid.')
            f.close()

def main():
    #f = Factory()
    #f.protocol = Echo
    f = WebSocketServerFactory("ws://localhost:8901", debug = False)
    f.protocol = MyServerProtocol
    reactor.listenTCP(8901, f)
    reactor.run()

if __name__ == '__main__':
    fpid = os.fork()
    if fpid != 0:
	print 'A new child ',  os.getpid()
	sys.exit(0)
    main()
