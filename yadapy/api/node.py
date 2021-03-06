import json, logging, os, copy, re
from uuid import uuid4
from yadapy.lib.crypt import decrypt, encrypt
from pymongo import Connection
from base64 import b64encode, b64decode
from yadapy.indexer import Indexer
from yadapy.db.mongodb.node import Node
from yadapy.db.mongodb.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from yadapy.db.mongodb.lib.jsonencoder import MongoEncoder


class MongoApi(object):
    def __init__(self, nodeComm = None):
        self.nodeComm = nodeComm
    
    def getCounts(self, data, decrypted):
        friend_requestCount=0
        messageCount=0
        try:
            latestMessageGUIDs = decrypted['latestMessageGUIDs']
            friendRequestPublicKeys = decrypted['friendRequestPublicKeys']
            node = Node({}, {'name': 'for api'})
            node.get().update(data)
            friend = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key'],
                                "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.routed_friend_requests"
                         },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests.routed_public_key" : {"$in": [friend['friend_public_key'] for friend in node.getFriendPublicKeyList()]}
                            }
                        },
                        {
                            "$project" : {
                                          "public_keym" :"$friend.public_key",
                                          "request_public_keym" : "$friend.data.routed_friend_requests.public_key",
                                          "routed_public_keym" : "$friend.data.routed_friend_requests.routed_public_key"
                                        }
                        },
                    ]
                })
            localFriendRequest = Node.db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend_requests"
                         },
                        {
                            "$project" : {
                                          "public_keym" :"$public_key",
                                          "request_public_keym" : "$friend_requests.public_key",
                                        }
                        },
                    ]
                })
            #this is a heck because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(friend['result']):
                if 'routed_public_keym' in r and r['routed_public_keym']==r['public_keym'] and not r['request_public_keym'] in friendRequestPublicKeys:
                    friend_requestCount+=1

            for i, r in enumerate(localFriendRequest['result']):
                if 'request_public_keym' in r and not r['request_public_keym'] in friendRequestPublicKeys:
                    friend_requestCount+=1
            
            message = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
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
                                "public_key" : "$friend.public_key",
                                "message" : {
                                             "thread_id" : "$friend.data.messages.thread_id",
                                             "guid" : "$friend.data.messages.guid",
                                             "timestamp" : "$friend.data.messages.timestamp",
                                             "public_key" : "$friend.data.messages.public_key",
                                             },
                            }
                        },
                        {
                            "$sort" :{
                                    "timestamp": 1  
                            }
                         },
                        {
                            "$group" : {
                            "_id" : "$message.thread_id",
                             "guid" : {"$first" : "$message.guid"},
                             "timestamp" : {"$max" : "$message.timestamp"},
                             "public_keym" : {"$first" : "$public_key"},
                             "message_public_keym" : {"$first" : "$message.public_key"},
                            }
                        },
                    ]
                })
            #this is a hack because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(message['result']):
                if 'message_public_keym' in r and 'public_keym' in r:
                    if r['public_keym'] in r['message_public_keym'] and not r['guid'] in latestMessageGUIDs:
                        messageCount+=1
                    
            return {"messages": messageCount, "friend_requests" : friend_requestCount, "requestType" : "getCounts"}
        except:
            raise
    
    
    
    
    def getFriends(self, data, decrypted):
        
        friend = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$project" : {
                                "public_key" : "$friend.public_key",
                                "name" : "$friend.data.identity.name",
                                "avatar" : "$friend.data.identity.avatar",
                                "modified" : "$friend.modified",
                                "timestamp" : "$friend.timestamp",
                                "_id" : 0
                            }
                        }]
                    })
        return {'friends' : friend['result'], 'requestType' : 'getFriends'}
    
    def getFriendSubscriptions(self, data, decrypted):
        
        friendUpdater(data, decrypted)
        
        query = {'public_key': data['public_key']}
        
        tagList = []
        [tagList.extend(tag['status']['tags']) for tag in Node.db.status.find(query, {'_id': 0, "status.tags": 1})]
        tagList = [tag['public_key'] for tag in tagList]
        
        
        if tagList:
            query['friend_public_key'] = {"$in": tagList}
            
        statusList = Node.db.friends.find(query, {'_id': 0, 
                                                  'friend.public_key': 1, 
                                                  'friend.modified': 1,
                                                  'friend.timestamp': 1,
                                                  'friend.data.status': 1, 
                                                  'friend.data.identity.name': 1, 
                                                  'friend.data.identity.avatar': 1,}
        )
        
        return {'status' : [status['friend'] for status in statusList], 'requestType' : 'getFriendSubscriptions'}
    
    def getFriend(self, data, decrypted):
        
        friendUpdater(data, decrypted)
        
        friend = Node.db.friends.find({"public_key" : data['public_key'], "friend_public_key" : decrypted['public_key']}, {'friend': 1})
        
        if friend.count():
            
            #so the goal here is to make any mutual STF refer to your FTF
            selectedFriend = friend[0]['friend']
            getMutualFriends(data, selectedFriend)
            return selectedFriend
        else:
            return {}
    
    
    def getThreads(self, data, decrypted):
        posts = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
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
                            "$match" : {
                                "friend.data.messages.thread_id" : {"$type" : 2}
                            }
                        },
                        {
                            "$project" : {
                                "public_key" : "$friend.public_key",
                                "message" : {
                                             "thread_id" : "$friend.data.messages.thread_id",
                                             "guid" : "$friend.data.messages.guid",
                                             "timestamp" : "$friend.data.messages.timestamp",
                                             "public_key" : "$friend.data.messages.public_key",
                                             "subject" : "$friend.data.messages.subject",
                                             "name" : "$friend.data.identity.name",
                                             "avatar" : "$friend.data.identity.avatar",
                                             },
                            }
                        },
                        {
                            "$sort" :{
                                    "timestamp": 1  
                            }
                         },
                        {
                            "$group" : {
                            "_id" : "$message.thread_id",
                            "friend_public_key" : {"$first" : "$public_key"},
                             "guid" : {"$first" : "$message.guid"},
                             "timestamp" : {"$max" : "$message.timestamp"},
                             "public_key" : {"$first" : "$message.public_key"},
                            "subject" : {"$first" : "$message.subject"},
                            "name" : {"$first" : "$message.name"},
                            "avatar" : {"$first" : "$message.avatar"},
                            }
                        }]
                    })
        finalPosts = []
        for i, r in enumerate(posts['result']):
            if 'avatar' not in r:
                r['avatar'] = ''
            finalPosts.append(r)
        posts = Node.db.command(
                {
                    "aggregate" : "messages", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$project" : {
                                "public_key" : "$public_key",
                                "message" : {
                                             "thread_id" : "$message.thread_id",
                                             "guid" : "$message.guid",
                                             "timestamp" : "$message.timestamp",
                                             "public_key" : "$message.public_key",
                                             "subject" : "$message.subject",
                                             },
                            }
                        },
                        {
                            "$group" : {
                            "_id" : "$message.thread_id",
                            "friend_public_key" : {"$first" : "$public_key"},
                             "guid" : {"$first" : "$message.guid"},
                             "timestamp" : {"$max" : "$message.timestamp"},
                             "public_key" : {"$first" : "$message.public_key"},
                            "subject" : {"$first" : "$message.subject"},
                            }
                        },]
                    })
        finalPosts = dict((x['_id'], x) for x in finalPosts)
        for i, r in enumerate(posts['result']):
            if 'avatar' not in r:
                if 'avatar' in data['data']['identity']:
                    r['avatar'] = data['data']['identity']['avatar']
                else:
                    r['avatar'] = ''
                    
            if 'name' not in r:
                r['name'] = data['data']['identity']['name']
            if not r['_id'] in finalPosts:
                finalPosts[r['_id']] = r
            elif finalPosts[r['_id']]['timestamp'] < r['timestamp']:
                finalPosts[r['_id']] = r
                
        return {'threads':[{'thread_id': x['_id'], 'public_key' : x['public_key'], 'name' : x['name'], 'subject' : x['subject'], 'avatar' : x['avatar'], 'guid' : x['guid'], 'timestamp': float(x['timestamp'])} for i, x in finalPosts.items()], 'requestType' : 'getThreads'}
        
    
    def getThread(self, data, decrypted):
        guids_added = []
        friendPosts = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "friend.data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : 1,
                                "message" : "$friend.data.messages",
                            }
                        },
                        {
                            "$unwind" : "$message"
                         },
                        {
                            "$match" : {
                                "message.thread_id" : decrypted['thread_id']
                            }
                        },
                        {
                            "$project" : {
                                          "message" : 1,
                                          "name" : "$friend.data.identity.name",
                                          "avatar" : "$friend.data.identity.avatar"
                                          }
                         }
                         ]
                    })['result']
        for x in friendPosts:
            if 'avatar' not in x:
                x['avatar'] = ''
            x['message']['name'] = x['name']
            x['message']['avatar'] = x['avatar']
        friendPosts = [x['message'] for x in friendPosts]
        for i, post in enumerate(friendPosts):
            post['timestamp'] = int(round(float(post['timestamp']),0))
            post['who'] = 'friend'
            post['message'] = b64decode(post['message'])
            guids_added.append(post['guid'])
        posts = Node.db.command(
                {
                    "aggregate" : "messages", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key'],
                                "message.thread_id" : decrypted['thread_id']
                            }
                        },
                        {
                            "$project" : {
                                "message" : 1,
                            }
                        },
                         ]
                    })['result']
        for x in posts:
            if 'avatar' not in x:
                x['avatar'] = ''
            x['message']['name'] = 'me'
        posts = [x['message'] for x in posts]
        for i, post in enumerate(posts):
            post['timestamp'] = int(round(float(post['timestamp']),0))
            post['who'] = 'me'
            post['message'] = b64decode(post['message'])
            guids_added.append(post['guid'])
        posts.extend(friendPosts)

        return {'thread':posts}
    
    
    def getStatus(self, data, decrypted):
        friends = Node.db.friends.find({"public_key" : data['public_key']}, {'friend': 1})
        posts = []        
        ignore = []
        
        statuss = Node.db.status.find({"public_key" : data['public_key'], "status.share_id": {"$not": {"$in": ignore}}}, {'_id': 0, 'status': 1})
        if statuss.count():
            for st in statuss:
                st = st['status']
                if not st['share_id'] in ignore:
                    ignore.append(st['share_id'])
                    if 'data' in data and 'identity' in data['data'] and 'avatar' in data['data']['identity']:
                        st['avatar'] = data['data']['identity']['avatar']
                    st['name'] = data['public_key']
                    st['public_key'] = data['public_key']
                    st.update({'blob': copy.deepcopy(st)})
                    posts.append(st) 
        
        friendUpdater(data, decrypted)
            
        for friend in friends:
            #we are excluding yada project status updates with this next line
            statusFriendTest = Node.db.friends.find({'public_key': YadaServer._data['public_key'], 'friend_public_key': friend['friend']['public_key']})
            if statusFriendTest.count() == 0:
                friend = friend['friend']
                try:
                    posts.extend(gatherStatuses(friend, ignore))
                except:
                    pass
            
        friends = Node.db.friends.find({"public_key" : data['public_key']}, {'friend': 1})
        for friend in friends:
            #we are excluding yada project status updates with this next line
            statusFriendTest = Node.db.friends.find({'public_key': YadaServer._data['public_key'], 'friend_public_key': friend['friend']['public_key']})
            if statusFriendTest.count() == 0:
                friend = friend['friend']
                getMutualFriends(data, friend)
                try:
                    for friendOfFriend in friend['data']['friends']:
                        posts.extend(gatherStatuses(friendOfFriend, ignore))
                except:
                    pass
        
        posts = sorted(posts, key=lambda status: status['timestamp'], reverse=True)
        return {'status':posts, 'requestType':'getStatus'}
    
    def getFriendRequests(self, data, decrypted):
        posts = []
        ignoredRequests = decrypted['ignoredRequests']
        logging.debug(ignoredRequests)
        node = Node({}, {'name': 'for api'})
        node.get().update(data)
        friend = Node.db.command(
            {
                "aggregate" : "friends", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : data['public_key'],
                            "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                        }
                    },
                    
                    {
                        "$unwind" : "$friend.data.routed_friend_requests"
                     },
                    {
                        "$match" : {
                            "friend.data.routed_friend_requests.routed_public_key" : {"$in": [friend['friend_public_key'] for friend in node.getFriendPublicKeyList()]}
                        }
                    },
                    {
                        "$project" : {
                                      "public_key" :"$friend.public_key",
                                      "request_public_key" : "$friend.data.routed_friend_requests.public_key",
                                      "routed_public_key" : "$friend.data.routed_friend_requests.routed_public_key",
                                      "name": "$friend.data.routed_friend_requests.data.identity.name"
                                    }
                    },
                ]
            })['result']
        localFriendRequest = Node.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : data['public_key']
                        }
                    },
                    {
                        "$match" : {
                            "friend_requests" : { "$not" : {"$size" : 0}}
                        }
                    },
                    {
                        "$unwind" : "$friend_requests"
                     },
                    {
                        "$project" : {
                                      "public_key" :"$public_key",
                                      "request_public_key" : "$friend_requests.public_key",
                                      "name" : "$friend_requests.data.identity.name"
                                    }
                    },
                ]
            })['result']
        logging.debug(localFriendRequest) 
        
        for request in friend:
            if 'routed_public_key' in request and not request['request_public_key'] in ignoredRequests:
                posts.append({'public_key' : request['request_public_key'], 'name' : request['name']})
                
        for request in localFriendRequest:
            if 'request_public_key' in request and not request['request_public_key'] in ignoredRequests:
                if not request['name']:
                    name = 'blank name'
                else:
                    name = request['name']
                posts.append({'public_key' : request['request_public_key'], 'name' : name})
        logging.debug(posts) 
        return {'friend_requests':posts, 'requestType':'getFriendRequests'}
    
    
    def getFriendRequest(self, data, decrypted):
        posts = []
        friend = Node.db.command(
                {
                    "aggregate" : "friends", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key'],
                                "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.routed_friend_requests"
                        },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests.public_key" : decrypted['public_key']
                            }
                        },
                        {
                            "$project" : {
                                          "routed_public_key" :"$friend.data.routed_friend_requests.routed_public_key",
                                          "friendRequest" : "$friend.data.routed_friend_requests"
                                        }
                        },
                    ]
                })['result']
                
        localFriendRequest = Node.db.command(
            {
                "aggregate" : "identities", "pipeline" : [
                    {
                        "$match" : {
                            "public_key" : data['public_key']
                        }
                    },
                    {
                        "$match" : {
                            "friend_requests" : { "$not" : {"$size" : 0}}
                        }
                    },
                    {
                        "$unwind" : "$friend_requests"
                     },
                    {
                        "$match" : {
                            "friend_requests.public_key" : decrypted['public_key']
                        }
                    },
                    {
                        "$project" : {
                                      "request_public_key" : "$friend_requests.public_key",
                                      "friendRequest" : "$friend_requests"
                                    }
                    },
                ]
            })['result']
            
        if len(friend) > 0:
            friend = friend[0]
        elif len(localFriendRequest) > 0:
            friend = localFriendRequest[0]
        else:
            return {}
        friendNode = Node(friend['friendRequest'])
        friendNode.stripIdentityAndFriendsForProtocolV1()
        return friendNode.get()
    
    
    def getIdentity(self, data, decrypted):
        node = Node(public_key=data['public_key'])
        return {'identity':node.get('data/identity'), 'requestType':'getIdentity'}
    
    def getLatestTags(self, data, decrypted):
        yadaServer = YadaServer()
        regx = re.compile("#.*", re.IGNORECASE)
        searchQuery = Node.db.friends.find({"public_key" : yadaServer.get('public_key'), "friend.data.identity.name" : regx}, {"_id":0}).limit(3).sort('friend.data.friends.data.status.timestamp', -1)
        results = [friend['friend'] for friend in searchQuery]
        return {'tags': results, 'requestType':'getLatestTags', 'new': True}
    
    def getTags(self, data, decrypted):
        yadaServer = YadaServer()
        data = Node(public_key = data['public_key'])
        tags = decrypted['tags']
        newTagList = []
        friendsAdded = []
        notFound = []
        
        matchedFriend = yadaServer.matchFriend(data)

        if 'tags' in decrypted and decrypted['tags']:
            newFriends = []
            outTags = []
            yadaServer = YadaServer()
            for requestedTag in decrypted['tags']:
                res = Node.db.friends.find({"public_key" : yadaServer.get('public_key'), "friend.data.identity.name": requestedTag.lower()})
                if res.count():
                    tag = res[0]
                    tagFriendNode = Node(tag['friend'])
                        
                    tagNode = Node(Node.col.find({'data.identity.name': tag['friend']['data']['identity']['name'].lower()})[0])
                    
                    mutualNode = data.isMutual(tagFriendNode)
                    if not mutualNode:
                        newFriend = Node({}, {'name': tag['friend']['data']['identity']['name'].lower()})
                        newFriend.set('data', copy.deepcopy(tagFriendNode.get('data')), True)
                        newFriend.set('source_indexer_key', tagFriendNode.get('public_key'), True)
                        newFriend.set('routed_public_key', matchedFriend.get('public_key'), True)
                        
                        identity = {'name': data.get('data/identity/name')}
                        try:
                            identity.update({'avatar': data.get('data/identity/avatar')})
                        except:
                            pass
                        
                        me = Node({}, identity)
                        me.set('public_key', newFriend.get('public_key'))
                        me.set('private_key', newFriend.get('private_key'))
                        me.set('source_indexer_key', matchedFriend.get('public_key'), True)
                        me.set('routed_public_key', tagFriendNode.get('public_key'), True)
                        
                        newFriend.add('data/friends', me.get(), create=True)
                        
                        data.addFriend(newFriend.get())
                            
                        tagNode.addFriend(me.get())
                        
                        nodeComm1 = NodeCommunicator(data)
                        try:
                            nodeComm1.updateRelationship(newFriend)
                        except:
                            pass
                        
                        friendsAdded.append(newFriend.get())
    
                        res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : tag['friend']['data']['identity']['name'].lower()})
                        for tag in res:
                            tagNode = Node(Node.col.find({'data.identity.name': tag['friend']['data']['identity']['name']})[0])
                            tagFriendNode = Node(tag['friend'])
                            nodeComm2 = NodeCommunicator(tagNode)
                            try:
                                nodeComm2.updateRelationship(Node(tagNode.getFriend(tagFriendNode.get('public_key'))))
                            except Exception as ex:
                                logging.exception(ex)
                        newFriends.append(newFriend.get())
                        outTags.append(newFriend.get())
                    else:
                        outTags.append(mutualNode.get())
                else:
                    notFound.append(requestedTag)
            return {'tags': outTags, 'requestType':'getTags', "friendsAdded": friendsAdded, 'notFound': notFound}
        else:
            return []

    def postTags(self, data, decrypted):

        yadaServer = YadaServer()
        alreadyAdded = []
        output = []
        
        if 'friends' not in data['data']:
            data['data']['friends'] = []
        data['data']['messages'] = []
        
        selfNode = Node(data)
        friendList = selfNode.getFriends()
        for friend in friendList:
            selfNode.add('data/friends', friend, True)
            
        matchedFriend = yadaServer.matchFriend(selfNode)
        for tag in decrypted['tags']:
            if Node.db.friends.find({"public_key" : yadaServer.get('public_key'), "friend.data.identity.name": tag['name'].lower()}).count():
                alreadyAdded.append(tag['name'])
                
            if tag['name'] not in alreadyAdded: #because it causes errors just to check, look into this later
                res = self.getTags(data, {'tags': [tag['name']]})
                if tag['name'] in res['tags']:
                    alreadyAdded.append(tag['name'])
        
            node = Node({}, {"name": tag['name'].lower(), "avatar": tag['avatar']})
            node.add('data/identity/ip_address', node.createIPAddress(Node.defaultHost, '80', '4'))
    
            newFriend = Node({}, {"name": tag['name'].lower(), "avatar": tag['avatar']})
            newFriend.set('data', copy.deepcopy(node.get('data')), force=True)
            
            newFriend.set('data/identity/name', 'yada server', force=True)
            
            node.add('data/friends', newFriend.get())
            
            newFriend.set('data', copy.deepcopy(node.get('data')), force=True)
            
            yadaServer.addFriend(newFriend.get())
            
            node.save()
            
            newFriend.set('data/identity/name', 'yada server', force=True)
            
            node.addFriend(newFriend.get())
            
            newFriendForSelf = Node({}, {"name": tag['name'].lower(), "avatar": tag['avatar']})
            newFriendForSelf.set('source_indexer_key', newFriend.get('public_key'), True)
            newFriendForSelf.set('routed_public_key', matchedFriend['public_key'], True) # need data - yadaserver public_key
            
            newFriendForSelf.set('data', copy.deepcopy(data.get('data')), True)
            node.add('data/friends', newFriendForSelf.get())
            node.addFriend(newFriendForSelf.get())
            
            newFriendForSelf.set('data/identity/name', tag['name'].lower(), True)
            newFriendForSelf.set('data/identity/avatar', tag['avatar'], True)
            output.append(copy.deepcopy(newFriendForSelf.get()))
            
            newFriendForSelf.set('data', copy.deepcopy(node.get('data')), True)
            selfNode.addFriend(newFriendForSelf.get())
            
            nodeComm = NodeCommunicator(selfNode)
            nodeComm.updateRelationship(newFriendForSelf)
                
            if tag['name'] not in alreadyAdded:
                res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : tag['name'].lower()})
                for restag in res:
                    tagNode = Node(Node.col.find({'data.identity.name': restag['friend']['data']['identity']['name']})[0])
                    tagFriendNode = Node(restag['friend'])
                    nodeComm2 = NodeCommunicator(tagNode)
                    try:
                        nodeComm2.updateRelationship(Node(tagNode.getFriend(tagFriendNode.get('public_key'))))
                    except Exception as ex:
                        raise ex
                
                alreadyAdded.append(tag['name'])
            
        return {"requestType": "postTag", "tags": output, 'alreadyAdded': alreadyAdded}
    
    def postRoutedFriendRequest(self, data, decrypted):
    
        data['data']['friends'] = []
        data['data']['messages'] = []
        node = Node(data)
        node.set('data/friends', node.getFriends(), True)
        nodeComm = NodeCommunicator(node)
        serverNode = Node(public_key = Node._data['public_key'])
        serverNodeComm = NodeCommunicator(serverNode)
        
        matchedFriend = serverNode.matchFriend(node)
        
        serverFriend = node.getFriend(matchedFriend['public_key'])
        
        serverFriend['private_key'] = matchedFriend['private_key']
        serverFriend['modified'] = 0
        serverFriend['data']['friends'] = []
        serverFriend['data']['messages'] = []
        
        serverFriendNode = Node(serverFriend)
        
        friendTest = Node.db.routed_friend_requests.find({
            'public_key': serverNode.get('public_key'), 
            'routed_public_key': decrypted['routed_public_key'],
            'routed_friend_request.source_indexer_key': serverFriend['public_key']
        })
        
        if friendTest.count() == 0 and matchedFriend['public_key'] != decrypted['routed_public_key'] and decrypted['routed_public_key'] not in node.getRoutedPublicKeysAndSourceIndexerKeys():
            friend = serverNodeComm.routeRequestForNode(node, decrypted['routed_public_key'], decrypted.get('name', decrypted['routed_public_key']), decrypted.get('avatar', ''))

            return {"status": "request sent", "friend": friend}
        return {"status": "already friends"}

    def postMessage(self, data, decrypted):
        friends_indexed = []
        data = Node(public_key = data['public_key'])
        dataNodeComm = NodeCommunicator(data, self.nodeComm.node)
        try:
            message = b64decode(decrypted['message']).decode('utf-8')
        except:
            message = decrypted['message']
        dataNodeComm.sendMessage(pub_keys=decrypted['public_key'], subject=decrypted['subject'], message=message, thread_id=decrypted['thread_id'], guid=decrypted['guid'])
        return {}
    
    
    def postStatus(self, data, decrypted):
        yadaServer = YadaServer()
        data = Node(public_key = data['public_key'])
        tags = []
        for tag in decrypted['tags']:
            if type(tag) == type('') or type(tag) == type(u''):
                tag = tag.lower()
            tags.append(tag)
        newTagList = []
        friendsAdded = []
        
        dataServerFriend = yadaServer.matchFriend(data)
        
        if 'tags' in decrypted and decrypted['tags']:
            res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : { '$in' : tags}})
            for tag in res:
                friend, new = addNewTagFriend(data, tag, dataServerFriend)
                slimFriend = {
                   'name': friend.get('data/identity/name'), 
                   'public_key': friend.get('public_key'),                       
                   'source_indexer_key': friend.get('source_indexer_key'),
                   'routed_public_key': friend.get('routed_public_key'),
                   'avatar': friend.get('data/identity/avatar')
                }
                if new:
                    friendsAdded.append(friend.get())
                newTagList.append(slimFriend)
            
            status = decrypted.copy()
            if res.count():
                status['tags'] = newTagList
                data.addStatus(status)                
            else:
                data.addStatus(status)  
                for tag in decrypted['tags']:
                    if 'share_id' in tag:
                        statusRef = Node.db.status.find({'public_key': data.get('public_key'), 'status.share_id': tag['share_id']})
                        if statusRef.count():
                            pass
                            #I did it, do nothing
                        else:
                            statusRef = Node.db.friends.find({'public_key': data.get('public_key'), 'friend.data.status.share_id': tag['share_id']})
                            
                        
                            if statusRef.count():
                                updateTagFriend(data, statusRef[0]['friend'], tag)
                            else:
                                #we are not friends with the originator of this status update. lets make friends.
                                statusRef = Node.db.command(
                                    {
                                        "aggregate" : "friends", "pipeline" : [
                                            {
                                                "$match" : {
                                                    "public_key" : data.get('public_key'),
                                                     'friend.data.friends.data.status.share_id': tag['share_id']
                                                }
                                            },
                                            {
                                                "$match" : {
                                                    "friend.data.friends" : { "$not" : {"$size" : 0}}
                                                }
                                            },
                                            {
                                                "$unwind" : "$friend.data.friends"
                                             },
                                            {
                                                "$match" : {
                                                    "friend.data.friends.data.status" : { "$not" : {"$size" : 0}}
                                                }
                                            },
                                            {
                                                "$match" : {
                                                    "friend.data.friends.data.status.share_id" : tag['share_id']
                                                }
                                            },
                                            {
                                                "$project" : {
                                                              "_id": 0,
                                                              "friend" : "$friend.data.friends",
                                                            }
                                            },
                                        ]
                                    }
                                )['result']
                                for tagItem in statusRef:
                                    tagItem = tagItem['friend']
                                    friend, new = addNewTagFriend(data, tagItem, dataServerFriend)
                                    slimFriend = {
                                       'name': friend.get('data/identity/name'), 
                                       'public_key': friend.get('public_key'),
                                    }
                                    
                                    try:
                                       slimFriend.update({'source_indexer_key': friend.get('source_indexer_key')})
                                    except:
                                        pass
                                    
                                    try:
                                       slimFriend.update({'routed_public_key': friend.get('routed_public_key')})
                                    except:
                                        pass
                                    
                                    try:
                                        slimFriend.update({'avatar': friend.get('data/identity/avatar')})
                                    except:
                                        slimFriend.update({'avatar': ''})
                                    if new:
                                        friendsAdded.append(friend.get())
                                    newTagList.append(slimFriend)
                                    updateTagFriend(data, friend, tag)
                                    
                        parentShare = Node.db.command(
                            {
                                "aggregate" : "friends", "pipeline" : [
                                    {
                                        "$match" : {
                                            "public_key" : data.get('public_key'),
                                             'friend.data.friends.data.status.share_id': tag['share_id']
                                        }
                                    },
                                    {
                                        "$match" : {
                                            "friend.data.friends" : { "$not" : {"$size" : 0}}
                                        }
                                    },
                                    {
                                        "$unwind" : "$friend.data.friends"
                                     },
                                    {
                                        "$match" : {
                                            "friend.data.friends.data.status" : { "$not" : {"$size" : 0}}
                                        }
                                    },
                                    {
                                        "$unwind" : "$friend.data.friends.data.status"
                                     },
                                    {
                                        "$match" : {
                                            "friend.data.friends.data.status.share_id" : tag['share_id']
                                        }
                                    },
                                    {
                                        "$project" : {
                                                      "_id": 0,
                                                      "status" : "$friend.data.friends.data.status",
                                                    }
                                    },
                                ]
                            }
                        )['result']
                        if parentShare and 'tags' in parentShare[0]['status']:
                            for tagItem in parentShare[0]['status']['tags']:
                                nodeComm = NodeCommunicator(data)
                                if 'friend' in statusRef[0]:
                                    statusRef = statusRef[0]['friend']
                                tagFriend = data.isMutual(tagItem, statusRef)
                                nodeComm.updateRelationship(tagFriend)
                                
                                res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : { '$in' : [tagItem['name']]}})
                                updateServerTag(res)
                                
        if 'tags' in decrypted and decrypted['tags']:
            for tag in status['tags']:
                nodeComm = NodeCommunicator(data)
                try:
                    if 'public_key' in tag:
                        nodeComm.updateRelationship(Node(data.getFriend(tag['public_key'])))
                    elif 'share_id' in tag:
                        friend = data.getFriendByShareId(tag['share_id'])
                        #the above may not always succeed, so we may not always have a friend for this share_id
                        if friend:
                            nodeComm.updateRelationship(Node(friend))
                except Exception as ex:
                    logging.warning(ex)
                
            for tag in status['tags']:
                res = []
                if 'public_key' in tag:
                    res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : { '$in' : tags}})
                    updateServerTag(res)
                elif 'share_id' in tag:
                    friend = data.getFriendByShareId(tag['share_id'])
                    #the above may not always succeed, so we may not always have a friend for this share_id
                    if friend:
                        res = Node.db.friends.find({'public_key': yadaServer.get('public_key'), 'friend.data.identity.name' : { '$in' : [friend['data']['identity']['name']]}})
                        updateServerTag(res)
               
                    
        return {"requestType": "postStatus", "friendsAdded": friendsAdded}
        
    
    def postFriend(self, data, decrypted):
        node = Node(public_key = data['public_key'])
        
        if 'messages' not in decrypted['data']:
            decrypted['data']['messages'] = []
            
        if 'friends' not in decrypted['data']:
            return {'status': 'error: no friend key in identity'}
            
        if not decrypted['data']['friends']:
            return {'status': 'error: no friends in identity, therefore it cannot be identified.'}
            
        if 'public_key' not in decrypted:
            return {'status': 'error: no public_key key in identity'}
            
        if 'private_key' not in decrypted:
            return {'status': 'error: no private_key key in identity'}
            
        friend = Node.db.friends.find({"public_key" : data['public_key'], "friend_public_key" : decrypted['public_key']}, {'friend': 1})
        if friend.count():
            return {'status': 'already friends'}

        if 'source_indexer_key' in decrypted:
            friend = Node.db.friends.find({"public_key" : data['public_key'], "friend.source_indexer_key" : decrypted['source_indexer_key']}, {'friend': 1})
            if friend.count():
                return {'status': 'already friends'}

        #TODO: check black and white lists here
        #black list relationship
        #black list identity
        #white list relationship
        #white list identity

        friend = Node(decrypted)
        mutual = node.isMutual(friend)
        nodeComm = NodeCommunicator(node)
        node.addFriend(friend.get())

        if mutual:
            nodeComm.updateRelationship(friend)
            if 'type' in mutual.get('data') and mutual.get('data/type') in ['indexer', 'manager']:
                useKeys = []
                for x in friend.get('data/friends'):
                    if x['public_key'] != friend.get('public_key'):
                        useKeys.append(x['public_key'])
                if useKeys:
                    Node.db.friends.remove({"friend.data.friends.public_key": {"$in": useKeys}, "friend_public_key": {"$ne": mutual.get('public_key')}})    
            node.removeFriend(friend.get())
            friend = mutual
        else:
            nodeComm.updateRelationship(friend)

        for fr in node.getIndexerFriends():
            if fr['public_key'] != friend.get('public_key'):
                try:
                    nodeComm.updateRelationship(Indexer(fr))
                except:
                    pass
                    
        try:
            if 'routed_friend_request' in decrypted:
                sourceIndexer = Node(node.getFriend(decrypted['routed_friend_request']))
                nodeComm.updateRelationship(sourceIndexer)
        except:
            pass
        
        return {}
    
    def postIdentity(self, data, decrypted):
        node = Node(public_key = data['public_key'])
        node.sync(decrypted)
        node.save()
        return {}
    
    def postSubscription(self, data, decrypted):
        if 'unsubscribe' in decrypted:
            Node.db.friends.update({'public_key': data['public_key'], 'friend_public_key': decrypted['public_key']}, {"$set": {"friend.subscribed": ""}}, multi=True)
        else:
            Node.db.friends.update({'public_key': data['public_key'], 'friend_public_key': decrypted['public_key']}, {"$set": {"friend.subscribed": "*"}}, multi=True)
            
        return {}

