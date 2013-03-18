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
    host = 'localhost'
    port = 27021
    def __init__(self, *args, **kwargs):
        
        if 'host' in kwargs:
            self.host = kwargs['host'] 
        if 'port' in kwargs:
            self.port = kwargs['port']
        
        if not self.conn:
            self.conn = Connection(self.host, self.port)
            self.db = self.conn.yadaserver
            self.col = self.db.identities

        if 'public_key' in kwargs:
            args = [x for x in args]
            args.insert(0, self.getProfileIdentity(kwargs['public_key']))
            
        super(Node, self).__init__(*args, **kwargs)
    
    def matchFriend(self, node):
        friend = self.db.command(
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
                    "$match" : {
                        "data.friends.public_key" : {"$in" : node.getFriendPublicKeysArray()}
                        }
                    },
                    {
                    "$project" : {
                        "public_key" : "$data.friends.public_key"
                        }
                    },
                ]
            })
        if friend['result']:
            return self.getFriend(friend['result'][0]['public_key'])
        else:
            return None
    
    def matchedFriendsPublicKeys(self, friend):
        keys = self.db.command(
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
                    "$match" : {
                        "data.friends.public_key" : {"$in" : friend.getFriendPublicKeysArray()}
                        }
                    },
                    {
                    "$project" : {
                        "public_key" : "$data.friends.public_key"
                        }
                    },
                ]
            })
        if keys['result']:
            return keys['result']
        else:
            return None
        
    def addFriend(self, friend):
        self.pushItem('data.friends', friend)
    
    def addMessage(self, message):
        self.pushItem('data.messages', message)
        
    def addFriendRequest(self, packet):
        self.pushItem('friend_requests', packet)
        
    def addRoutedFriendRequest(self, packet):
        self.pushItem('data.routed_friend_requests', packet)
        
    def addPromotionRequest(self, packet):
        self.pushItem('promotion_requests', packet)
    
    def pushItem(self, path, item):
        try:
            
            result = self.col.find({'public_key':self.get('public_key')}, {'_id':1})
            if result.count() > 0:
                if type(result[0]['_id']) == type(''):
                    id = ObjectId(result[0]['_id'])
                else:
                    id = result[0]['_id']
            else:
                self.col.insert(self.get())
                del self._data['_id']
            status = self.col.update({'_id':id}, {'$push' : {path: item}})
            status = self.col.update({'_id':id}, {'$set' : {'modified': self.setModifiedToNow()}})
            return "save ok"
        except:
            raise
        
    def addIPAddress(self, ipAddress):
        self.pushItem('data.identity.ip_address', ipAddress)
    
    def setFriendData(self, friend, data):
        self.setFriendAttribute(friend, 'data', data)

    def setFriendWebToken(self, friend, data):
        self.setFriendAttribute(friend, 'web_token', data)

    def setFriendAttribute(self, friend, path, data):
        self.col.update({"data.friends": {"$elemMatch": {"public_key": friend.get('public_key')}}}, {"$set": {"data.friends.$.%s" % path: data}})
    
    def publicKeyLookup(self, public_key):
        result = self.col.find({"data.friends.public_key" : public_key}, {'public_key': 1, 'private_key': 1, "_id": 0, 'data.identity': 1, 'data.messages': [], 'data.friends': []})
        
        if result.count() > 0:
            return result
        else:
            return self.col.find({"public_key" : public_key}, {'public_key': 1, 'private_key': 1, "_id": 0, 'data.identity': 1, 'data.messages': [], 'data.friends': []})
                
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
        
    def getFriendQuery(self, public_key):
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
            })['result']
            
    def getRoutedFriendRequests(self, public_key):
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
                            "routed_friend_request" : "$data.routed_friend_requests",
                            "data" : 0,
                            "public_key" : 0,
                            "private_key" : 0,
                            "modified":0
                        }
                    },
                    {
                                "$match" : {
                                    "routed_friend_request" : {"$not" : { "$size" : 0 }}
                                    
                        }
                    },
                    {
                        "$unwind" : "$routed_friend_request"
                    },
                    {
                        "$match" : {
                            "routed_friend_request.routed_public_key" : {"$in" : public_key}
                        }
                    },
                ]
            })
        if friend['result']:
            return friend['result'][0]['friend']
        else:
            return None
        
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
        })['result']
    
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
    
    def getMessagesForFriend(self, public_key):
        friend = self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : self.get('public_key')
                        }
                    },
                    {
                                "$match" : {
                                    "data.messages" : {"$not" : { "$size" : 0 }}
                                    
                        }
                    },
                    {
                        "$unwind" : "$data.messages"
                    },
                    {
                        "$match" : {
                            "data.messages.public_key" : public_key
                        }
                    },
                    {
                        "$project" : {
                                "message": "$data.messages"
                        }
                    },
                ]
            })
            
        if friend['result']:
            return friend['result']
        else:
            return []

    def getRoutedFriendRequestsForFriend(self, public_key):
        friend = self.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : self.get('public_key')
                        }
                    },
                    {
                        "$match" : {
                            "data.routed_friend_requests" : {"$not" : { "$size" : 0 }}     
                        }
                    },
                    {
                        "$unwind" : "$data.routed_friend_requests"
                    },
                    {
                        "$match" : {
                            "data.routed_friend_requests.routed_public_key" : public_key
                        }
                    },
                    {
                        "$project" : {
                                "routed_friend_request": "$data.routed_friend_requests"
                        }
                    },
                ]
            })
            
        if friend['result']:
            return friend['result']
        else:
            return []
 
    def save(self):
        try:
            super(Node, self).save()
            result = self.col.find({'public_key':self.get('public_key')})
            if result.count() > 0:
                if type(result[0]['_id']) == type(''):
                    id = ObjectId(result[0]['_id'])
                else:
                    id = result[0]['_id']
                self._data['_id'] = id
                self.col.update({'public_key': self.get('public_key')}, self.get())
                del self._data['_id']
            else:
                self.col.insert(self.get())
                del self._data['_id']
            return "save ok"
        except:
            raise
    
    def getIpList(self):
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
                            "_id" : 0,
                            "ip_address" : "$data.identity.ip_address",
                        }
                    },
                ]
            })['result'][0]['ip_address']

    def respondWithRelationship(self, friendNode):
        """
        This method will return a dictionary prepared to be encrypted, encoded and sent
        
        @friendNode Node instance This is used for the public and private key information
        
        returns dictionary
        """
        #TODO: apply permissions to dictionary for this relationship
        bogus1 = Node({}, {'name': 'bogus 1'})
        bogus2 = Node({}, {'name': 'bogus 2'})
        bogus3 = Node({}, {'name': 'bogus 3'})
        bogus4 = Node({}, {'name': 'bogus 4'})
        
        friend5 = self.getFriend(friendNode.get('public_key'))
        
        selfNode = Node({}, self.get('data/identity'))
        selfNode.add('data/friends', bogus1.get())
        selfNode.add('data/friends', bogus2.get())
        selfNode.add('data/friends', bogus3.get())
        selfNode.add('data/friends', bogus4.get())
        selfNode.add('data/friends', friend5)
        
        selfNode.set('data/messages', [message['message'] for message in self.getMessagesForFriend(friendNode.get('public_key'))])
        selfNode.set('data/routed_friend_requests', [routed_friend_request['routed_friend_request'] for routed_friend_request in self.getRoutedFriendRequestsForFriend(friendNode.get('public_key'))])
        
        friendNode.get().update({"data" : selfNode.get('data')})
        friendNode.preventInfiniteNesting(friendNode.get())
        friendNode.stripIdentityAndFriendsForProtocolV1(friendNode)
        friendNode.setModifiedToNow()
        return friendNode.get()
    
    def updateFromNode(self, inboundNode, impersonate=False):
        """
        inboundNode is an Node instance of a friend of self and used to update the information
        for that friend in your friends list.
        
        returns void
        """
        node = Node(inboundNode)
        friend = self.getFriend(node.get('public_key'))
        if friend:
            if impersonate:
                self.sync(inboundNode)
            else:
                friend = Node(friend)
                if 'permissions' in node.get():
                    if not 'permissions' in friend.get():
                        friend.set('permissions_approved', "0", True)
                        friend.set('permissions', node.get('permissions'))
                    else:
                        if set(node.get('permissions')) != set(friend.get('permissions')):
                            friend.set('permissions_approved', "0")
                            friend.set('permissions', node['permissions'])
                            
                if not 'modified' in friend.get() or float(friend.get('modified')) < float(node.get('modified')):
                    #we're going to directly set this element because we want to retain the modified time
                    
                    if "web_token" in node.get():
                        self.setFriendWebToken(node, node.get('web_token'))
                        
                    tempList = []
                    for x in node._data['data']['friends']:
                        tempDict = {} 
                        tempDict['public_key'] = x['public_key']
                        if 'data' in x:
                            if 'identity' in x['data']:
                                if 'name' in x['data']['identity']:
                                    tempDict['data'] = {}
                                    tempDict['data']['identity'] = {}
                                    tempDict['data']['identity']['name'] = x['data']['identity']['name']
                                    tempDict['data']['identity']['ip_address'] = x['data']['identity']['ip_address']
                        tempList.append(tempDict)
                        
                    node._data['data']['friends'] = tempList
                    node._data['modified'] = node._data['modified']
                    
                    self.setFriendData(node, node.get('data'))
                else:
                    pass
        elif self.get('public_key') == node.get('public_key'):
            self.sync(node.get())
            self.save()