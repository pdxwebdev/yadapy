import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange

class Node(object):
    _data = {} # Where the actual identity dictionary data is stored.
    _db = {}
    identityData = {}
    _initialFriends = []
    
    def __init__(self, *args, **kwargs):
        super(Node, self).__init__()
        
        self.args = args
        self.kwargs = kwargs
        
        if 'identityData' in kwargs:
            identityData = kwargs['identityData']
        else:
            identityData = args[0]
            
        try:
            newIdentity = ''
            newIdentity = args[1]
        except:
            if kwargs.get('newIdentity', None):
                newIdentity = kwargs.get('newIdentity', None)
            
        if len(args)>2:
            self._initialFriends = args[2]
        elif 'initialFriends' in kwargs:
            self._initialFriends = kwargs.get('initialFriends', None)
        else:
            self._initialFriends = []
            
        self.identityData = copy.deepcopy({
          "name" : "",
          "avatar": "",
          "modified" : self.newTimeStamp(),
          "label" : "default",
          "location" : [
            {
              "physical_address" : {
                "city" : "",
                "state" : "",
                "address" : "",
                "unit" : "",
                "country" : ""
              },
              "web_address" : [
                {
                  "url" : "",
                  "label" : "home"
                }
              ],
              "label" : "Default",
              "phone" : [
                {
                  "prefix" : "",
                  "area_code" : "",
                  "number" : "",
                  "country_code" : "",
                  "label" : "home"
                }
              ],
              "guid" : self.newUuid(),
              "email" : [
                {
                  "username" : "",
                  "domain" : "",
                  "label" : "home"
                }
              ]
            }
          ],
          "birth_date" : {
            "label" : "default",
            "year" : "",
            "day" : "",
            "modified" : self.newTimeStamp(),
            "month" : ""
          },
          "ip_address" : []
        })
        if identityData:
            self.setData(identityData)
        elif newIdentity:
            self.setData(self.newIdentity(newIdentity))
        else:
            raise InvalidIdentity("An identity cannot be created. No identity data provided. Try ({}, {'name': 'my name'})")
        
    def get(self, path=""):
        """
        Takes a key path separated by forward slashes / to find an entity of the identity
        
        Example:
        id.get("data/friends") #would return the friends list
        
        """
        if path == "":
            return self._data
        try:
            splitPath = filter(None, path.split('/'))
            entity = {}
            entity = self._data
            num = len(splitPath) - 1
            for idx, el in enumerate(splitPath):
                if type(entity) == type([]):
                    el = int(el)
                entity = entity[el]
            return entity
        except KeyError:
            logging.debug("Path '%s' is invalid for this identity" % path)
            raise
        except:
            raise
    
    def set(self, path="", assignment="", create=False, force=False):
        """
        Takes a key path separated by forward slashes / to find an entity of the identity
        Second parameter is the value or expression being assigned
        
        Example:
        id.set("data/identity/name","Matt") #would return the friends list
        
        """
        if path == "":
            return self._data
        try:
            splitPath = filter(None, path.split('/'))
            entity = {}
            entity = self._data
            num = len(splitPath) - 1
            for idx, el in enumerate(splitPath):
                if type(entity) == type([]):
                    el = int(el)
                if idx < num:
                    entity = entity[el]
                else:
                    if not el in entity and create == True:
                        entity[el] = assignment
                        if type(entity) == type([]):
                            entity[el]['timestamp'] = self.newTimeStamp()
                            entity[el]['modified'] = self.newTimeStamp()
                        else:
                            entity['timestamp'] = self.newTimeStamp()
                            entity['modified'] = self.newTimeStamp()
                    elif type(entity[el]) == type(assignment) or force == True:
                        entity[el] = assignment
                        entity['modified'] = self.newTimeStamp()
                    else:
                        raise InvalidIdentity("Type mismatch when setting element for '%s' key" % path)
        except KeyError:
            raise
        except InvalidIdentity:
            raise
        except:
            raise

    def add(self, path="", assignment="", create=False):
        """
        @path string Takes a key path separated by forward slashes / to find an entity of the identity
        Second parameter is the value or expression being assigned
        
        Example:
        id.add("data/messages",[{..message object..}]) #would append a message 
                                                       #to the messages list
        
        """
        try:
            array = self.get(path)
        except KeyError:
            if create == True:
                array = []
            else:
                raise
        except:
            raise
        
        if type([]) == type(array):
            if type(assignment) == type([]):
                array.extend(assignment)
            else:
                array.append(assignment)
            
        self.set(path, array, create)
        self.setModifiedToNow()

    def delKey(self, path="", assignment=""):
        """
        Takes a key path separated by forward slashes / to find an entity of the identity
        Second parameter is the value or expression being assigned
        
        Example:
        id.add("status") #would delete the status key
        
        """
        if path == "":
            return self._data
        try:
            splitPath = filter(None, path.split('/'))
            entity = {}
            entity = self._data
            num = len(splitPath) - 1
            for idx, el in enumerate(splitPath):
                if idx < num:
                    entity = entity[el]
                else:
                    if el in entity:
                        del entity[el]
                    else:
                        raise InvalidIdentity("Invalid path encountered with deleting key %" % el)
        except KeyError:
            raise
        except InvalidIdentity:
            raise
        except:
            raise

    def newIdentity(self, identity):
        self.identityData.update(identity)
        return copy.deepcopy({
            'public_key':self.newUuid(), 
            'private_key':self.newUuid(),
            'modified': self.newTimeStamp(),
            'friend_requests': [],
            'data':{
                "routed_friend_requests" : [],
                "routed_messages" : [],
                "messages" : [],
                "friends" : self._initialFriends,
                "status" : [],
                "identity" : self.identityData
            }
        })
    
    def getData(self, path=""):
        return self.get(path)
    
    def setData(self, data):
        if self.validIdentity(data):
            self._data = data
            
    def validIdentity(self, data):
        try:
            if 'public_key' in data \
            and 'private_key' in data \
            and 'modified' in data \
            and 'data' in data \
            and 'friends' in data['data'] \
            and 'identity' in data['data'] \
            and 'messages' in data['data'] \
            and 'name' in data['data']['identity']:
                return True
            else:
                raise InvalidIdentity("invalid identity dictionary for identity")
        except InvalidIdentity:
            raise
        
    def dedupIP(self):
        addresses = self.get('data/identity/ip_address')
        newList = {}
        for index, item in enumerate(addresses):
            if 'guid' not in item:
                item['guid'] = str(uuid4())
            if 'modified' not in item:
                item['modified'] = int(time.time())
            if 'protocol_version' not in item:
                item['protocol_version'] = '4'
            if 'address' not in item:
                continue
            if item['address'] == '':
                continue
            newList[item['guid']] = item
        self.get('data/identity/ip_address', [item for index, item in newList.items()])

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
        
    def replaceIdentityOfFriendsWithPubKeys(self, node = None):
        tempList = []
        for i, friend in enumerate(self.get('data/friends')):
            
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

    def sync(self, inbound, is_self=True, permission_object={}):
        """
        This kicks off the _updateTree method which will synchronize the two identity objects
        @inbound dictionary Is the object to synchronize against
        @is_self bool This is necessary because a friend has the ability to impersonate you.
        @permission_object dictionary This object should match the index structure of
        
        returns void
        """
        if 'friends' not in self.get('data'):
            self._data['data']['friends'] = []
        self._updateTree(self.get(), inbound, is_self, permission_object)
        

    def _updateTree(self, internal, inbound, is_self=True, permission_object={}):
        if not internal or not inbound: return
        if type(inbound) == type({}):
            if 'modified' not in internal or 'modified' not in inbound:
                #CRUD: UPDATE
                if not is_self:
                    if 'U' in permission_object:
                        internal['modified'] = int(time.time())
                        inbound['modified'] = int(time.time())
                else:
                    internal['modified'] = int(time.time())
                    inbound['modified'] = int(time.time())
            if 'label' not in internal or 'label' not in inbound:
                #CRUD: UPDATE
                if not is_self:
                    if 'U' in permission_object:
                        internal['label'] = 'default'
                        inbound['label'] = 'default'
                else:
                    internal['label'] = 'default'
                    inbound['label'] = 'default'
                    
            for key, inboundRef in inbound.items():
                if not is_self:
                    if key not in permission_object:
                        permission_object_ref = permission_object
                    else:
                        permission_object_ref = permission_object[key]
                else:
                    permission_object_ref = permission_object
                try:
                    internalRef = internal[key]
                except:
                    #CRUD: UPDATE
                    if not is_self:
                        if 'U' in permission_object_ref:
                            internal[key] = inboundRef
                    else:
                        internal[key] = inboundRef
                    continue
                if type(inboundRef) == type({}):
                    self._updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                    if type(inboundRef) == type({}):
                        curTime = int(time.time())
                        inboundRef['modified'] = curTime
                elif type(inboundRef) == type([]):
                    if key == 'messages':
                        pass
                    key_name = ''
                    internalRef_indexed={} 
                    newList=[]
                    newList_indexed={}
                    key_dict={
                              'status':'share_id',
                              'messages':'guid',
                              'friends':'public_key'
                    }
                    if key in key_dict:
                        key_name = key_dict[key]
                    else:
                        key_name = 'guid'
                        self._updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                    if key_name != '':
                        for index, item in enumerate(internalRef):
                            try:
                                internalRef_indexed[(item[key_name],)] = item
                            except:
                                internalRef[index][key_name] = str(uuid4())
                                internalRef_indexed[(internalRef[index][key_name],)] = item
                                logging.warning("object could not be referenced with the key '%s'. Assigning a new one." %key_name)
                        for item in inboundRef:
                            if key_name not in item:
                                continue
                            if (item[key_name],) in internalRef_indexed:
                                if 'modified' not in internalRef_indexed[(item[key_name],)] and 'modified' in item: 
                                    newList.append(item)
                                    self.updateStatus(internal,key,item[key_name],"update")
                                    continue
                                if 'modified' not in item and 'modified' in internalRef_indexed[(item[key_name],)]: 
                                    newList.append(internalRef_indexed[(item[key_name],)])
                                    continue
                                if 'modified' not in item and 'modified' not in internalRef_indexed[(item[key_name],)]:
                                    internalRef_indexed[(item[key_name],)]['modified'] = self.newTimeStamp()
                                    item['modified'] = 0
                                try:
                                    timeType = 'modified' if 'modified' in internalRef_indexed[(item[key_name],)] and 'modified' in item else 'timestamp'
                                    if float(internalRef_indexed[(item[key_name],)][timeType]) < float(item[timeType]):
                                        #CRUD: UPDATE
                                        if not is_self:
                                            if 'U' in permission_object_ref:
                                                newList.append(item)
                                                self.updateStatus(internal,key,item[key_name],"update", item)
                                        else:
                                            newList.append(item)
                                            self.updateStatus(internal,key,item[key_name],"update", item)
                                    else:
                                        newList.append(internalRef_indexed[(item[key_name],)])
                                except:
                                    raise
                            else:
                                #CRUD: CREATE
                                if not is_self:
                                    if 'C' in permission_object_ref:
                                        newList.append(item)
                                        if key == 'messages':
                                            self.addMessage(item)
                                        elif key == 'friends':
                                            self.addFriend(item)
                                        if not key_name=='guid':
                                            self.updateStatus(internal,key,item[key_name], "new", item)
                                else:
                                    newList.append(item)
                                    if key == 'messages':
                                        self.addMessage(item)
                                    elif key == 'friends':
                                        self.addFriend(item)
                                    if not key_name=='guid':
                                        self.updateStatus(internal,key,item[key_name], "new", item)
                        for item in newList:
                            newList_indexed[(item[key_name],)] = item
                        for item in internalRef:
                            if (item[key_name],) not in newList_indexed:
                                newList.append(item)
                        internal[key]=newList
                    else:
                        self._updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                        if type(inboundRef) == type({}):
                            curTime = int(time.time())
                            #CRUD: UPDATE
                            if not is_self:
                                if 'U' in permission_object_ref:
                                    inboundRef['modified'] = curTime
                            else:
                                inboundRef['modified'] = curTime
                else:
                    
                    if 'modified' not in inbound:
                        continue
                    if 'modified' not in internal:
                        #CRUD: UPDATE
                        if not is_self:
                            if 'U' in permission_object_ref:
                                internal[key] = inboundRef
                                continue
                        else:
                            internal[key] = inboundRef
                            continue
                    try:
                        #CRUD: UPDATE
                        if not is_self:
                            if 'U' in permission_object_ref:
                                Node.updatePair(key,internal,internalRef,inbound,inboundRef)
                        else:
                            Node.updatePair(key,internal,internalRef,inbound,inboundRef)
                    except:
                        raise
            try:
                if float(internal['modified'])<float(inbound['modified']):
                    print 'update made to dict %s to %s' %(internal['modified'],inbound['modified'])
                    logging.debug('update made to dict %s to %s' %(internal['modified'],inbound['modified']))
                    #CRUD: UPDATE
                    if not is_self:
                        if 'U' in permission_object_ref:
                            internal['modified'] = inbound['modified']
                    else:
                        internal['modified'] = inbound['modified']
            except:
                pass
        if type(inbound) == type([]):
            i=0
            for key, inboundRef in enumerate(inbound):
                if not is_self:
                    if key not in permission_object:
                        permission_object_ref = permission_object
                else:
                    permission_object_ref = permission_object
                try:
                    internalRef = internal[i]
                except:
                    #CRUD: CREATE
                    if not is_self:
                        if 'C' in permission_object_ref:
                            internal.append(inboundRef)
                            continue
                    else:
                        internal.append(inboundRef)
                        continue
                curTime = int(time.time())
                if type(inboundRef) == type({}):
                    self._updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                    if type(inboundRef) == type({}):
                        inboundRef['modified'] = curTime
                        if 'label' not in inboundRef:
                            inboundRef['label'] = 'default'
                elif type(inboundRef) == type([]):
                    self._updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                    if type(inboundRef) == type({}):
                        inboundRef['modified'] = curTime
                        if 'label' not in inboundRef:
                            inboundRef['label'] = 'default'
                else:
                    
                    if 'modified' not in internal:
                        #CRUD: UPDATE
                        if not is_self:
                            if 'U' in permission_object_ref:
                                internal[i] = inboundRef
                                continue
                        else:
                            internal[i] = inboundRef
                            continue
                    try:
                        if int(internal['modified'])<int(inbound['modified']):
                            print 'update made to list'
                            logging.debug('update made to list')
                            #CRUD: UPDATE
                            if not is_self:
                                if 'U' in permission_object_ref:
                                    internal[i] = inboundRef
                            else:
                                internal[i] = inboundRef
                    except:
                        raise
                i=i+1

    def syncStfStatuses(self, inbound):
        #this is suppose to be run from a first tier Node friend.
        if 'friends' in self.get('data') and 'friends' in inbound['data']:
            stfIndexed = {}
            
            for stf in inbound['data']['friends']:
                stfIndexed[stf['public_key']] = stf
                
            for internalStf in self.get('data/friends'):
                inboundStf = stfIndexed[internalStf['public_key']] #if the public key isn't here, we have a problem with the previous sync step which should have added all friends from inbound. giving it all public keys
                if 'status' in internalStf['data'] and 'status' in inboundStf['data']:
                    internalStfSharesIndex = {}
                    for internalStfShare in internalStf['data']['status']:
                        internalStfSharesIndex[internalStfShare['share_id']] = internalStfShare
                        
                    for inboundStfShare in inboundStf['data']['status']:
                        if inboundStfShare['share_id'] not in internalStfSharesIndex:
                            internalStf['data']['status'].append(inboundStfShare)
                    
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
            content['avatar'] = obj['data']['identity']['avatar']
            
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

class InvalidIdentity(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
