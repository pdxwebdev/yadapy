import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib, inspect
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange
from pymongo import Connection
from json import JSONEncoder
from yadapy.lib.crypt import encrypt, decrypt
try:
    from pymongo.objectid import ObjectId
except:
    from bson.objectid import ObjectId
from node import Node
from yadapy.node import InvalidIdentity
from yadapy.manager import YadaServer as Manager


class YadaServer(Manager, Node):
    conn = None
    def __init__(self, *args, **kwargs):
        
        if 'host' not in kwargs:
            host = 'localhost'
        else:
            host = kwargs['host']
            
        if 'port' not in kwargs:
            port = 27021
        else:
            port = kwargs['port']
            
        identityData = args[0]
        try:
            newIdentity = args[1]
        except:
            newIdentity = None
        
        if not self.conn:
            self.conn = Connection(host, port)
            self.db = self.conn.yadaserver
            self.col = self.db.identities
        
        if type(identityData) == type(u'') or type(identityData) == type(''):
            identityData = self.getManagedNode(identityData)
        elif type(identityData) == type({}):
            newIdentity = newIdentity
        else:
            raise InvalidIdentity("A valid server Identity was not given nor was a public_key specified.")
        super(YadaServer, self).__init__(identityData=identityData, newIdentity=newIdentity)
    
    def getManagedNode(self, public_key):
        res = [x for x in self.col.find({'public_key':public_key})]
        if len(res):
            return res[0]
        else:
            return False
        
    def addManagedNode(self, data):
        try:
            node = Node(data)
            self.col.insert(node.get())
            return "ok"
        except:
            raise InvalidIdentity("cannot add invalid node to managed nodes")
        

    def getServerData(self):
        data = self.col.find({'public_key':self.get('public_key')})[0]
        return data
    
    def getServerIdentity(self):
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
                        "data" : {"identity" : "$data.identity","type" : "$data.type"},
                        "_id" : 0,
                        "modified" : "$modified",
                    }
                }
                ]
            })['result'][0];
            
    def getServerFriendsPublicKeysList(self):
        return self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                {
                    "$match" : {
                        "public_key" : self.get('public_key')
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
    def addServerMessage(self, message):
        self.col.update({'public_key':self.get('public_key')}, {'$push' : {'data.messages': message}})
    
    def addServerFriend(self, friend):
        self.col.update({'public_key':self.get('public_key')}, {'$push' : {'data.friends': friend}})

    def publicKeyLookup(self, public_key):
        return [x for x in self.col.find({
                                "data.friends" : {
                                                  "$elemMatch" : {
                                                                  "public_key" : public_key
                                                                  }
                                                  }
                    })]
        
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
                        "$unwind" : "$friend"
                    },
                    {
                        "$match" : {
                            "friend.public_key" : public_key
                        }
                    },
                ]
            });
            
        if friend['result']:
            return friend['result'][0]['friend']
        else:
            return super(YadaServer, self).getFriend(public_key)
        
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
        return self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                {
                    "$match" : {
                        "public_key" : public_key
                    }
                },
                {
                    "$project" : {
                        "data" : {"identity" : "$data.identity","type" : "$data.type"},
                        "_id" : 0,
                        "modified" : "$modified",
                    }
                }
                ]
            })['result'][0];
        
    def updateManagedNode(self, node):
        self.col.update({'public_key':node.get('public_key')},node.get())
        
    def addFriendForProfile(self, friend):
        self.update({'public_key':self.get('public_key')}, {'$push' : {'data.friends': friend}})
        self.update({'public_key':self.get('public_key')}, {'$set' : {'modified': self.setModifiedToNow()}})
    
    def addMessageForProfile(self, message):
        self.update({'public_key':self.get('public_key')}, {'$push' : {'data.messages': message}})
        self.update({'public_key':self.get('public_key')}, {'$set' : {'modified': self.setModifiedToNow()}})
    
    def forceJoinNodes(self, sourceNode, destNode):
        
        newFriendRequest = Node({}, sourceNode.get('data/identity'), sourceNode.getFriendPublicKeysDict())
        newFriendRequest.set('status', 'FRIEND_REQUEST', True)
        
        newIndexerFriendRequest = Node({}, destNode.get('data/identity'), destNode.getFriendPublicKeysDict())
        newIndexerFriendRequest.set('public_key', newFriendRequest.get('public_key'))
        newIndexerFriendRequest.set('private_key', newFriendRequest.get('private_key'))
        
        #checks to see if the user has already "friended" this indexer
        res = self.col.find({ '$and' : [{'public_key':destNode.get('public_key')},{'data.friends.data.friends.public_key':newFriendRequest.getFriendPublicKeysDict()[0]['public_key']}]})
        if not res.count():
            newFriendRequest.replaceIdentityOfFriendsWithPubKeys()
            destNode.add('data/friends', newFriendRequest.get())
            destNode.save()
        
        #checks to see if the indexer has already "friended" this user
        res = self.col.find({ '$and': [{'public_key':sourceNode.get('public_key')},{'data.friends.data.friends.public_key':newIndexerFriendRequest.getFriendPublicKeysDict()[0]['public_key']}]})
        if not res.count():
            newIndexerFriendRequest.replaceIdentityOfFriendsWithPubKeys()
            sourceNode.add('data/friends', newIndexerFriendRequest.get())
            sourceNode.save()
            