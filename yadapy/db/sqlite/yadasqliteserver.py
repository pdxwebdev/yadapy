from yadapy.manager import YadaServer as ServerNode
from nodesqlite import Node
import sqlite3, json
from uuid import uuid4

class YadaServer(ServerNode):
	
	def __init__(self, identityData={}, newIdentity={}, initialFriends=[], location=None):
				
		super(YadaServer, self).__init__(identityData=identityData, newIdentity=newIdentity, initialFriends=initialFriends, location=location)
	
	def save(self):
		res = self.cursor.execute("SELECT id FROM node WHERE public_key = ?", [self.get('public_key')])
		if len([x for x in res]):
			self.cursor.execute("UPDATE node SET data = ? WHERE public_key = ?", [json.dumps(self.get()), self.get('public_key')])
		else:
			self.cursor.execute("INSERT INTO node (data, public_key) VALUES (?, ?)", [json.dumps(self.get()), self.get('public_key')])

attrDict = {}
for i, x in YadaServer.__dict__.items():
    attrDict[i] = x

YadaServer = type("YadaServer", (Node,), attrDict)