import logging, os, marshal, json, cPickle, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from lib.crypt import encrypt, decrypt
from uuid import uuid4
from node import Node, InvalidIdentity


class YadaServer(Node):
    
    def __init__(self, *args, **kwargs):
        
        if 'identityData' in kwargs:
            identityData = kwargs['identityData']
        else:
            identityData = args[0]
            kwargs['identityData'] = identityData
        
        try:
            newIdentity = args[1]
        except:
            newIdentity = None
        
        if type(kwargs['identityData']) == type(u'') or type(kwargs['identityData']) == type(''):
            identityData = self.getManagedNode(kwargs['identityData'])
        elif type(kwargs['identityData']) == type({}):
            identityData = kwargs['identityData']
        else:
            raise InvalidIdentity("A valid server Identity was not given nor was a public_key specified.")
        
        super(YadaServer, self).__init__(*args, **kwargs)
    
    def validIdentity(self, data):
        try:
            if 'public_key' in data \
            and 'private_key' in data \
            and 'modified' in data \
            and 'data' in data \
            and 'type' in data['data'] \
            and data['data']['type'] == 'manager' \
            and 'friends' in data['data'] \
            and 'identity' in data['data'] \
            and 'messages' in data['data'] \
            and 'name' in data['data']['identity']:
                return True
            else:
                raise InvalidIdentity("invalid identity dictionary for identity")
        except InvalidIdentity:
            raise

    def newIdentity(self, identity):
        self.identityData.update(identity)
        return copy.deepcopy({
            'public_key':self.newUuid(), 
            'private_key':self.newUuid(),
            'modified': self.newTimeStamp(),
            'friend_requests': [],
            'data':{
                "type" : "manager",
                "routed_friend_requests" : [],
                "routed_messages" : [],
                "managed_nodes" : [],
                "messages" : [],
                "friends" : self._initialFriends,
                "status" : [],
                "identity" : self.identityData
            }
        })
        
    def stripIdentityAndFriendsForProtocolV1(self, node):
        self.replaceIdentityOfFriendsWithPubKeys()
        self.stripIdentityOfIrrelevantFriendRequests(node)
        self.stripManagedNodes()
        
    def stripManagedNodes(self):
        try:
            self.set('data/managed_nodes', [])
        except:
            pass
        
    #this method was invented just so an incomming packet can be decrypted
    #so it doesn't matter which node in the relationship we return
    def getFriend(self, public_key):
        friend = self.publicKeyLookup(public_key)
        if friend:
            return Node(friend[0]).getFriend(public_key)
        else:
            friend = super(YadaServer, self).getFriend(public_key)
            if friend:
                return friend
            else:
                friend = self.getManagedNode(public_key)
                return friend
        
    def getManagedNode(self, public_key):
        for friend in self.get('data/managed_nodes'):
            if friend['public_key']==public_key:
                return friend
        return None
    
    def addManagedNode(self, data):
        try:
            #using node class to validate the node data before inserting it into managed users
            node = Node(data)
            #adding user to the database
            self.add('data/managed_nodes', node.get())
            self.save()
        except:
            raise InvalidIdentity("cannot add invalid node to managed nodes")
        
    def syncManagedNode(self, node):
        for managedNode in self.get('data/managed_nodes'):
            managedNode = Node(managedNode)
            if managedNode.get('public_key') == node.get('public_key'):
                managedNode.sync(node.get())
                self.save()
                return managedNode.get()
        return None
    
    def publicKeyLookup(self, public_key):
        nodes = []
        for node in self.get('data/managed_nodes'):
            for friend in node['data']['friends']:
                if public_key == friend['public_key']:
                    nodes.append(node)
        for friend in self.get('data/friends'):
            if public_key == friend['public_key']:
                nodes.append(self.get())
        return nodes
    
    def getServerData(self):
        return self.get()
    
    def queryIndexer(self, dataToSend, indexer, user):
        serverData = self.get('data/friends')
        params = urllib.urlencode({'data': dataToSend})
        intersection = set([x['public_key'] for x in serverData]) & set([x['public_key'] for x in indexer.get('data/friends')])
        if intersection or set(self.getIpAddressArray()) % set(indexer.getIpAddressArray()):
            return json.loads(self.hostedUserUpdate(json.loads(dataToSend)))
        else:
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
            for i, ip in enumerate(indexer.get('data/identity/ip_address')):
                conn = httplib.HTTPConnection("%s" %(ip['address']))
                conn.request("POST", "", params, headers)
                response = conn.getresponse()
                obj = response.read()
                return json.loads(obj)
                message = json.loads(obj["thread"])
                posts.extend(message)
                conn.close()
    
    def loadInboundJson(self, request):
        jsonDict = {}
        try:
            jsonDict = json.loads(request.POST['data'])
            if type(jsonDict['data']) == type("") or type(jsonDict['data']) == type(u""):
                jsonDict['data'] = jsonDict['data'].replace(' ', '+')
        except:
            logging.debug('loadInboundJson error in parsing json')
        return jsonDict
    
    @staticmethod
    def getInformationFromIdentity(data, profile):
        if data['query'] == 'messages':
            posts = []
            guids_added = []
            thread_id = data['thread_id']
            posts.extend(profile.getThread(thread_id))
            for message in posts:
                message['timestamp'] = int(round(float(message['timestamp']),0))
                message['who'] = 'friend'
            return json.dumps(posts)
        if data['query'] == 'friend_request_count':
            request_count = 0
            friendList = [x['public_key'] for x in data['data']['friends']]
            if 'routed_friend_requests' in profile.get('data'):
                for friend in profile.get('data/routed_friend_requests'):
                    if 'routed_public_key' in friend and friend['routed_public_key'] in friendList:
                        request_count += 1
            else:
                request_count = 0
            return json.dumps({'friend_request_count' : request_count})
        if data['query'] == 'friend_requests':
            requests = []
            friendList = [x['public_key'] for x in data['data']['friends']]
            if 'routed_friend_requests' in profile.get('data'):
                for friend in profile.get('data/routed_friend_requests'):
                    if 'routed_public_key' in friend and friend['routed_public_key'] in friendList:
                        requests.append(friend)
            else:
                requests = []
            return json.dumps({'friend_requests' : requests})
                
    def consumePacket(self, responseDecoded):
        #some serious rethinking needed here
        #importToNode will fail if the packet is not intended for the server
        #we will then try to see if the packet is intended for a managed node
        if not self.importToNode(responseDecoded):
            self.hostedUserUpdate(responseDecoded)
            return "Packet was intended for managed node"
        else:
            return "Packet was intended for server"

    def hostedUserUpdate(self, jsonDict, request=None):
        idQuery = self.getManagedNode(jsonDict['public_key'])
        #check to see if a hosted user is trying to replicate self
        if idQuery:
                        
            id = Node(idQuery)#p
            decryptedIncomingIdentity = decrypt(id.get('private_key'), id.get('private_key') ,jsonDict['data'].replace(' ', '+'))
            incomingId = Node(json.loads(decryptedIncomingIdentity))#user
            
            InternalId = Node(self.getManagedNode(id.get('public_key')))#data
            if InternalId.get():
                try:
                    InternalId.dedupIP()
                except:
                    logging.warning("an error occured when running dedupIP() method")
                InternalId.sync(incomingId.get(), True, {})
            self.updateManagedNode(InternalId)
        elif jsonDict.get('status', None) and jsonDict['status'] == "MANAGE_REQUEST":
            #replace spaces with plus symbols, this was a problem early on
            data = b64decode(jsonDict['data'].replace(' ', '+'))
            #attemped to load data into memory structure
            data = json.loads(data)
            self.addManagedNode(data)
            return "node is now managed by this node manager"

    def chooseRelationshipNode(self, relationship, inboundNode, impersonate = False):
        r = relationship
        
        for idx, node in enumerate(r):
            p = Node(node)
            #this or clause is only for the case where yada server is in the friendship and 
            #the managed node only has yada server as a friend
            if p.get('public_key') == self.get('public_key'):
                if impersonate == False:
                    return self
                else:
                    if r[0]['public_key'] != self.get('public_key'):
                        return self.getClassInstanceFromNodeForNode(Node(r[0]).get())
                    else:
                        return self.getClassInstanceFromNodeForNode(Node(r[1]).get())
        
        for node in r:
            p = Node(node)
            
            intersection = set([x['public_key'] for x in p.getFriendPublicKeyList()]) & set([x['public_key'] for x in inboundNode.get('data/friends')])
            
            if impersonate:
                if len(intersection) > 1:
                    return self.getClassInstanceFromNodeForNode(p.get())
            else:
                if len(intersection) == 1:
                    return self.getClassInstanceFromNodeForNode(p.get())
        
        for node in r:
            p = Node(node)
            
            if p.get('public_key') != inboundNode.get('public_key'):
                return self.getClassInstanceFromNodeForNode(p.get())
        
    def getRelationshipData(self, relationship):
        pass

    def updateFriendInIdentity(self, inbound, p):
        
        if not isinstance(inbound, Node):
            raise InvalidIdentity("inbound parameter not an instance of Identity class")
        
        if not isinstance(p, Node):
            raise InvalidIdentity("p parameter not an instance of Identity class")
        
        if 'status' in inbound.get() and inbound.get('status')=='FRIEND_REQUEST':
            inbound.delKey('status')
            
        if 'status' in inbound.get() and inbound.get('status')=='ROUTED_FRIEND_REQUEST':
            pass
        
        friend = Node(p.getFriend(inbound.get('public_key')))
                
        if 'permissions' in inbound.get():
            if not 'permissions' in friend.get():
                friend.set('permissions_approved', "0", True)
                friend.set('permissions', inbound.get('permissions'))
            else:
                if set(inbound.get('permissions')) != set(friend.get('permissions')):
                    friend.set('permissions_approved', "0")
                    friend.set('permissions', inbound['permissions'])
                    
        if not 'modified' in friend.get() or float(friend.get('modified')) < float(inbound.get('modified')):
            friend.set('data', inbound.get('data'))
            if "web_token" in inbound.get():
                friend.set('web_token', inbound.get('web_token'))
            self.updateManagedNode(p)
        p.updateFriend(inbound)

    def updateFromNode(self, inboundNode, impersonate = False):
        managedNode = self.getManagedNode(inboundNode['public_key'])
        managedNodeRelationship = self.publicKeyLookup(inboundNode['public_key'])
        node = None
        if managedNode:
            self.syncManagedNode(managedNode, inboundNode)
        elif managedNodeRelationship:
            node = self.chooseRelationshipNode(managedNodeRelationship, Node(inboundNode), impersonate)
        
        if node:
            node = self.getClassInstanceFromNodeForNode(node.get())
            if isinstance(node, YadaServer):
                super(YadaServer, node).updateFromNode(inboundNode)
            else:
                if impersonate:
                    node.sync(inboundNode, is_self=False, permission_object=inboundNode['permissions'])
                    node.save()
                else:
                    node.updateFromNode(inboundNode)
        else:
            super(YadaServer, self).updateFromNode(inboundNode)
    
    def handleRoutedMessage(self, packet):
        pass
        
    def handleFriendRequest(self, packet):
        
        friendRequest = Node(packet)
        
        if 'routed_public_key' in packet:
            node = self.matchFriend(friendRequest)
            managedNodeRelationship = self.publicKeyLookup(packet['routed_public_key'])
            node = self.chooseRelationshipNode(managedNodeRelationship, self.get(), impersonate = True)
            node = self.getClassInstanceFromNodeForNode(node.get())
            node.addFriendRequest(friendRequest.get())
        else:
            self.addFriend(copy.deepcopy(friendRequest.get()))
            logging.debug('added new friend to friends list')
        return self.respondWithRelationship(friendRequest)
    
    def handleManageRequest(self, packet):
        self.addManagedNode(packet)
        node = Node(self.matchFriend(Node(packet)))
        return self.respondWithRelationship(node)
    
    def handlePromotionRequest(self, packet, public_key):
        managedNodeRelationship = self.publicKeyLookup(public_key)
        managedNode = self.chooseRelationshipNode(managedNodeRelationship, Node(packet), impersonate=True)
        managedNode.addPromotionRequest(packet)
        
    def forceJoinNodes(self, sourceNode, destNode):
        
        newFriendRequest = Node({}, sourceNode.get('data/identity'), sourceNode.getFriendPublicKeysDict())
        newFriendRequest.set('status', 'FRIEND_REQUEST', True)
        
        newIndexerFriendRequest = Node({}, destNode.get('data/identity'), destNode.getFriendPublicKeysDict())
        newIndexerFriendRequest.set('public_key', newFriendRequest.get('public_key'))
        newIndexerFriendRequest.set('private_key', newFriendRequest.get('private_key'))
        
        #checks to see if the user has already "friended" this indexer
        res = destNode.matchFriend(sourceNode)
        if not res:
            newFriendRequest.replaceIdentityOfFriendsWithPubKeys()
            destNode.add('data/friends', newFriendRequest.get())
            destNode.save()
        
        #checks to see if the indexer has already "friended" this user
        res = sourceNode.matchFriend(destNode)
        if not res:
            newIndexerFriendRequest.replaceIdentityOfFriendsWithPubKeys()
            sourceNode.add('data/friends', newIndexerFriendRequest.get())
            sourceNode.save()
        
        return newFriendRequest.get()
    
    def getFriendRequestsFromIndexer(self, node, indexer):
        selectedFriendIndexer = Node(node.matchFriend(indexer))
        dataToSend = '{"method" : "GET", "public_key" : "%s", "data" : "%s"}' %(selectedFriendIndexer.get('public_key'), encrypt(selectedFriendIndexer.get('private_key'), selectedFriendIndexer.get('private_key'), json.dumps({'query':'friend_requests', 'data':{'friends':[{'public_key':x['public_key']} for x in node.get('data/friends')]}})))
        return self.queryIndexer(dataToSend, selectedFriendIndexer, node) 

    def respondWithRelationship(self, inboundNode, impersonate=False):
        inbound = inboundNode.get()
        managedNode = self.getManagedNode(inbound['public_key'])
        managedNodeRelationship = self.publicKeyLookup(inbound['public_key'])
        node = None
        if managedNode:
            self.syncManagedNode(managedNode, inboundNode)
        elif managedNodeRelationship:
            node = self.chooseRelationshipNode(managedNodeRelationship, inboundNode, impersonate)
        
        if node and not isinstance(node, YadaServer):
            node = self.getClassInstanceFromNodeForNode(node.get())
            return node.respondWithRelationship(inboundNode)
        else:
            return super(YadaServer, self).respondWithRelationship(inboundNode)