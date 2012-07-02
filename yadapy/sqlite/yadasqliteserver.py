from manager import YadaServer
import sqlite3, json
from uuid import uuid4

class YadaServer(YadaServer):
	
	def __init__(self, identityData={}, newIdentity={}, initialFriends=[], location=None):
		s = sqlite3.connect(location)
		self.cursor = s.cursor()
		try:
			self.cursor.execute('CREATE TABLE node (id INTEGER PRIMARY KEY, public_key varchar(50), data TEXT)')
		except:
			print "table already exists"
		
		super(YadaSQLiteServer, self).__init__(identityData=identityData, newIdentity=newIdentity, initialFriends=initialFriends)
	
	def save(self):
		res = self.cursor.execute("SELECT id FROM node WHERE public_key = ?", [self.get('public_key')])
		if len([x for x in res]):
			self.cursor.execute("UPDATE node SET data = ? WHERE public_key = ?", [json.dumps(self.get()), self.get('public_key')])
		else:
			self.cursor.execute("INSERT INTO node (data, public_key) VALUES (?, ?)", [json.dumps(self.get()), self.get('public_key')])
		