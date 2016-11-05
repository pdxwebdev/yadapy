import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange

class Node(object):
    relationship = None
    shared_secret = None
    relations = None
    
    def __init__(self):
        if not self.relations:
            self.relations = []
        self.validate()
    
    def validate(self):
        assert isinstance(self.identity, Identity)
        assert isinstance(self.relationship_id, RelationshipIdentifier)
        assert isinstance(self.shared_secret, SharedSecret)

    def addRelation(self, relation):
        self.relations.append(relation)

    def getFriendTopLevelMeta(self, public_key):
        return self.getFriend(public_key)
    
    def getFriendPublicKeyList(self):
        return self.getFriendPublicKeysDict()
    
    def getIpAddressArray(self):
        return [x['address'] for x in self.get('data/identity/ip_address')] 
    
    def getFriend(self, public_key):
        for friend in self.get('data/friends'):
            if friend['public_key']==public_key:
                return friend
        return None
    
    def getFriends(self):
        return self.get('data/friends')
    
    def isMutual(self, node):
        #to determine if an external node is already your friend
    
        if isinstance(node, Node):
            node = node.get()
            
        directFriend = self.getFriend(node['public_key'])
        if directFriend:
            return directFriend
        
        tempNode = Node(copy.deepcopy(self.get()))
        
        tempNode.set('data/friends', self.getFriends(), True)
        
        friend1Keys = set(self.getRPandSIKeys(tempNode.get()))
        
        friend2Keys = set(self.getRPandSIKeys(node))
        
        intersection = friend1Keys & friend2Keys
        
        nodeFriendsIndexed = {}
        if intersection:
            for friend in self.getFriends():
                for stf in friend['data']['friends']:
                    if 'routed_public_key' in stf and stf['routed_public_key'] in intersection:
                        if not self.getFriend(stf['routed_public_key']):
                            return Node(friend)
                    elif 'source_indexer_key' in stf and stf['source_indexer_key'] in intersection:
                        if not self.getFriend(stf['source_indexer_key']):
                            return Node(friend)
        else:
            return False
    
    
    def getRPandSIKeys(self, friend):
        keys = []
        for fr in friend['data']['friends']:
            if 'routed_public_key' in fr:
                keys.append(fr['routed_public_key'])
            if 'source_indexer_key' in fr:
                keys.append(fr['source_indexer_key'])
        return keys
    
    def addFriend(self, friend):
        """
        adds a friend to the data/friends element. also validates the friend is a valid identity
        
        returns void
        """
        try:
            node = Node(friend)
            self.setModifiedToNow()
            self.add('data/friends', friend)
            self.save()
        except:
            raise InvalidIdentity("cannot add friend, invalid node")
            
    def addFriendRequest(self, friendRequest):
        """
        adds a friend to the friend_requests element. also validates the friend request is a valid identity
        
        returns void
        """
        try:
            node = Node(friendRequest)
            if not self.matchFriend(node):
                self.setModifiedToNow()
                self.add('friend_requests', friendRequest, True)
                self.save()
        except:
            raise InvalidIdentity("cannot add friend, invalid node")

    def addMessage(self, message):
        """
        adds a friend to the data/messages element.
        
        returns void
        """
        try:
            self.setModifiedToNow()
            self.add('data/messages', message)
            self.save()
        except:
            raise InvalidIdentity("cannot add friend, invalid node")
            
    def updateFromNode(self, inboundNode, impersonate=False):
        """
        inboundNode is an Node instance of a friend of self and used to update the information
        for that friend in your friends list.
        
        returns void
        """
        node = Node(inboundNode)
        selfBaseNode = Node(self.get())
        friend = selfBaseNode.getFriend(node.get('public_key'))
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
                    friend._data['data'] = node.get('data')
                    if "web_token" in node.get():
                        friend.set('web_token', node.get('web_token'))
                    tempList = []
                    for x in friend._data['data']['friends']:
                        if 'immutable' in x and x['immutable'] == 'true':
                            tempDict = x
                            tempList.append(tempDict)
                            continue
                        tempDict = {} 
                        tempDict['public_key'] = x['public_key']
                        if 'data' in x:
                            if 'identity' in x['data']:
                                if 'name' in x['data']['identity']:
                                    tempDict['data'] = {}
                                    tempDict['data']['identity'] = {}
                                    tempDict['data']['identity']['name'] = x['data']['identity']['name']
                                    tempDict['data']['identity']['ip_address'] = x['data']['identity']['ip_address']
                                    if 'avatar' in x['data']['identity']:
                                        tempDict['data']['identity']['avatar'] = x['data']['identity']['avatar']
                        tempList.append(tempDict)
                    friend._data['data']['friends'] = tempList
                    friend._data['modified'] = node._data['modified']
                    self.save()
                else:
                    pass
        elif self.get('public_key') == node.get('public_key'):
            self.sync(node.get())
            self.save()

    def matchFriend(self, node):
        intersection = set(self.getFriendPublicKeysArray()) & set(node.getFriendPublicKeysArray())
        if len(intersection) == 1:
            friend = self.getFriend(list(intersection)[0])
            return friend
        else:
            return None

    def getRoutedPublicKeysAndSourceIndexerKeys(self):
        keys = []
        if 'data' in self.get():
            for fr in self.get('data/friends'):
                if 'routed_public_key' in fr:
                    keys.append(fr['routed_public_key'])
                if 'source_indexer_key' in fr:
                    keys.append(fr['source_indexer_key'])
        return keys
        
    def getFriendPublicKeysArray(self):
        return [x['public_key'] for x in self.get('data/friends')]
    
    def getFriendPublicKeysDict(self):
        return [{'public_key' : x['public_key']} for x in self.get('data/friends')]
    
    def setModifiedToNow(self):
        self.set('modified', self.newTimeStamp(), force=True)
                
    def stripIdentityAndFriendsForProtocolV1(self, node=None):
        self.replaceIdentityOfFriendsWithPubKeys(node)
        if node:
            self.stripIdentityOfIrrelevantMessages(node)
            self.stripIdentityOfIrrelevantFriendRequests(node)
                    
    def stripIdentityAndFriendsForWebGUI(self):
        if 'data' in self.get():
            self.stripIdentityOfFriendRequests()
            self.base64DecodeMessages()
            if 'friends' in self.get('data'):
                for i, friend in enumerate(self.get('data/friends')):
                    self.stripFriendIdentityForFriend(friend)
                    
    def stripIdentityAndFriendsForFriend(self):
        self.stripFriendIdentityForFriend()
        for friend in self.get('data/friends'):
            self.stripFriendIdentityForFriend(friend)
    
    def stripFriendIdentityForFriend(self, friend={}):
        if not friend:
            friend = self.get()
        if 'data' in friend:
            self.stripIdentityOfIrrelevantMessages(friend)
            self.replaceIdentityOfFriendsWithPubKeys(friend)
            self.stripIdentityOfIrrelevantFriendRequests(friend)
            self.base64DecodeMessages(friend)
        
    def stripIdentityOfIrrelevantMessages(self, friend):
        messageList = []
        for x, message in enumerate(self.get('data/messages')):
            if friend.get('public_key') in message['public_key']:
                messageList.append(message)
        self.set('data/messages', messageList)

    def stripNodeForQr(self):
        if 'messages' in self._data['data']:
            self._data['data']['messages'] = []
        
        if 'status' in self._data['data']:
            self._data['data']['status'] = []
        
        if 'friends' in self._data['data']:
            self._data['data']['friends'] = []
        
        if 'routed_friend_requests' in self._data['data']:
            del self._data['data']['routed_friend_requests']
            
        if 'routed_messages' in self._data['data']:
            del self._data['data']['routed_messages']
            
        if 'birth_date' in self._data['data']['identity']:
            del self._data['data']['identity']['birth_date']
            
        if 'location' in self._data['data']['identity']:
            del self._data['data']['identity']['location']
        
        if 'label' in self._data['data']['identity']:
            del self._data['data']['identity']['label']
            
        if 'friend_requests' in self._data:
            del self._data['friend_requests']
        
        if '_id' in self._data:
            del self._data['_id']
        
    def replaceIdentityOfFriendsWithPubKeys(self, node = None):
        tempList = []
        for i, friend in enumerate(self.get('data/friends')):
            if 'immutable' in friend and friend['immutable'] == 'true':
                tempDict = friend
                tempList.append(tempDict)
                continue
            tempDict = {} 
            tempDict['public_key'] = friend['public_key']
            
            if friend.get('source_indexer_key', None):
                tempDict['source_indexer_key'] = friend['source_indexer_key']
            
            if friend.get('routed_public_key', None):
                tempDict['routed_public_key'] = friend['routed_public_key']
                
            if 'data' in friend:
                if 'identity' in friend['data']:
                    if 'name' in friend['data']['identity']:
                        try:
                            tempDict['data'] = {}
                            tempDict['data']['identity'] = {}
                            tempDict['data']['identity']['name'] = friend['data']['identity']['name']
                            tempDict['data']['identity']['ip_address'] = friend['data']['identity']['ip_address']
                            if 'status' in friend['data']:
                                tempDict['data']['status'] = friend['data']['status']
                            if 'avatar' in friend['data']['identity']:
                                tempDict['data']['identity']['avatar'] = friend['data']['identity']['avatar']
                            
                            try:
                                if node and node.get('public_key') == friend['public_key']:
                                    tempDict = friend
                            except:
                                pass
                        except:
                            continue
            tempList.append(tempDict)
        self._data['data']['friends'] = tempList
                
    def replaceIdentityOfFriendsWithPubKeysKeepPrivateKeys(self):
        for i, friend in enumerate(self.get('data/friends')):
            self._data['data']['friends'][i] = {'public_key' : friend['public_key'],'private_key' : friend['private_key']}
                
    def stripIdentityOfIrrelevantFriendRequests(self, node):
        newFriendRequestList = []
        if 'routed_friend_requests' in self.get()['data']:
            for request in self.get('data/routed_friend_requests'):
                if request['routed_public_key'] == node.get('public_key'):
                    newFriendRequestList.append(request)
            self.set('data/routed_friend_requests', newFriendRequestList)

    def preventInfiniteNesting(self, newFriendNode):
        node = Node(newFriendNode)
        selfInFriend = self.getSelfInFriend(node)
        if selfInFriend:
            selfInFriend['data'] = {}
        
    def getSelfInFriend(self, node):
        #DELTE MYSELF FROM FRIEND TO AVOID ENDLESS LOOP
        i=0
        friend = node.getFriend(node.get('public_key'))
        if friend and 'data' in friend and 'friends' in friend['data']:
            for f in friend['data']['friends']:
                if f['public_key'] == friend['public_key']:
                    return f

    def base64DecodeMessages(self):
        for index, message in enumerate(self.get('data/messages')):
            if 'message' in message:
                try:
                    b64decode(message['message']).decode('utf-8')
                    message['message'] = b64decode(message['message'])
                except:
                    pass
        for friend in self.get('data/friends'):
            try:
                friendNode = Node(friend)
                for index, message in enumerate(friendNode.get('data/messages')):
                    if 'message' in message:
                        try:
                            b64decode(message['message']).decode('utf-8')
                            message['message'] = b64decode(message['message'])
                        except:
                            pass
            except:
                pass
                    
    def base64EncodeMessages(self):
        for index, message in enumerate(self.get('data/messages')):
            if 'message' in message:
                try:
                    b64encode(message['message']).decode('utf-8')
                    message['message'] = b64encode(message['message'])
                except:
                    pass

    def newUuid(self):
        return unicode(uuid4())
    
    def newTimeStamp(self):
        return time.time()
    
    def handlePromotionRequest(self, packet):
        return self.addPromotionRequest(packet)
    
    def handleRoutedFriendRequest(self, packet):
        return self.addRoutedFriendRequest(packet)
    
    def handleRoutedMessage(self, packet):
        pass
    
    def handleFriendRequest(self, packet):
        self.addFriendRequest(packet)
        
    def addPromotionRequest(self, packet):
        node = Node(packet)
        self.add('promotion_requests', node.get(), True)
        self.save()
        
    def addRoutedFriendRequest(self, packet):
        node = Node(packet)
        self.add('data/routed_friend_requests', node.get(), True)
        self.save()
        
    def respondWithRelationship(self, friendNode):
        """
        This method will return a dictionary prepared to be encrypted, encoded and sent
        
        @friendNode Node instance This is used for the public and private key information
        
        returns dictionary
        """
        #TODO: apply permissions to dictionary for this relationship
        friendNode.get().update({"data" : copy.deepcopy(self.get('data'))})
        friendNode.preventInfiniteNesting(friendNode.get())
        friendNode.stripIdentityAndFriendsForProtocolV1(friendNode)
        friendNode.setModifiedToNow()
        return friendNode.get()
    
    
    def sendMessage(self, pub_keys, subject, message, thread_id=None, guid=None):
        """Creates either a new message thread or replies to an existing thread if @thread_id is given.
        
        :param pub_keys: list A list of public_keys to send to
        :type pub_keys: list
        
        :subject string Just like an email subject
        :message string The body of the message, just like email
        :thread_id string The thread_id to allow aggregation of a topic
        
        returns a new message object that can be inserted into data/messages
        """
        if not thread_id:
            thread_id = str(uuid4())
            
        if not guid:
            guid = str(uuid4())
                       
        return {'public_key':pub_keys, 'timestamp':self.newTimeStamp(),'thread_id':thread_id,'subject':subject,'message':b64encode(message),'guid':guid} 

    def sync(self, inbound, is_self=True, permission_object={}, array_update = True):
        """
        This kicks off the _updateTree method which will synchronize the two identity objects
        @inbound dictionary Is the object to synchronize against
        @is_self bool This is necessary because a friend has the ability to impersonate you.
        @permission_object dictionary This object should match the index structure of
        
        returns void
        """
        if 'friends' not in self.get('data'):
            self._data['data']['friends'] = []
        self._updateTree(self.get(), inbound, is_self, permission_object, array_update)

    def syncStfStatuses(self, inbound):
        #this is suppose to be run from a first tier Node friend.
        if 'friends' in self.get('data') and 'friends' in inbound['data']:
            stfIndexed = {}
            
            for stf in inbound['data']['friends']:
                stfIndexed[stf['public_key']] = stf
                
            for internalStf in self.get('data/friends'):
                try: #adding try because inbound may have less public_keys than internal
                    inboundStf = stfIndexed[internalStf['public_key']] #if the public key isn't here, we have a problem with the previous sync step which should have added all friends from inbound. giving it all public keys
                    if 'status' in internalStf['data'] and 'status' in inboundStf['data']:
                        internalStfSharesIndex = {}
                        for internalStfShare in internalStf['data']['status']:
                            internalStfSharesIndex[internalStfShare['share_id']] = internalStfShare
                            
                        for inboundStfShare in inboundStf['data']['status']:
                            if inboundStfShare['share_id'] not in internalStfSharesIndex:
                                internalStf['data']['status'].append(inboundStfShare)
                except Exception as e:
                    pass
                    
    def updateStatus(self, jsonData, arrayKey, elementKey, newOrUpdate, obj={}):
        """
        This method will attempt to update your status automatically based on activity
        during the sync process.
        
        returns void        
        """
        lookup={}
        if arrayKey=='status': return
        if 'status' not in jsonData: return
        for item in jsonData['status']:
            if type(item['content'])== type({}):
                lookup[(item['content']['ref_id'],item['content']['type'])] = item
        if (elementKey,arrayKey) in lookup: return
        
        content = {'type': arrayKey,'ref_id':elementKey,'newOrUpdate':newOrUpdate}
        if type(obj) == type({}) and 'data' in obj and 'identity' in obj['data']:
            content['name'] = obj['data']['identity']['name']
            if 'avatar' in obj['data']['identity']:
                content['avatar'] = obj['data']['identity']['avatar']
            else:
                content['avatar'] = ''
            
        jsonData['status'].append({
            'timestamp': self.newTimeStamp(),
            'share_id': str(uuid4()),
            'content': content
        })
        return
    
    @staticmethod
    def updatePair(key,internal,internalRef,inbound,inboundRef):
        """
        This function will handle assigning a value to a key in a list or dictionary
        while in the updateTree method.
        
        returns void
        """
        if float(internal['modified'])<float(inbound['modified']):
            if key != 'modified':
                print 'update made to dict %s to %s' %(internal[key],inboundRef)
                logging.debug('update made to dict %s to %s' %(internal[key],inboundRef))
                internal[key] = inboundRef
                
    def searchForNode(self, searchNode):
        """
        tries to find the relationship of self with the friend of your friend.
        Because even though you have the mutual friend node gotten from your friend's friend list,
        that node will not have the correct public key.
        So we need to return the corresponding friend in your list
        
        returns none or Node instance
        """
        for node in self.get('data/friends'):
            try:
                node = Node(node)
            except:
                break
            if set(node.getFriendPublicKeysArray()) & set(searchNode.getFriendPublicKeysArray()):
                return node
        return None
    
    def createIPAddress(self, host, port='80', protocol='4'):
        """
        generates a new IP Address object
        @host string Can be an IP address or a host name.
        @port string Can be any string port number
        @protocol is the version of IP being used. 4 or 6
        
        returns dictionary
        """
        if ":" in host:
            parts = host.split(':')
            host = parts[0]
            port = parts[1]
        
        return {
            "protocol_version" : protocol,
            "guid" : self.newUuid(),
            "modified" : self.newTimeStamp(),
            "address" : host,
            "timestamp" : self.newTimeStamp(),
            "port" : port,
            "path" : "/"
        }
        
    def addIPAddress(self, host, port='80', protocol='4'):
        """
        Adds an IP address object to the data/identity/ip_address element.
        This object is used by your friends to contact you.
        
        returns void
        """
        self.add('data/identity/ip_address', self.createIPAddress(host, port, protocol))
        
    def getClassInstanceFromNodeForNode(self, identity):
        
        m = self.getClassInstanceFromNode()
        
        if not hasattr(self, 'kwargs'):
            self.kwargs = {}
        
        if 'friends' not in identity['data']:
            identity['data']['friends'] = []
        
        if 'messages' not in identity['data']:
            identity['data']['messages'] = []
            
        self.kwargs['identityData'] = identity
            
        try:
            node = m.manager.YadaServer(**self.kwargs)
        except:
            node = m.node.Node(**self.kwargs)
        
        return node
    
    def my_import(self, name):
        m = __import__(name)
        for n in name.split(".")[1:]:
            m = getattr(m, n)
        return m
    
    def getClassInstanceFromNode(self):
        module = self.__module__
        module = module.split(".")
        module = ".".join(module[:-1])
        return self.my_import(module)
        
    def save(self):
        """
        This is a place holder method to indicate that subclasses with persistent storage 
        should override this method
        
        returns void
        """
        self.setModifiedToNow()
        for friend in self.get('data/friends'):
            Node(friend).stripIdentityAndFriendsForProtocolV1()


