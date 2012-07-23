from yadapy.node import Node as BaseNode
import sqlite3, json, os
from uuid import uuid4

class Node(BaseNode):
    
    def __init__(self, *args, **kwargs):
        s = sqlite3.connect(kwargs['location'])
        self.cursor = s.cursor()
        try:
            self.cursor.execute('CREATE TABLE node (id INTEGER PRIMARY KEY, public_key varchar(50), data TEXT)')
            """
            self.cursor.execute(database, "DROP TABLE IF EXISTS yada;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS config;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS identity;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS messages;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS friends;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS status;")
            self.cursor.execute(database, "DROP TABLE IF EXISTS friend_requests;")
    
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS config (key TEXT, value TEXT);")
            
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS identity (blob BLOB);")
            
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS messages (guid TEXT PRIMARY KEY, thread_id TEXT, public_key TEXT, subject TEXT, who TEXT, timestamp INTEGER, blob BLOB, read INTEGER DEFAULT 0);")
            
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS friends (public_key TEXT, name TEXT, blob BLOB);")
            
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS status (public_key TEXT, share_id TEXT PRIMARY KEY, timestamp INTEGER, blob BLOB, read INTEGER DEFAULT 0);")
            
            self.cursor.execute(database, "CREATE TABLE IF NOT EXISTS friend_requests (public_key TEXT PRIMARY KEY, blob BLOB, read INTEGER DEFAULT 0, ignored INTEGER DEFAULT 0);")
    
            if(self.cursor.execute(database, "CREATE UNIQUE INDEX IF NOT EXISTS messagex ON messages(guid);") == SQLITE_OK):
                pass
        
            if(self.cursor.execute(database, "CREATE UNIQUE INDEX IF NOT EXISTS friendx ON friends(public_key);") == SQLITE_OK):
                pass
            
            if(self.cursor.execute(database, "CREATE UNIQUE INDEX IF NOT EXISTS friendreqx ON friend_requests(public_key);") == SQLITE_OK):
                pass
            
            if(self.cursor.execute(database, "CREATE UNIQUE INDEX IF NOT EXISTS statusx ON status(share_id);") == SQLITE_OK):
                pass
    
            self.cursor.execute(database, "INSERT INTO config (key, value) VALUES ('friendask', '0');")
            
            self.cursor.execute(database, "INSERT INTO config (key, value) VALUES ('cloudask', '0');")
            """
        except:
            pass
        super(Node, self).__init__(*args, **kwargs)
        
        
    
    def save(self):
        res = self.cursor.execute("SELECT id FROM node WHERE public_key = ?", [self.get('public_key')])
        if len([x for x in res]):
            self.cursor.execute("UPDATE node SET data = ? WHERE public_key = ?", [json.dumps(self.get()), self.get('public_key')])
        else:
            self.cursor.execute("INSERT INTO node (data, public_key) VALUES (?, ?)", [json.dumps(self.get()), self.get('public_key')])