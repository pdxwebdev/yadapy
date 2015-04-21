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
    host = None
    port = None
    def __init__(self, *args, **kwargs):
        
        if 'host' in kwargs:
            self.host = kwargs['host'] 
        if 'port' in kwargs:
            self.port = kwargs['port']

        if 'public_key' in kwargs:
            args = [x for x in args]
            args.insert(0, self.getProfileIdentity(kwargs['public_key']))
            
        super(Node, self).__init__(*args, **kwargs)
    
    def matchFriend(self, friend):
        keys = self.db.friends.find({"public_key": self.get('public_key'), "friend_public_key" : {"$in": friend.getFriendPublicKeysArray()}}, {'friend_public_key': 1})
        if keys.count() > 0:
            return self.getFriend(keys[0]['friend_public_key'])
        else:
            return None
        
    def matchAnyFriend(self, friend):
        keys = self.db.friends.find({"friend_public_key" : {"$in": friend.getFriendPublicKeysArray()}}, {'friend_public_key': 1})
        if keys.count() > 0:
            return self.getFriend(keys[0]['friend_public_key'])
        else:
            return None
    
    def matchedFriendsPublicKeys(self, friend):
        
        keys = self.db.friends.find({"public_key": self.get('public_key'), "friend_public_key" : {"$in": friend.getFriendPublicKeysArray()}}, {'friend_public_key': 1})
            
        if keys.count() > 0:
            return keys
        else:
            return None
        
    def addFriend(self, friend):
        self.db.friends.insert({'public_key': self.get('public_key'), 'friend_public_key': friend['public_key'], 'friend': friend})
        try:
            self.addStatus({'content': {
                                        'ref_id': friend['public_key'], 
                                        'type': 'friends', 
                                        'newOrUpdate': 'new',
                                        'name': friend['data']['identity']['name'],
                                        'avatar': friend['data']['identity']['avatar']
                            },                                     
                            'timestamp': self.newTimeStamp(), 
                            'share_id': str(uuid4()),
                            'tags': [
                                {
                                'public_key': friend['public_key'],
                                'routed_public_key': friend['routed_public_key'],
                                'source_indexer_key': friend['source_indexer_key'],
                                'name': friend['data']['identity']['name'],
                                'avatar': friend['data']['identity']['avatar']
                                }
                                ]
                            })
        except:
            pass
        
    def addMessage(self, message):
        #self.pushItem('data.messages', message)
        for public_key in message['public_key']:
            if self.getFriend(public_key):
                self.db.messages.insert({'public_key': self.get('public_key'), 'friend_public_key': public_key, 'message': message})
            
    def addStatus(self, status):
        self.db.status.insert({'public_key': self.get('public_key'), 'status': status})
        
    def addFriendRequest(self, packet):
        self.pushItem('friend_requests', packet)
        
    def addRoutedFriendRequest(self, packet):
        #self.pushItem('data.routed_friend_requests', packet)
        self.db.routed_friend_requests.insert({'public_key': self.get('public_key'), 'routed_public_key': packet['routed_public_key'], 'routed_friend_request': packet})
        
    def addPromotionRequest(self, packet):
        #self.pushItem('promotion_requests', packet)
        self.db.promotion_requests.insert({'public_key': self.get('public_key'), 'promotion_request': packet})
         
    def addIPAddress(self, ipAddress):
        self.pushItem('data.identity.ip_address', ipAddress)
        
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
                result = self.col.find({'public_key':self.get('public_key')}, {'_id':1})
                if type(result[0]['_id']) == type(''):
                    id = ObjectId(result[0]['_id'])
                else:
                    id = result[0]['_id']
            status = self.col.update({'_id':id}, {'$push' : {path: item}})
            status = self.col.update({'_id':id}, {'$set' : {'modified': self.setModifiedToNow()}})
            return "save ok"
        except:
            raise
   
    def removeFriend(self, friend):
        self.db.friends.remove({"public_key": self.get('public_key'), "friend_public_key":friend['public_key']})
     
    def setFriendData(self, friend, data):
        self.setFriendAttribute(friend, 'data', data)

    def setFriendWebToken(self, friend, data):
        self.setFriendAttribute(friend, 'web_token', data)

    def setFriendAttribute(self, friend, path, data):
        self.col.update({"data.friends": {"$elemMatch": {"public_key": friend.get('public_key')}}}, {"$set": {"data.friends.$.%s" % path: data}})
                
    def getFriend(self, public_key):
        friend = self.db.friends.find({'public_key': self.get('public_key'), 'friend_public_key': public_key}, {'friend': 1})
            
        if friend.count() > 0:
            return friend[0]['friend']
        else:
            return super(Node, self).getFriend(public_key)
        
    def getFriends(self, limit=5):
        friends = self.db.friends.find(
            {
                'public_key': self.get('public_key')
            }, 
            {
                'friend': 1
            }
        ).sort('friend.data.status.timestamp', -1).limit(limit)
        
        if friends.count() > 0:
            friendList = [friend['friend'] for friend in friends]
            return friendList
        else:
            return super(Node, self).get('data/friends')

    def getFriendsWhoTaggedMe(self, limit=5):
        self.db.friends.ensure_index([("public_key",1), ("friend.data.status.tags.public_key",1)])
        self.db.friends.ensure_index([('friend.data.status.timestamp', -1)])
        friends = self.db.friends.find(
            {
                'public_key': self.get('public_key'),
                'friend.data.status.tags.public_key' : {"$in": [pf['friend_public_key'] for pf in self.getFriendPublicKeyList()]}
            }, 
            {
                'friend': 1
            }
        ).hint([("public_key",1), ("friend.data.status.tags.public_key",1)]).limit(limit).sort('friend.data.status.timestamp', -1)
        
        friendList = []
        
        for friend in friends:
            friendList.append(friend['friend'])
            for status in friend['friend']['data']['status']:
                childStatusFriends = self.db.friends.find(
                    {
                        'public_key': self.get('public_key'),
                        'friend.data.status.tags.share_id' : status['share_id']
                    }, 
                    {
                        'friend': 1
                    }
                ).hint([("public_key",1), ("friend.data.status.tags.public_key",1)]).limit(limit).sort('friend.data.status.timestamp', -1)
                for childStatusFriend in childStatusFriends:
                    friendList.append(childStatusFriend['friend'])
        
        if friends.count() > 0:
            return friendList
        else:
            try:
                return super(Node, self).get('data/friends')
            except:
                return []
        
    def getFriendBySourceIndexerKey(self, public_key):
        friend = self.db.friends.find({'public_key': self.get('public_key'), 'friend.data.friends.source_indexer_key': public_key}, {'friend': 1})
            
        if friend.count() > 0:
            return friend[0]['friend']
        else:
            return []
        
    def getIndexerFriends(self):
        indexerFriends = self.db.friends.find(
            {
                'public_key': self.get('public_key'), 
                '$or':[
                    {
                        'friend_public_key': {
                            '$in': self.getRoutedPublicKeysAndSourceIndexerKeys()
                        }
                    },
                    {
                        'friend.data.type': {
                            '$in': ['manager', 'indexer']
                        }
                    }
                ]
            }
        )
        return [friend['friend'] for friend in indexerFriends]
    
    def getFriendsRoutedThroughIndexers(self, indexerList):
        indexerPublicKeys = [indexer['public_key'] for indexer in indexerList]
        friendsRoutedThroughIndexers = self.db.friends.find(
            {
                'public_key': self.get('public_key'), 
                "$or": [
                    {
                         'friend.source_indexer_key': {
                            '$in': indexerPublicKeys
                        }
                    },
                    {
                        'friend.routed_public_key': {
                            '$in': indexerPublicKeys
                        }
                    }
                ]
            }
        )
        keysAdded = []
        retFriendsRoutedThroughIndexers = []
        for friendRoutedThroughIndexer in friendsRoutedThroughIndexers:
            if not friendRoutedThroughIndexer['friend']['source_indexer_key'] in keysAdded and \
                not friendRoutedThroughIndexer['friend']['routed_public_key'] in keysAdded:
                
                    keysAdded.append(friendRoutedThroughIndexer['friend']['source_indexer_key'])
                    keysAdded.append(friendRoutedThroughIndexer['friend']['routed_public_key'])
                    retFriendsRoutedThroughIndexers.append(friendRoutedThroughIndexer['friend'])
                
        return retFriendsRoutedThroughIndexers
        
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
    
    def getPromotionRequests(self):
        return self.db.promotion_requests.find({"public_key" : self.get('public_key')}, {"promotion_request" : 1})
    
    def getFriendPublicKeyList(self):
        return self.db.friends.find({"public_key" : self.get('public_key')}, {"friend_public_key" : 1})
    
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
    
    def getFriendByShareId(self, share_id):
        friends = self.db.friends.find({"public_key": self.get("public_key"), "friend.data.status.share_id" : share_id}, {"friend_public_key" : 1})
        
        if friends.count() > 0:
            return self.getFriend(friends[0]['friend_public_key'])
        else:
            return None
    
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
    
    def getIdentity(self):
        return self.db.identities.find({'public_key': self.get('public_key')}, {'data.identity': 1, "_id": 0})[0]['data']['identity']
    
    def getNodeType(self):
        result = self.db.identities.find({'public_key': self.get('public_key')}, {'data.type': 1, "_id": 0})[0]['data']
        if 'type' in result:
            return result['type']
        else:
            return 'node'
    
    def getStaticFriend(self):
        return [x['friend'] for x in self.db.friends.find({'public_key': self.get('public_key'),'friend.data.type': 'static'})]
    
    def getMessagesForFriend(self, public_key):
        messages = self.db.messages.find({'public_key': self.get('public_key'), 'friend_public_key': public_key})
            
        if messages.count() > 0:
            return [message['message'] for message in messages]
        else:
            return []

    def getRoutedFriendRequestsForFriend(self, public_key):
        requests = self.db.routed_friend_requests.find({'public_key': self.get('public_key'), 'routed_public_key': public_key})
            
        if requests.count() > 0:
            return [request['routed_friend_request'] for request in requests]
        else:
            return []
        
    def getStatusesForFriend(self, public_key):
        #TODO: use public key for some possible filtering
        statuses = self.db.status.find({'public_key': self.get('public_key')})
            
        if statuses.count() > 0:
            return [status['status'] for status in statuses]
        else:
            return []

    def getRoutedPublicKeysAndSourceIndexerKeys(self):
        routedPublicKeysAndSourceIndexerKeys = self.db.friends.find({'public_key': self.get('public_key'), 'friend.routed_public_key': {'$exists': True}, 'friend.source_indexer_key': {'$exists': True}}, {'friend.routed_public_key': 1, 'friend.source_indexer_key': 1, '_id': 0})
            
        if routedPublicKeysAndSourceIndexerKeys.count() > 0:
            friends = [routedPublicKeyAndSourceIndexerKey['friend'] for routedPublicKeyAndSourceIndexerKey in routedPublicKeysAndSourceIndexerKeys]
            keys = []
            keys.extend([friend['routed_public_key'] for friend in friends])
            keys.extend([friend['source_indexer_key'] for friend in friends])
            return keys
        else:
            return super(Node, self).getRoutedPublicKeysAndSourceIndexerKeys()
        
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
            
    def isMutual(self, externalNode, notThisNode = None, source_node = None, dest_node=None):
        #to determine if an external node is already your friend
    
        if isinstance(externalNode, Node):
            externalNode = externalNode.get()
            
        directFriend = self.getFriend(externalNode['public_key'])
        if directFriend:
            return Node(directFriend)
        
        if 'type' in self.get('data') and self.get('data/type') in ['manager', 'indexer']:
            useKeys = [source_node['public_key'], dest_node['public_key']]
            friends = self.db.friends.find(
                {
                    'public_key': self.get('public_key'),
                    '$or' : [
                             {'friend.dest_node_key': {'$in': useKeys}},
                             {'friend.source_node_key': {'$in': useKeys}}
                    ],
                    
                }, 
                {
                    '_id': 0,
                    'friend': 1
                }
            )
            if friends.count():
                return Node(friends[0]['friend'])
            
        if 'friends' not in externalNode['data']:
            return None
        
        return self.alreadyFriends(externalNode, notThisNode)
    
    def alreadyFriends(self, externalNode, notThisNode = None):
        #to determine if an external node is already your friend
    
        if isinstance(externalNode, Node):
            externalNode = externalNode.get()
                    
        try:
            friend2Keys = self.getRPandSIKeys(externalNode)
            
            useKeys = []
            for friend in externalNode['data']['friends']:
                if friend['public_key'] in friend2Keys:
                    useKeys.append(friend['public_key'])
            
            friends = self.db.friends.find(
                {
                    'public_key': self.get('public_key'),
                    '$or' : [
                             {'friend.data.friends.routed_public_key': {'$in': useKeys}},
                             {'friend.data.friends.source_indexer_key': {'$in': useKeys}}
                    ],
                    
                }, 
                {
                    '_id': 0,
                    'friend': 1
                }
            )
            if friends.count():
                return Node(friends[0]['friend'])
            else:
                raise 
        except:
            if 'source_indexer_key' in externalNode and 'routed_public_key' in externalNode:
                friends = self.db.friends.find(
                    {
                        'public_key': self.get('public_key'),
                        'friend.data.friends.public_key': {'$in': [externalNode['routed_public_key'], externalNode['source_indexer_key']]}                    
                    },
                    {
                        '_id': 0,
                        'friend': 1
                    }
                )
                if friends.count():
                    if notThisNode:
                        if friends[0]['friend']['public_key'] == notThisNode['public_key']:
                            return Node(friends[1]['friend'])
                        else:
                            return Node(friends[0]['friend'])
                    else:
                        #without notThisNode, we cannot accurately determine the correct node 
                        #if we are friends with two friends having friends with public_keys equal to source_indexer_key and routed_public_key
                        return None
                else:
                    return None
            if 'data' in self.get() and 'type' in self.get('data') and self.get('data/type') in ['manager', 'indexer']:
                useKeys = []
                for friend in externalNode['data']['friends']:
                    useKeys.append(friend['public_key'])
                friends = self.db.friends.find(
                    {
                        'public_key': self.get('public_key'),
                        'friend_public_key': {'$in': useKeys}                    
                    },
                    {
                        '_id': 0,
                        'friend': 1
                    }
                )
                if friends.count():
                    if friends[0]['friend']['public_key'] != externalNode['public_key']:
                        return Node(friends[0]['friend'])
            
            if 'type' in externalNode['data'] and externalNode['data']['type'] in ['manager', 'indexer']:
                useKeys = []
                for friend in externalNode['data']['friends']:
                    useKeys.append(friend['public_key'])
                friends = self.db.friends.find(
                    {
                        'public_key': self.get('public_key'),
                        'friend.data.friends.public_key': {'$in': useKeys}
                    },
                    {
                        '_id': 0,
                        'friend': 1
                    }
                )
                if friends.count():
                    return Node(friends[0]['friend'])
                else:
                    return None
            else:
                return None
                
    def respondWithRelationship(self, friendNode):
        """
        This method will return a dictionary prepared to be encrypted, encoded and sent
        
        @friendNode Node instance This is used for the public and private key information
        
        returns dictionary
        """
        #TODO: apply permissions to dictionary for this relationship
        
        selfNode = Node({}, self.getIdentity())
        
        selfNode.set('data/type', self.getNodeType(), True)
        
        indexerList = self.getIndexerFriends()
        if len(indexerList) > 1:
            pass
        
        if 'data' in self.get() and 'type' in self.get('data') and self.get('data/type') in ['manager', 'indexer']:
            selfNode.set('data/friends', [])
            staticFriends = self.getStaticFriend()
            if staticFriends:
                pubKeyList = [key['public_key'] for key in selfNode.get('data/friends')]
                for friend in staticFriends:
                    if not friend['public_key'] in pubKeyList:
                        selfNode.add('data/friends', friend)
            else:
                staticFriend = Node({}, {'name':'static friend'})
                staticFriend.set('data/type', 'static', True)
                self.addFriend(staticFriend.get())
                selfNode.add('data/friends', friend)
        else:
            if indexerList:
                [selfNode.add('data/friends', indexer) for indexer in indexerList]
            
            pubKeyList = [key['public_key'] for key in selfNode.get('data/friends')]
            
            friendList = self.getFriendsWhoTaggedMe(15)
            if friendList:
                for friend in friendList:
                    if not friend['public_key'] in pubKeyList:
                        selfNode.add('data/friends', friend)
                        
            friendsCount = self.db.friends.find(
                {
                    'public_key': self.get('public_key')
                }
            ).count()
            
            friend5 = self.getFriend(friendNode.get('public_key'))
            
            pubKeyList = [key['public_key'] for key in selfNode.get('data/friends')]
            if not friend5['public_key'] in pubKeyList:
                selfNode.add('data/friends', friend5)
            
            #indexer giveaway
            friendsRoutedThroughIndexers = self.getFriendsRoutedThroughIndexers(indexerList)
            for friendRoutedThroughIndexer in friendsRoutedThroughIndexers:
                if not friendRoutedThroughIndexer['public_key'] in pubKeyList:
                    selfNode.add('data/friends', friendRoutedThroughIndexer)
            
            selfNode.set('data/friends_count', friendsCount, True)
            
        if 'include_node' in friendNode.get():
            includeFriend = self.getFriend(friendNode.get('include_node'))
            includeFriend['immutable'] = "true"
            selfNode.add('data/friends', includeFriend)
            
        selfNode.set('data/messages', self.getMessagesForFriend(friendNode.get('public_key')))
        selfNode.set('data/routed_friend_requests', self.getRoutedFriendRequestsForFriend(friendNode.get('public_key')))
        selfNode.set('data/status', self.getStatusesForFriend(friendNode.get('public_key')))
        
        
        friendNode.get().update({"data" : selfNode.get('data')})
        friendNode.preventInfiniteNesting(friendNode.get())
        friendNode.stripIdentityAndFriendsForProtocolV1(friendNode)
        friendNode.setModifiedToNow()
        return friendNode.get()
    
    def updateFromNode(self, inboundNode, impersonate=False, preserve_key=None):
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
                    
                    selfInFriend = {}
                    if node and 'data' in node.get() and 'friends' in node.get('data'):
                        for f in node.get('data/friends'):
                            if f['public_key'] == node.get('public_key'):
                                selfInFriend = f
                                break
                    try:
                        self.sync(selfInFriend, is_self = False, permission_object = node.get('permissions'))
                    except:
                        pass
                    
                    if "web_token" in node.get():
                        self.setFriendWebToken(node, node.get('web_token'))
                        
                    tempList = []
                    for x in node._data['data']['friends']:
                        if 'immutable' in x and x['immutable'] == 'true':
                            tempDict = x
                            tempList.append(tempDict)
                            continue
                        tempDict = {} 
                        tempDict['public_key'] = x['public_key']
            
                        if x.get('source_indexer_key', None):
                            tempDict['source_indexer_key'] = x['source_indexer_key']
                        
                        if x.get('routed_public_key', None):
                            tempDict['routed_public_key'] = x['routed_public_key']
                            
                        if 'data' in x:
                            if 'identity' in x['data']:
                                if 'name' in x['data']['identity']:
                                    tempDict['data'] = {}
                                    tempDict['data']['identity'] = {}
                                    tempDict['data']['identity']['name'] = x['data']['identity']['name']
                                    tempDict['data']['identity']['ip_address'] = x['data']['identity']['ip_address']
                                    if 'status' in x['data']:
                                        tempDict['data']['status'] = x['data']['status']
                                    if 'avatar' in x['data']['identity']:
                                        tempDict['data']['identity']['avatar'] = x['data']['identity']['avatar']
                                    
                                    if x['public_key'] == preserve_key:
                                        tempDict = x
                                        
                        tempList.append(tempDict)
                        
                    node._data['data']['friends'] = tempList
                    node._data['modified'] = node._data['modified']
                    friend.sync(node.get(), array_update = False)
                    
                    friend.syncStfStatuses(node.get())                                            
                    
                    self.db.friends.update({'public_key': self.get('public_key'), "friend_public_key": node.get('public_key')}, {'$set': {"friend.data" : friend.get('data'), "friend.modified": node.get('modified')}})
                else:
                    raise BaseException("Friend not updated. Old node newer than inbound node.")
        elif self.get('public_key') == node.get('public_key'):
            self.sync(node.get())
            self.save()