def updateTagFriend(data, statusOriginNode, tag):
    if isinstance(statusOriginNode, Node):
        statusOriginNode = statusOriginNode.get()
    for statusItem in statusOriginNode['data']['status']:
        if statusItem['share_id'] == tag['share_id'] and 'tags' in statusItem:
            for nestedTagItem in statusItem['tags']:
                myFriend = data.isMutual(nestedTagItem, statusOriginNode)
                if myFriend:
                    nodeComm = NodeCommunicator(data)
                    nodeComm.updateRelationship(myFriend)
                    
def addNewTagFriend(data, tag, matchedFriend):
    if 'friend' in tag:
        tagFriendNode = Node(tag['friend'])
        tag = tag['friend']
    else:
        tagFriendNode = tag
        
    tagNode = Node(Node.col.find({'data.identity.name': tag['data']['identity']['name']})[0])
    mutualNode = data.isMutual(tagFriendNode)
    if not mutualNode:
        newFriend = Node({}, {'name': tag['data']['identity']['name']})
        newFriend.set('data', copy.deepcopy(tagFriendNode.get('data')), True)
        newFriend.set('source_indexer_key', tagFriendNode.get('public_key'), True)
        newFriend.set('routed_public_key', matchedFriend.get('public_key'), True)
        
        identity = {'name': data.get('data/identity/name')}
        try:
            identity.update({'avatar': data.get('data/identity/avatar')})
        except:
            identity.update({'avatar': ''})
        
        me = Node({}, identity)
        me.set('public_key', newFriend.get('public_key'))
        me.set('private_key', newFriend.get('private_key'))
        me.set('source_indexer_key', matchedFriend.get('public_key'), True)
        me.set('routed_public_key', tagFriendNode.get('public_key'), True)
        
        newFriend.add('data/friends', me.get(), create=True)
        newFriend.set('data/messages', [], True)
        
        data.addFriend(newFriend.get())
            
        tagNode.addFriend(me.get())
        
        return newFriend, True
    else:
        return mutualNode, False
        
