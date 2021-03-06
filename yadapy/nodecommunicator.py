import logging, os, ujson as json, time, copy, time, datetime, re, urllib, httplib, socket, requests
from base64 import b64encode, b64decode
from uuid import uuid4
from lib.crypt import encrypt, decrypt
from node import Node
from manager import YadaServer

timeout = 1
socket.setdefaulttimeout(timeout)

class GetOutOfLoop( Exception ):
     pass
 
class NodeCommunicator(object):

    impersonate = False
    
    def __init__(self, node):
        self.node = node
    
    def _doRequest(self, toNode, hostNode, data, method='PUT', status=None):
        
        packet = self._buildPacket(toNode, hostNode, data, method, status)
        
        responses = []
        addresses = []
        for address in self._getHostPortArray(hostNode):
            if address in addresses:
                continue
            else:
                addresses.append(address)
                
            host, port = address
            
            response = self._internetRequest(host, port, packet)
                
            if response:
                responses.append(response)
                
        return responses
    
    def _internetRequest(self, host, port, dataToSend):
        response = requests.post("http://" + host + ":" + str(port) + "/", data={'data': dataToSend})
        return response.content
        
    def _buildPacket(self, toNode, hostNode, data, method='PUT', status=None):

            packet = \
                {
                    "public_key" : hostNode.get('public_key'), 
                    "method" : "IMPERSONATE" if self.impersonate else method, 
                    "data" : b64encode(data)
                }
            if status:
                packet.update({"status" : status})
                
            return json.dumps(packet)
            
    def _getHostPortArray(self, hostNode):
        addresses = []
        for hostElement in hostNode.get('data/identity/ip_address'):
            host = hostElement['address']
            port = None
            if 'port' in hostElement:
                try:
                    port = int(hostElement['port'])
                except:
                    pass
            elif len(host.split(':')) == 2:
                try:
                    port = int(host.split(':')[1])
                    host = host.split(':')[0]
                except:
                    pass
                try:
                    port = int(host.split(':')[2])
                    host = host.split(':')[1]
                except:
                    pass
            elif len(host.split(':')) == 3:
                try:
                    port = int(host.split(':')[2])
                    host = host.split(':')[1]
                except:
                    pass
                
            if not port:
                port = 80
            addresses.append((host,port))
        return addresses

    def addManager(self, host):
        
        #add the new manager's host address to my ip addresses
        self.node.addIPAddress(self.node.createIPAddress(host))
        self.node.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        #save the manager friend to the node
        friendPublicKey = unicode(uuid4())
        friendPrivateKey = unicode(uuid4())
        managerFriendNode = YadaServer({}, {"name" : "new manager" })
        managerFriendNode.set('public_key', friendPublicKey)
        managerFriendNode.set('private_key', friendPrivateKey)
        managerFriendNode.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        self.node.add('data/friends', managerFriendNode.get())
                
        #build the friend request
        meToSend = Node(copy.deepcopy(self.node.get()))
        meToSend = self.node.getClassInstanceFromNodeForNode(meToSend.get())
        meToSend = self.node.respondWithRelationship(copy.deepcopy(managerFriendNode))
        
        responses = []
        #send the friend request to the manager
        response = self._doRequest(meToSend, managerFriendNode, json.dumps(meToSend), status="FRIEND_REQUEST")
        responses.extend(response)
        
        #simply send my entire object to manager
        encryptedData = encrypt(managerFriendNode.get('private_key'), managerFriendNode.get('private_key'), json.dumps(self.node.get()))
        response = self._doRequest(self.node, managerFriendNode, b64decode(encryptedData), status="MANAGE_REQUEST")
        responses.extend(response)
        
        for response in responses:
            try:
                self.handlePacket(json.loads(response))
            except:
                logging.debug("failed to handle packet")
                raise
    
    def sendMessage(self, pub_keys, subject, message, thread_id=None, guid=None):
        self.node.addMessage(self.node.sendMessage(pub_keys, subject, message, thread_id, guid))
        for pub_key in pub_keys:
            friend = self.node.getFriend(pub_key)
            try:
                node = Node(friend)
            except:
                node = Node({}, friend['data']['identity'])
                
            self.updateRelationship(node)

    def syncManager(self):
        
        data = b64decode(encrypt(self.node.get('private_key'), self.node.get('private_key'), json.dumps(self.node.get())))
        #simply send my entire object to manager
        responses = self._doRequest(self.node, self.node, data, status="MANAGE_SYNC")
        return responses

    def requestFriend(self, host, source_node = None, dest_node = None):
                
        #save the manager friend to the node
        friendPublicKey = unicode(uuid4())
        friendPrivateKey = unicode(uuid4())
        friendNode = Node({}, {"name" : "new manager" })
        friendNode.set('public_key', friendPublicKey)
        friendNode.set('private_key', friendPrivateKey)
        if source_node and dest_node:
            friendNode.set('source_node_key', source_node['public_key'], True)
            friendNode.set('dest_node_key', dest_node['public_key'], True)
        friendNode.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        self.node.addFriend(friendNode.get())
        
        #build the friend request
        meToSend = Node(copy.deepcopy(self.node.get()))
        meToSend.set('public_key', friendPublicKey)
        meToSend.set('private_key', friendPrivateKey)
        if source_node and dest_node:
            meToSend.set('source_node_key', source_node['public_key'], True)
            meToSend.set('dest_node_key', dest_node['public_key'], True)
        friendNode.add('data/friends', meToSend.get())
        
        #send the friend request to the manager
        friendResponses = self._doRequest(meToSend, friendNode, json.dumps(meToSend.get()), status="FRIEND_REQUEST")
        for response in friendResponses:
            try:
                self.handlePacket(json.loads(response))
            except:
                print "Friend does not auto approve friend requests. There was no response from friend request."
        return friendNode

    def routeRequestForNode(self, destNode, destinationPublicKey, name='new friend', avatar=''):
        
        newFriend = Node({}, {'name':'Just created for the new keys'})
        
        selectedFriend = Node(self.node.getFriend(destinationPublicKey))
        selectedFriend.set('routed_public_key', destinationPublicKey, True)
        selectedFriend.set('public_key', newFriend.get('public_key'))
        selectedFriend.set('private_key', newFriend.get('private_key'))
        selectedFriend.setModifiedToNow()
        selectedFriend.set('source_indexer_key', destNode.get('public_key'), True)
        
        destNode.add('data/friends', selectedFriend.get())
        
        sourceNodeCopy = Node(copy.deepcopy(destNode.get()))
        sourceNodeCopy.set('routed_public_key', destinationPublicKey, True)
        sourceNodeCopy.set('source_indexer_key', destNode.get('public_key'), True)
        
        
        data = b64decode(encrypt(destNode.get('private_key'), 
                                 destNode.get('private_key'), 
                                 json.dumps(sourceNodeCopy.get())))
        
        self.node.updateFromNode(destNode.get(), preserve_key=selectedFriend.get('public_key'))
        self.updateRelationship(destNode)
        
        packet = self._buildPacket(destNode, destNode, data, status="ROUTED_FRIEND_REQUEST")
        
        self.handlePacket(json.loads(packet))
        
        return selectedFriend.get()
        
    def updateRelationship(self, destNode, toInclude = None):
        destNodeCopyNode = Node(copy.deepcopy(destNode.get()))
        sourceNodeCopy = self.node.get()
        
        if self.impersonate:
            dictToSend = destNode.respondWithRelationship(destNode)
        else:
            dictToSend = self.node.respondWithRelationship(destNodeCopyNode)
        
        if toInclude:
            dictToSend['include_node'] = toInclude
        
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(dictToSend)))
        
        responses = self._doRequest(sourceNodeCopy, destNode, data, method="GET")
        for response in responses:
            self.handlePacket(json.loads(response))
            
    def grantPromotion(self, destNode):
        destNodeCopyNode = Node(copy.deepcopy(destNode.get()))
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        
        if self.impersonate:
            dictToSend = destNode.respondWithRelationship(destNode)
        else:
            dictToSend = self.node.respondWithRelationship(destNodeCopyNode)
        dictToSend['public_key'] = self.node.get('public_key')
        dictToSend['private_key'] = self.node.get('private_key')
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(dictToSend)))
        
        self._doRequest(sourceNodeCopy, destNode, data, method="PUT", status="PROMOTION_REQUEST")

    def handlePacket(self, packet, callbackCls = None):
        
        packetData = b64decode(packet['data'])
        friend = self.node.getFriend(packet['public_key'])
        if not friend and packet.get('status', None) not in ['FRIEND_REQUEST', "REGISTER_REQUEST"]:
            node = self.node.getManagedNode(packet['public_key'])
            if not node:
                friend = self.node.getFriend(packet['public_key'])
                raise BaseException("No identity found for packet.")
        
        if packet.get('status', None) in ['FRIEND_REQUEST', "REGISTER_REQUEST"]:
            response = self.node.handleFriendRequest(json.loads(packetData))
            
            #Response will be None if the node does not automatically approve friend requests
            if response:
                responseData = Node(response)
                responsePacket = \
                    {
                        "method" : "PUT",
                        "public_key" : response['public_key'],
                        "data" : encrypt(response['private_key'], response['private_key'], json.dumps(responseData.get()))
                    }     
                return responsePacket
            else:
                return None
        
        elif packet.get('status', None) in ['PROMOTION_REQUEST']:
            
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            decrypted = json.loads(data)
            response = self.node.handlePromotionRequest(decrypted, friend['public_key'])
            
            #Response will be None if the node does not automatically approve friend requests
            if response:
                responseData = Node(response)
                responsePacket = \
                    {
                        "method" : "PUT",
                        "public_key" : response['public_key'],
                        "data" : encrypt(response['private_key'], response['private_key'], json.dumps(responseData.get()))
                    }     
                return responsePacket
            else:
                return None
            
        elif packet.get('status', None) == 'ROUTED_FRIEND_REQUEST':
            
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            decrypted = json.loads(data)
            
            #updating at the median node
            self.node.handleRoutedFriendRequest(decrypted)
            
            #updating the destination
            requestedFriend = self.node.getFriend(decrypted['routed_public_key'])
            if not requestedFriend:
                requestedFriend = self.node.getFriendBySourceIndexerKey(decrypted['routed_public_key'])
                if not requestedFriend:
                    return \
                        {
                            "status" : "404"
                        }  
                
            requestedFriendNode = self.node.getClassInstanceFromNodeForNode(requestedFriend)
            self.updateRelationship(requestedFriendNode)
            
            #updating the originator
            requestingFriendNode = self.node.getClassInstanceFromNodeForNode(friend)
            self.updateRelationship(requestingFriendNode)
        
        elif packet.get('status', None) == 'ROUTED_MESSAGE':
            
            data = decrypt(friend['private_key'], friend['private_key'], packetData)
            self.node.handleRoutedMessage(data['data'])
            
        elif packet.get('status', None) == 'MANAGE_REQUEST':
            
            try:
                data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            except:
                data = packetData
            responseData = self.node.handleManageRequest(json.loads(data))
            responseData = Node(responseData)
            return \
                {
                    "method" : "PUT",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }  
            
        elif packet.get('status', None) == 'MANAGE_SYNC':
            
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
            responseData = self.node.syncManagedNode(Node(json.loads(data)))
            responseData = Node(responseData)
            return \
                {
                    "method" : "SYNC",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }  
        
        elif packet.get('status', None) in ['INDEXER_REQUEST_ACCEPT', 'INDEXER_REQUEST_UPDATE']:
            packetData = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            loadedData = json.loads(packetData)
            if len(loadedData['data']['friends']) == 2:#is the indexer friends with these two?
                for remoteFriend in loadedData['data']['friends'][0]['data']['friends']:
                    friend1 = self.node.getFriend(remoteFriend['public_key'])
                    if friend1:
                        break
                for remoteFriend in loadedData['data']['friends'][1]['data']['friends']:
                    friend2 = self.node.getFriend(remoteFriend['public_key'])
                    if friend2:
                        break
                if friend1 and friend2:#is are these two friends with the sending indexer
                    confirmed1 = False
                    for friend in friend1['data']['friends']:
                        if friend['public_key'] == loadedData['data']['friends'][0]['routed_public_key'] or \
                            friend['public_key'] == loadedData['data']['friends'][0]['source_indexer_key'] or \
                            friend['public_key'] == loadedData['data']['friends'][0]['public_key']:
                            confirmed1 = friend
                            break
                    confirmed2 = False
                    for friend in friend2['data']['friends']:
                        if friend['public_key'] == loadedData['data']['friends'][1]['routed_public_key'] or \
                            friend['public_key'] == loadedData['data']['friends'][1]['source_indexer_key'] or \
                            friend['public_key'] == loadedData['data']['friends'][1]['public_key']:
                            confirmed2 = friend
                            break
                    if confirmed1 and confirmed2:
                        callbackCls = callbackCls()
                        if packet.get('status', None) == 'INDEXER_REQUEST_UPDATE':
                            callbackCls.friendRequestSuccess(friend1, friend2)
                        elif packet.get('status', None) == 'INDEXER_REQUEST_ACCEPT':
                            callbackCls.friendAcceptSuccess(friend1, friend2)
                        return {}
                    else:
                        return {}
            #show some kind of notification
            
        elif packet.get('method', None) == 'PUT':
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            self.node.updateFromNode(json.loads(data))
        
        elif packet.get('method', None) == 'IMPERSONATE':
            
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            self.node.updateFromNode(json.loads(data), impersonate = True)
            responseData = self.node.respondWithRelationship(Node(json.loads(data)), impersonate = True)
            responseData = Node(responseData)
            return \
                {
                    "method" : "PUT",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }
            
        elif packet.get('method', None) == 'GET':
            
            packetData = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            start = time.time()
            friend = json.loads(packetData)
            if 'messages' in friend['data']:
                callbackCls = callbackCls()
                callbackCls.handleMessages(friend['data']['messages'])
            self.node.updateFromNode(friend)
            end = time.time()
            print "updateFromNode: %s" % (end - start)
            start = time.time()
            responseData = self.node.respondWithRelationship(Node(json.loads(packetData)))
            end = time.time()
            print "updateFromNode: %s" % (end - start)
            start = time.time()
            responseData = Node(responseData)
            encryptedResponse =  {
                    "method" : "PUT",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }
            end = time.time()
            print "updateFromNode: %s" % (end - start)
            return encryptedResponse
                
        elif packet.get('method', None) == 'SYNC':
            node = self.node.get()
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
            responseData = self.node.sync(json.loads(data))
            responseData = Node(responseData)
            return responseData
            
    def newTimeStamp(self):
        return time.time()
