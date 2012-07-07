from yadapy.node import Node as BaseNode
import sqlite3, json, os
from uuid import uuid4

class Node(BaseNode):
    
    def __init__(*args, **kwargs):
        self = args[0]
        s = sqlite3.connect(kwargs['location'])
        self.cursor = s.cursor()
        try:
            self.cursor.execute('CREATE TABLE node (id INTEGER PRIMARY KEY, public_key varchar(50), data TEXT)')
            super(Node, self).__init__(*args[1:], **kwargs)
        except:
            print "table already exists"
            res = self.cursor.execute("SELECT data FROM node WHERE public_key = ?", [self.get('public_key')])
            super(Node, self).__init__(res[0])
        
        
    
    def save(self):
        res = self.cursor.execute("SELECT id FROM node WHERE public_key = ?", [self.get('public_key')])
        if len([x for x in res]):
            self.cursor.execute("UPDATE node SET data = ? WHERE public_key = ?", [json.dumps(self.get()), self.get('public_key')])
        else:
            self.cursor.execute("INSERT INTO node (data, public_key) VALUES (?, ?)", [json.dumps(self.get()), self.get('public_key')])