def updateServerTag(tags):
    for tag in tags:
        tagNode = Node(Node.col.find({'data.identity.name': tag['friend']['data']['identity']['name']})[0])
        tagFriendNode = Node(tag['friend'])
        nodeComm2 = NodeCommunicator(tagNode)
        try:
            nodeComm2.updateRelationship(Node(tagNode.getFriend(tagFriendNode.get('public_key'))))
        except Exception as ex:
            raise ex

def gatherStatuses(friend, ignore):
    posts = []
    if 'status' in friend['data']:
        if friend['data']['status']:
            for st in friend['data']['status']:
                if not st['share_id'] in ignore:
                    ignore.append(st['share_id'])
                    if 'data' in friend and 'identity' in friend['data'] and 'avatar' in friend['data']['identity']:
                        st['avatar'] = friend['data']['identity']['avatar']
                        
                    if friend.get('routed_public_key', None):
                        st['routed_public_key'] = friend['routed_public_key']
                        
                    if friend.get('source_indexer_key', None):
                        st['source_indexer_key'] = friend['source_indexer_key']
                        
                    st['name'] = friend['public_key']
                    st['public_key'] = friend['public_key']
                    st.update({'blob': copy.deepcopy(st)})
                    posts.append(st)
    return posts

def friendUpdater(data, decrypted):
    data['data']['friends'] = []
    data['data']['messages'] = []
    node = Node(data)
    nodeComm = NodeCommunicator(node)
    
    query = {'public_key': data['public_key'], 'friend.subscribed': '*'}
    if 'public_key' in decrypted:
        query.update({'friend_public_key': decrypted['public_key']})
        del query['friend.subscribed']
    
    statusList = Node.db.friends.find(query, {'_id': 0, 
                                              'friend.public_key': 1, 
                                              'friend.private_key': 1, 
                                              'friend.modified': 1,
                                              'friend.timestamp': 1,
                                              'friend.data.identity.name': 1, 
                                              'friend.data.identity.ip_address': 1,}
    )

    for friend in statusList:
        friend = friend['friend']
        friend['data']['friends'] = []
        friend['data']['messages'] = []
        friend['modified'] = 0
        friendNode = Node(friend)
        try:
            nodeComm.updateRelationship(friendNode)
        except:
            pass