class RelationshipIdentifier(object):
    relationship_id = None

    def validate():

        try:
            val = UUID(self.relationship_id, version=4)
        except ValueError:
            raise Exception('Invalid UUID Version 4')

        if val.hex != self.relationship_id:
            raise Exception('Invalid UUID Version 4')


class NewRelationshipIdentifier(RelationshipIdentifier):

    def __init__(self):
        self.relationship_id = str(uuid4())


class ExistingRelationshipIdentifier(RelationshipIdentifier):

    def __init__(self, relationship_id):
        self.relationship_id = relationship_id
        self.validate()


class SharedSecret(object):
    shared_secret = None

    def valid_uuid4(uuid_string):

        try:
            val = UUID(uuid_string, version=4)
        except ValueError:
            raise Exception('Invalid UUID Version 4')

        if val.hex != uuid_string:
            raise Exception('Invalid UUID Version 4')


class NewSharedSecret(SharedSecret):

    def __init__(self):
        self.shared_secret = str(uuid4())


class ExistingSharedSecret(SharedSecret):

    def __init__(self, shared_secret):
        self.valid_uuid4(shared_secret)
        self.shared_secret = shared_secret
            

class Identity(object):
    name = None
    avatar = None

    def __init__(self, name, avatar):
        self.name = name
        self.avatar = avatar
        self.validate()

    def validate(self):
        if type(self.name) != type('') or type(self.avatar) != type(''):
            raise Exception("invalid identity params")

