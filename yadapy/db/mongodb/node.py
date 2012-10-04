import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib, inspect
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange
from pymongo import Connection
from yadapy.node import Node as BaseNode
try:
    from pymongo.objectid import ObjectId
except:
    from bson.objectid import ObjectId

 
class Node(BaseNode):
    conn = None
    def __init__(self, *args, **kwargs):
        
        if 'host' in kwargs:
            host = kwargs['host'] 
        else:
            host = 'localhost'
        if 'port' in kwargs:
            port = kwargs['port']
        else:
            port = 27021
        
        if not self.conn:
            self.conn = Connection(host, port)
            self.db = self.conn.yadaserver
            self.col = self.db.identities

        if 'public_key' in kwargs:
            args = [x for x in args]
            args.insert(0, self.getProfileIdentity(kwargs['public_key']))
            
        super(Node, self).__init__(*args, **kwargs)
    
    def queryIndexerByHost(self, host):
        
        indexerQuery = self.db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                                                              
                        {
                            "$match" : {
                                "data.identity.name" : host
                            }
                        },
                        
                        {
                            "$match" : {
                                "data.type" : "indexer"
                            }
                        },
                    ]
                })['result']
        if not indexerQuery:
            return None
        else:
            return indexerQuery[0]
    
    def publicKeyLookup(self, public_key):
        return self.col.find({
                                "data.friends" : {
                                                  "$elemMatch" : {
                                                                  "public_key" : public_key
                                                                  }
                                                  }
                    })
        
    def getFriend(self, public_key):
        friend = self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : self.get('public_key')
                        }
                    },
                    {
                        "$project" : {
                            "_id" : 0,
                            "friend" : "$data.friends",
                            "data" : 0,
                            "public_key" : 0,
                            "private_key" : 0,
                            "modified":0
                        }
                    },
                    {
                                "$match" : {
                                    "friend" : {"$not" : { "$size" : 0 }}
                                    
                        }
                    },
                    {
                        "$unwind" : "$friend"
                    },
                    {
                        "$match" : {
                            "friend.public_key" : public_key
                        }
                    },
                ]
            })
            
        if friend['result']:
            return friend['result'][0]['friend']
        else:
            return super(Node, self).getFriend(public_key)
        
    def getFriendPublicKeyList(self):
        return self.db.command(
        {
            "aggregate" : "identities", "pipeline" : [
            {
                "$match" : {
                    "public_key" : self.get('public_key')
                }
            },
            {
                        "$match" : {
                            "data.friends" : {"$not" : { "$size" : 0 }}
                            
                }
            },
            {
            "$unwind" : "$data.friends"
            },
            {
                "$project" : {
                    "public_key" : "$data.friends.public_key",
                    "_id" : 0
                }
            }
            ]
        })['result'];
    
    def getFriendTopLevelMeta(self, public_key):
        return self.db.command(
        {
            "aggregate" : "identities", "pipeline" : [
            {
                "$match" : {
                    "public_key" : self.get('public_key')
                }
            },
            {
                "$project" : {
                    "friend" : "$data.friends",
                }
            },
            {
                        "$match" : {
                            "friend" : {"$not" : { "$size" : 0 }}
                            
                }
            },
            {
            "$unwind" : "$friend"
            },
            {
                "$project" : {
                    "public_key" : "$friend.public_key",
                    "data" : 0
                }
            },
            {
                "$match" : {
                    "public_key" : public_key
                }
            },
            ]
        })['result'][0]['friend'];
    
    def getProfileIdentity(self, public_key):
        ret = self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                {
                    "$match" : {
                        "public_key" : public_key
                    }
                },
                ]
            })['result'][0];
        ret['_id'] = str(ret['_id'])
        return ret
    
    def save(self):
        try:
            result = self.col.find({'public_key':self.get('public_key')})
            if result.count() > 0:
                if type(result[0]['_id']) == type(''):
                    id = ObjectId(result[0]['_id'])
                else:
                    id = result[0]['_id']
                self._data['_id'] = id
                self.setModifiedToNow()
                self.col.update({'public_key': self.get('public_key')}, self.get())
                del self._data['_id']
            else:
                self.setModifiedToNow()
                self.col.insert(self.get())
            return "save ok"
        except:
            raise