def getMutualFriends(data, selectedFriend):
    stfs = [x for x in selectedFriend['data']['friends']]
    for stf in stfs:
        if 'routed_public_key' in stf and 'source_indexer_key' in stf:
            key_to_use = ''
            for stfTest in stfs:
                if stfTest['public_key'] == stf['routed_public_key']:
                    key_to_use = stf['source_indexer_key']
                    field_to_use = 'source_indexer_key'
                    break
                elif stfTest['public_key'] == stf['source_indexer_key']:
                    key_to_use = stf['routed_public_key']
                    field_to_use = 'routed_public_key'
                    break
                
            if key_to_use:
                #check if mutual friend
                mft = Node.db.friends.find({
                                            "public_key" : data['public_key'], 
                                            "friend.data.friends.public_key" : key_to_use
                                            })
                if mft.count():
                    #filter out the indexer result if present
                    for mftres in mft:
                        mft2 = Node.db.friends.find({
                                                    "public_key" : data['public_key'],
                                                    "$or": [
                                                        {"friend.routed_public_key": mftres['friend']['public_key']},
                                                        {"friend.source_indexer_key": mftres['friend']['public_key']}
                                                    ]})
                        if not mft2.count():
                            #is mutual friend
                            stf.update(mftres['friend'])
                else:
                    #not mutual, apply correct routed_public_key
                    stf['routed_public_key'] = key_to_use