class NewNode(Node):
    def __init__(self, identity):
        self.shared_secret = NewSharedSecret()
        self.relationship_id = NewRelationshipIdentifier()
        self.identity = identity
        super(NewNode, self).__init__()


class ExistingNode(Node):
    def __init__(self, shared_secret, relationship_id, identity):
        self.shared_secret = shared_secret
        self.relationship_id = relationship_id
        self.identity = identity
        super(ExistingNode, self).__init__()


class Relation(Node):
    pass


class NewRelation(Relation):
    def __init__(self, node):
        self.shared_secret = NewSharedSecret()
        self.relationship_id = NewRelationshipIdentifier()
        self.identity = node.identity
        super(NewRelation, self).__init__()


class ExistingRelation(Relation):
    def __init__(self, relationship_id, shared_secret, identity):
        self.relationship_id = relationship_id
        self.shared_secret = shared_secret
        self.identity = identity
        super(ExistingRelation, self).__init__()


class Relationship(Node):
    """
    meta class
    """
    source_node = None
    dest_node = None

    def validate(self):
        assert isinstance(self.relationship_id, RelationshipIdentifier)
        assert isinstance(self.shared_secret, SharedSecret)


class NewRelationship(Relationship):
    
    def __init__(self, source_relation, dest_relation):
        self.source_node = source_relation
        self.dest_node = dest_relation
        self.relationship_id = NewRelationshipIdentifier()
        self.shared_secret = NewSharedSecret()
        super(NewRelationship, self).__init__()


class ExistingRelationship(Relationship):

    def __init__(self, source_relation, dest_relation, relationship_id, shared_secret):
        self.source_node = source_relation
        self.dest_node = dest_relation
        self.relationship_id = relationship_id
        self.shared_secret = shared_secret
        super(ExistingRelationship, self).__init__(source_relation, dest_relation)

