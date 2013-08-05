from yadapy.node import Node as BaseNode
import sqlite3, json, os
from uuid import uuid4

class Node(BaseNode):
    
    def __init__(self, *args, **kwargs):
        s = sqlite3.connect(kwargs['location'])
        self.cursor = s.cursor()
        try:            
            self.cursor.execute("DROP TABLE IF EXISTS identity;")
            self.cursor.execute("DROP TABLE IF EXISTS messages;")
            self.cursor.execute("DROP TABLE IF EXISTS friends;")
            self.cursor.execute("DROP TABLE IF EXISTS status;")
            self.cursor.execute("DROP TABLE IF EXISTS friend_requests;")
    
            
            self.cursor.execute("CREATE TABLE IF NOT EXISTS identity (identity_public_key TEXT, blob BLOB);")
            
            self.cursor.execute("CREATE TABLE IF NOT EXISTS messages (identity_public_key TEXT, guid TEXT PRIMARY KEY, thread_id TEXT, public_key TEXT, subject TEXT, who TEXT, timestamp INTEGER, blob BLOB, read INTEGER DEFAULT 0);")
            
            self.cursor.execute("CREATE TABLE IF NOT EXISTS friends (identity_public_key TEXT, public_key TEXT, name TEXT, blob BLOB);")
            
            self.cursor.execute("CREATE TABLE IF NOT EXISTS status (identity_public_key TEXT, public_key TEXT, share_id TEXT PRIMARY KEY, timestamp INTEGER, blob BLOB, read INTEGER DEFAULT 0);")
            
            self.cursor.execute("CREATE TABLE IF NOT EXISTS friend_requests (identity_public_key TEXT, public_key TEXT PRIMARY KEY, blob BLOB, read INTEGER DEFAULT 0, ignored INTEGER DEFAULT 0);")
    
    
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS messagex ON messages(identity_public_key);")
        
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS friendx ON friends(identity_public_key);")
            
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS friendreqx ON friend_requests(identity_public_key);")
            
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS statusx ON status(identity_public_key);")
            
            
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS messagex ON messages(guid);")
        
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS friendx ON friends(public_key);")
            
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS friendreqx ON friend_requests(public_key);")
            
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS statusx ON status(share_id);")
    
            
        except:
            raise
        super(Node, self).__init__(*args, **kwargs)
        
    def getCounts(data, decrypted):
        friend_requestCount=0
        messageCount=0
        try:
            latestMessageGUIDs = decrypted['latestMessageGUIDs']
            friendRequestPublicKeys = decrypted['friendRequestPublicKeys']
            connection = Connection('localhost',27021)
            db = connection.yadaserver
            """
            friend = self.cursor.execute("SELECT count(*) FROM friend_requests WHERE read"
                                          "public_keym" :"$friend.public_key",
                                          "request_public_keym" : "$friend.data.routed_friend_requests.public_key",
                                          "routed_public_keym" : "$friend.data.routed_friend_requests.routed_public_key"
                                        )
            """
            #this is a hack because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(friend['result']):
                if 'routed_public_keym' in r and r['routed_public_keym']==r['public_keym'] and not r['request_public_keym'] in friendRequestPublicKeys:
                    friend_requestCount+=1
            
            message = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.messages"
                        },
                        {
                            "$project" : {
                                          "public_keym" :"$friend.public_key",
                                          "guid" :"$friend.data.messages.guid",
                                          "message_public_keym" : "$friend.data.messages.public_key"
                                        }
                        },
                    ]
                })
            #this is a heck because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(message['result']):
                if 'message_public_keym' in r and 'public_keym' in r:
                    if r['public_keym'] in r['message_public_keym'] and not r['guid'] in latestMessageGUIDs:
                        messageCount+=1
                    
            return '{"messages":"%s", "friend_requests" : "%d", "requestType" : "getCounts"}' %(messageCount, friend_requestCount)
        except:
            raise
    
    def save(self):
        res = self.cursor.execute("SELECT id FROM node WHERE public_key = ?", [self.get('public_key')])
        if len([x for x in res]):
            self.cursor.execute("UPDATE node SET data = ? WHERE public_key = ?", [json.dumps(self.get()), self.get('public_key')])
        else:
            self.cursor.execute("INSERT INTO node (data, public_key) VALUES (?, ?)", [json.dumps(self.get()), self.get('public_key')])