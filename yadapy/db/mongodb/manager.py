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
    host = None
    port = None
    
    def __init__(self):
        self._data['modified'] = 0
        self.setModifiedToNow()
          
    def _createServerNode(self, *args, **kwargs):
        
        if 'host' in kwargs:
            self.host = kwargs['host']
            
        if 'port' in kwargs:
            self.port = kwargs['port']
        
        if 'identityData' in kwargs:
            identityData = kwargs['identityData']
        else:
            kwargs['identityData'] = args[0]
            identityData = args[0]
        
        try:
            newIdentity = args[1]
        except:
            newIdentity = None
                
        if type(identityData) == type(u'') or type(identityData) == type(''):
            kwargs['identityData'] = self.getManagedNode(identityData)
        elif type(newIdentity) == type({}):
            kwargs['newIdentity'] = newIdentity
        elif type(identityData) == type({}):
            pass
        else:
            raise InvalidIdentity("A valid server Identity was not given nor was a public_key specified.")
        super(YadaServer, self).__init__(*args, **kwargs)
    
    def getManagedNode(self, public_key):
        res = [x for x in self.col.find({'public_key':public_key})]
        if res:
            if '_id' in res[0]:
                del res[0]['_id']
        if len(res):
            return res[0]
        else:
            return False
        
    def addManagedNode(self, data, friendNode):
        try:
            node = Node(data)
            for friend in node.get('data/friends'):
                node.addFriend(friend)
            node.set('data/friends', [])
            self.db.managed.insert({'managed_public_key': node.get('public_key'), 'friend_public_key': friendNode.get('public_key')})
            self.col.insert(node.get())
            return "ok"
        except:
            raise InvalidIdentity("cannot add invalid node to managed nodes")
        
    def syncManagedNode(self, node):
        try:
            managedNode = Node(self.getManagedNode(node.get('public_key')))
            managedNode.sync(node.get())
            managedNode.save()
            return managedNode.get()
        except:
            raise InvalidIdentity("cannot sync invalid node in managed nodes")

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
                        "public_key": "$public_key",
                        "private_key": "$private_key"
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
    def addServerMessage(self, message):
        self.col.update({'public_key':self.get('public_key')}, {'$push' : {'data.messages': message}})
    
    def addServerFriend(self, friend):
        self.col.update({'public_key':self.get('public_key')}, {'$push' : {'data.friends': friend}})
        
    def getFriend(self, public_key):
        friend = self.db.friends.find({'public_key': self.get('public_key'), 'friend_public_key': public_key}, {'friend': 1})
            
        if friend.count() > 0:
            return friend[0]['friend']
        else:
            try:
                friend = Node({}, {'name': 'temp'})
                friend.get().update(self.publicKeyLookup(public_key)[0])
                return self.db.friends.find({'public_key': friend.get('public_key'), 'friend_public_key': public_key}, {'friend': 1})[0]['friend']
            except:
                return []
            
    def publicKeyLookup(self, public_key):
        friends = self.db.friends.find({"friend_public_key" : public_key}, {'public_key': 1})
        
        if friends.count() > 0:
            identities = self.col.find({
                                        "public_key" : {"$in": [friend['public_key'] for friend in friends]}
                                        }, 
                                       { 
                                        'public_key': 1, 
                                        'private_key': 1, 
                                        "_id": 0, 
                                        'data.identity': 1, 
                                        'data.messages': 1, 
                                        'data.status': 1,
                                        'data.type': 1
                                        }
                                       )
            if identities.count() > 0:
                return identities
            
        return self.col.find({"public_key" : public_key}, {'public_key': 1, 'private_key': 1, "_id": 0, 'data.identity': 1, 'data.messages': 1, 'data.status': 1})
    
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
            
    def chooseRelationshipNode(self, r, inboundNode, impersonate = False):
        
        node0 = Node({}, {'name': '0'})
        node1 = Node({}, {'name': '1'})
        
        result = self.db.managed.find({"friend_public_key" : {"$in": inboundNode.getFriendPublicKeysArray()}})
        
        if r.count() == 1:
            if result.count() == 0: #inbound is not hosted here
                node0.get().update(r[0]) #here we hard-coded to return node0, so we have to make sure the node we return is not the inbound
                return node0
        
        if r.count() == 2:
            node0.get().update(r[0])
            node1.get().update(r[1])
            
            if result.count() == 1: #inbound is hosted here
                if r[0]['public_key'] == self.get('public_key'): #is this node the server
                    return node0 #we return the server because now we know inbound is not the server because result is not empty
                elif r[1]['public_key'] == self.get('public_key'): #is this node the server
                    return  node1 #we return the server because now we know inbound is not the server because result is not empty
                elif r[0]['public_key'] == result[0]['managed_public_key']: #neither node is the server 
                    return node1
                elif r[1]['public_key'] == result[0]['managed_public_key']: #neither node is the server
                    return node0
            else: #inbound is not hosted here
                if r[0]['public_key'] == self.get('public_key'): #is this node the server
                    return node0 #we return the server because now we know inbound is not the server because result is not empty
                elif r[1]['public_key'] == self.get('public_key'): #is this node the server
                    return  node1 #we return the server because now we know inbound is not the server because result is not empty
                #it is not possible to have 2 nodes hosted and have result be empty.
                    
    def updateFromNode(self, inboundNode, impersonate = False):
        managedNode = self.getManagedNode(inboundNode['public_key'])
        relationship = self.publicKeyLookup(inboundNode['public_key'])
        node = None
        if managedNode:
            self.syncManagedNode(managedNode, inboundNode)
        else:
            node = self.chooseRelationshipNode(relationship, Node(inboundNode), impersonate)
        
        if node:
            if isinstance(node, YadaServer):
                super(YadaServer, node).updateFromNode(inboundNode)
            else:
                if impersonate:
                    node.sync(inboundNode, is_self=False, permission_object=inboundNode['permissions'])
                else:
                    node.updateFromNode(inboundNode)