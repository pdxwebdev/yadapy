import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from uuid import uuid4
from random import randrange

class Node(object):
    _data = {} # Where the actual identity dictionary data is stored.
    _db = {}
    identityData = {}
    _initialFriends = []
    
    def __init__(*args, **kwargs):
        super(Node, args[0]).__init__()
        
        self = args[0]
        
        self.defaultHost = "staging.yadaproject.com"
        self.defaultPort = "8089"
        
        if len(args)<=1:
            identityData = kwargs.get('identityData', None)
        else:
            identityData = args[1]
            
        if len(args)<=2:
            newIdentity = kwargs.get('newIdentity', None)
        else:
            newIdentity = args[2]
            
        if len(args)>3:
            args[0]._initialFriends = args[3]
        elif 'initialFriends' in kwargs:
            args[0]._initialFriends = kwargs.get('initialFriends', None)
        else:
            args[0]._initialFriends = []
            
        args[0].identityData = copy.deepcopy({
          "name" : "",
          "modified" : args[0].newTimeStamp(),
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
              "guid" : args[0].newUuid(),
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
            "modified" : args[0].newTimeStamp(),
            "month" : ""
          },
          "ip_address" : []
        })
        if identityData:
            args[0].setData(identityData)
        elif newIdentity:
            args[0].setData(args[0].newIdentity(newIdentity))
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
                entity = entity[el]
            return entity
        except KeyError:
            logging.critical("Path '%s' is invalid for this identity" % path)
            raise
        except:
            raise
    
    def set(self, path="", assignment="", create=False):
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
                if idx < num:
                    entity = entity[el]
                else:
                    if not el in entity and create == True:
                        entity[el] = assignment
                        entity['timestamp'] = self.newTimeStamp()
                        entity['modified'] = self.newTimeStamp()
                    elif type(entity[el]) == type(assignment):
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
        Takes a key path separated by forward slashes / to find an entity of the identity
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
    
    def addFriend(self, friend):
        try:
            node = Node(friend)
            self.setModifiedToNow()
            self.add('data/friends', friend)
        except:
            InvalidIdentity("cannot add friend, invalid node")
            
    def addFriendRequest(self, friendRequest):
        try:
            node = Node(friendRequest)
            self.setModifiedToNow()
            self.add('friend_requests', friendRequest)
        except:
            InvalidIdentity("cannot add friend, invalid node")

    def addMessage(self, message):
        try:
            self.setModifiedToNow()
            self.add('data/messages', message)
        except:
            InvalidIdentity("cannot add friend, invalid node")
            
    def updateFromNode(self, inboundNode):
        node = Node(inboundNode)
        friend = self.getFriend(node.get('public_key'))
        if friend:
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
                friend.set('data', node.get('data'))
                if "web_token" in node.get():
                    friend.set('web_token', node.get('web_token'))
                self.save()
            else:
                pass
        elif self.get('public_key') == node.get('public_key'):
            self.sync(node.get())
            self.save()

    def matchFriend(self, node):
        intersection = set(self.getFriendPublicKeysArray()) & set(node.getFriendPublicKeysArray())
        if intersection:
            friend = self.getFriend(list(intersection)[0])
            return friend
        else:
            return None
    
    def addRoutedFriendRequest(self):
        pass

    def getFriendPublicKeysArray(self):
        return [x['public_key'] for x in self.get('data/friends')]
    
    def getFriendPublicKeysDict(self):
        return [{'public_key' : x['public_key']} for x in self.get('data/friends')]
    
    def setModifiedToNow(self):
        self.set('modified', self.newTimeStamp())
                
    def stripIdentityAndFriendsForProtocolV1(self, node):
        self.replaceIdentityOfFriendsWithPubKeys()
        self.stripIdentityOfIrrelevantFriendRequests(node)
                    
    def stripIdentityAndFriendsForWebGUI(self):
        if 'data' in identity:
            self.stripIdentityOfFriendRequests()
            self.base64DecodeMessages()
            if 'friends' in identity['data']:
                for i, friend in enumerate(self.get('data/friends')):
                    self.stripFriendIdentityForFriend(friend)
                    
    def stripIdentityAndFriendsForFriend(self):
        if 'data' in identity:
            self.stripFriendIdentityForFriend()
            if 'friends' in identity['data']:
                for i, friend in enumerate(self.get('data/friends')):
                    self.stripFriendIdentityForFriend(friend)
    
    def stripFriendIdentityForFriend(self, friend={}):
        if not friend:
            friend = self.get()
        if 'data' in friend:
            stripIdentityOfIrrelevantMessages(friend)
            replaceIdentityOfFriendsWithPubKeys(friend)
            stripIdentityOfFriendRequests(friend)
            base64DecodeMessages(friend)
        
    def stripIdentityOfIrrelevantMessages(self):
        messageList = []
        for x, message in enumerate(self.get('data/messages')):
            if self.get('public_key') in message['public_key']:
                messageList.append(message)
        self.set('data/messages', messageList)
        
    def replaceIdentityOfFriendsWithPubKeys(self):
        for i, friend in enumerate(self.get('data/friends')):
            self._data['data']['friends'][i] = {'public_key' : friend['public_key']}
                
    def replaceIdentityOfFriendsWithPubKeysKeepPrivateKeys(self):
        for i, friend in enumerate(self.get('data/friends')):
            self._data['data']['friends'][i] = {'public_key' : friend['public_key'],'private_key' : friend['private_key']}
                
    def stripIdentityOfIrrelevantFriendRequests(self, node):
        newFriendRequestList = []
        for request in self.get('data/routed_friend_requests'):
            if request['routed_public_key'] == node.get('public_key'):
                newFriendRequestList.append(request)
        self.set('data/routed_friend_requests', newFriendRequestList)

    def preventInfiniteNesting(self, newFriendNode):
        node = Node(newFriendNode)
        #DELTE MYSELF FROM FRIEND TO AVOID ENDLESS LOOP
        i=0
        friend = Node(node.getFriend(node.get('public_key')))
        for f in friend.get('data/friends'):
            if f['public_key'] == friend.get('public_key'):
                f['data'] = {}
        
    def base64DecodeMessages(self):
        for index, message in enumerate(self.get('data/messages')):
            if 'message' in message:
                try:
                    b64decode(message['message']).decode('utf-8')
                    message['message'] = b64decode(message['message'])
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
     
    def handleRoutedFriendRequest(self, packet):
        return self.addRoutedFriendRequest(packet)
    
    def handleRoutedMessage(self, packet):
        pass
    
    def handleFriendRequest(self, packet):
        self.addFriendRequest(packet)

    def addRoutedFriendRequest(self, packet):
        node = Node(packet)
        self.add('data/routed_friend_requests', node.get(), True)
        self.save()
        print "friend request added"
        
    def respondWithRelationship(self, friendNode):
        #TODO: apply permissions to dictionary for this relationship
        #TODO: pune fields to limit the data sent
        friendNode.get().update({"data" : copy.deepcopy(self.get('data'))})
        friendNode.preventInfiniteNesting(friendNode.get())
        friendNode.stripIdentityAndFriendsForProtocolV1(friendNode)
        friendNode.setModifiedToNow()
        return friendNode.get()
    
    
    def sendMessage(self, pub_keys, subject, message, thread_id=None):
        if thread_id:
            return {'public_key':pub_keys, 'timestamp':self.newTimeStamp(),'thread_id':thread_id,'subject':subject,'message':b64encode(message),'guid':str(uuid4())}
        else:
            return {'public_key':pub_keys, 'timestamp':self.newTimeStamp(),'thread_id':str(uuid4()),'subject':subject,'message':b64encode(message),'guid':str(uuid4())} 

    def sync(self, inbound, is_self=True, permission_object={}):
        self.updateTree(self.get(), inbound, is_self, permission_object)
        

    def updateTree(self, internal, inbound, is_self=True, permission_object={}):
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
                    self.updateTree(internalRef,inboundRef,is_self,permission_object_ref)
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
                                                self.updateStatus(internal,key,item[key_name],"update")
                                        else:
                                            newList.append(item)
                                            self.updateStatus(internal,key,item[key_name],"update")
                                    else:
                                        newList.append(internalRef_indexed[(item[key_name],)])
                                except:
                                    raise
                            else:
                                #CRUD: CREATE
                                if not is_self:
                                    if 'C' in permission_object_ref:
                                        newList.append(item)
                                        if not key_name=='guid':
                                            self.updateStatus(internal,key,item[key_name], "new")
                                else:
                                    newList.append(item)
                                    if not key_name=='guid':
                                        self.updateStatus(internal,key,item[key_name], "new")
                        for item in newList:
                            newList_indexed[(item[key_name],)] = item
                        for item in internalRef:
                            if (item[key_name],) not in newList_indexed:
                                newList.append(item)
                        internal[key]=newList
                    else:
                        self.updateTree(internalRef,inboundRef,is_self,permission_object_ref)
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
            for inboundRef in inbound:
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
                    self.updateTree(internalRef,inboundRef,is_self,permission_object_ref)
                    if type(inboundRef) == type({}):
                        inboundRef['modified'] = curTime
                        if 'label' not in inboundRef:
                            inboundRef['label'] = 'default'
                elif type(inboundRef) == type([]):
                    self.updateTree(internalRef,inboundRef,is_self,permission_object_ref)
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


    def updateStatus(self, jsonData, arrayKey, elementKey, newOrUpdate):
        lookup={}
        if arrayKey=='status': return
        if 'status' not in jsonData: return
        for item in jsonData['status']:
            if type(item['content'])== type({}):
                lookup[(item['content']['ref_id'],item['content']['type'])] = item
        if (elementKey,arrayKey) in lookup: return
        jsonData['status'].append({
            'timestamp': self.newTimeStamp(),
            'share_id': str(uuid4()),
            'content': {'type': arrayKey,'ref_id':elementKey,'newOrUpdate':newOrUpdate}
        })
        return
    
    @staticmethod
    def updatePair(key,internal,internalRef,inbound,inboundRef):
        if float(internal['modified'])<float(inbound['modified']):
            if key != 'modified':
                print 'update made to dict %s to %s' %(internal[key],inboundRef)
                logging.debug('update made to dict %s to %s' %(internal[key],inboundRef))
                internal[key] = inboundRef
                
    def searchForNode(self, searchNode):
        for node in self.get('data/friends'):
            try:
                node = Node(node)
            except:
                break
            if set(node.getFriendPublicKeysArray()) & set(searchNode.getFriendPublicKeysArray()):
                return node
        return None
    
    def createIPAddress(self, host, port='80', protocol='4'):
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
        self.add('data/identity/ip_address', self.createIPAddress(host, port, protocol))
        
    def save(self):
        self.setModifiedToNow()

class InvalidIdentity(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)