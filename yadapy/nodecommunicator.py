import logging, os, json, time, copy, time, datetime, re, urllib, httplib, socket, requests
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
    
    def __init__(self, node, manager = None):
        self.node = node
        self.manager = manager
    
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
            response = None
            
            if self.isHostedHere(host, port):
                response = self.handleInternally(hostNode, packet)
                if response is False:
                    response = self._internetRequest(host, port, packet)
            else:
                response = self._internetRequest(host, port, packet)
                
            if response:
                try:
                    if not type(response) == type({}):
                        response = json.loads(response)
                    responses.append(response)
                    self.handlePacket(response)
                except:
                    pass
        return responses
    
    def _internetRequest(self, host, port, dataToSend):
        s = requests.session()
        s.config['keep_alive'] = False
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
            if len(host.split(':')) > 1:
                port = int(host.split(':')[1])
                host = host.split(':')[0]
            elif 'port' in hostElement:
                try:
                    port = int(hostElement['port'])
                except:
                    pass
                
            if not port:
                port = 80
            addresses.append((host,port))
        return addresses
        
    #this should only return true where self isinstance of YadaServer
    def isHostedHere(self, host, port):
        for ipEl in self.node.get('data/identity/ip_address'):
            if str(host) == str(ipEl['address']) and str(port) == str(ipEl['port']):
                return True
            elif host + ":" + str(port) == ipEl['address']:
                return True
                
    #this should only be executed if self isinstance of YadaServer
    def handleInternally(self, node, packet):
        if self.manager:
            relationship = self.manager.publicKeyLookup(node.get('public_key'))
            managedNode = self.manager.chooseRelationshipNode(relationship, self.node)
        else:
            if isinstance(self.node, self.node.getClassInstanceFromNode().manager.YadaServer):
                relationship = self.node.publicKeyLookup(node.get('public_key'))
                managedNode = self.node.chooseRelationshipNode(relationship, self.node, impersonate=True)
            else:
                return False
            
        managedNode = self.node.getClassInstanceFromNodeForNode(managedNode.get())
        nodeComm = NodeCommunicator(managedNode)
        
        return nodeComm.handlePacket(json.loads(packet))

    def addManager(self, host):
        
        #add the new manager's host address to my ip addresses
        self.node.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        #save the manager friend to the node
        friendPublicKey = unicode(uuid4())
        friendPrivateKey = unicode(uuid4())
        managerFriendNode = YadaServer({}, {"name" : "new manager" })
        managerFriendNode.set('public_key', friendPublicKey)
        managerFriendNode.set('private_key', friendPrivateKey)
        managerFriendNode.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        self.node.add('data/friends', managerFriendNode.get())
        self.node.save()
        
        #build the friend request
        meToSend = Node(copy.deepcopy(self.node.get()))
        meToSend.set('public_key', friendPublicKey)
        meToSend.set('private_key', friendPrivateKey)
        
        managerFriendNode.add('data/friends', meToSend.get())
        
        #send the friend request to the manager
        friendResponses = self._doRequest(meToSend, managerFriendNode, json.dumps(meToSend.get()), status="FRIEND_REQUEST")

        #simply send my entire object to manager
        encryptedData = encrypt(managerFriendNode.get('private_key'), managerFriendNode.get('private_key'), json.dumps(self.node.get()))
        responses = self._doRequest(self.node, managerFriendNode, b64decode(encryptedData), status="MANAGE_REQUEST")
        return (responses, friendResponses)
    
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

    def requestFriend(self, host):
                
        #save the manager friend to the node
        friendPublicKey = unicode(uuid4())
        friendPrivateKey = unicode(uuid4())
        friendNode = Node({}, {"name" : "new manager" })
        friendNode.set('public_key', friendPublicKey)
        friendNode.set('private_key', friendPrivateKey)
        friendNode.add('data/identity/ip_address', self.node.createIPAddress(host))
        
        self.node.add('data/friends', friendNode.get())
        self.node.save()
        
        #build the friend request
        meToSend = Node(copy.deepcopy(self.node.get()))
        meToSend.set('public_key', friendPublicKey)
        meToSend.set('private_key', friendPrivateKey)
        
        friendNode.add('data/friends', meToSend.get())
        
        #send the friend request to the manager
        friendResponse = self._doRequest(meToSend, friendNode, json.dumps(meToSend.get()), status="FRIEND_REQUEST")
        try:
            self.handlePacket(json.loads(friendResponse))
        except:
            print "Friend does not auto approve friend requests. There was no response from friend request."

    def routeRequestThroughNode(self, destNode, destinationPublicKey):
        
        newFriend = Node({}, {'name':'Just created for the new keys'})
        
        selectedFriend = Node({}, {"name" : "new friend"})
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        sourceNodeCopy.set('routed_public_key', destinationPublicKey, True)

        selectedFriend.set('routed_public_key', destinationPublicKey, True)
        selectedFriend.set('public_key', newFriend.get('public_key'))
        selectedFriend.set('private_key', newFriend.get('private_key'))
        selectedFriend.setModifiedToNow()
        selectedFriend.set('source_indexer_key', destNode.get('public_key'), True)
        
        sourceNodeCopy.set('public_key', newFriend.get('public_key'))
        sourceNodeCopy.set('private_key', newFriend.get('private_key'))
        
        sourceNodeCopy.set('source_indexer_key', destNode.get('public_key'), True)
        sourceNodeCopy.replaceIdentityOfFriendsWithPubKeys()
        
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(sourceNodeCopy.get())))
        
        self.node.add('data/friends', selectedFriend.get())
        self.node.save()
        
        return self._doRequest(destNode, destNode, data, status="ROUTED_FRIEND_REQUEST")
        
    def updateRelationship(self, destNode):
        destNodeCopyNode = Node(copy.deepcopy(destNode.get()))
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        if self.impersonate:
            dictToSend = destNode.respondWithRelationship(destNode)
        else:
            dictToSend = self.node.respondWithRelationship(destNodeCopyNode)
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(dictToSend)))
        sourceNodeCopy.set('public_key', destNode.get('public_key'))
        sourceNodeCopy.set('private_key', destNode.get('private_key'))
        self._doRequest(sourceNodeCopy, destNode, data, method="GET")

    def grantPromotion(self, destNode):
        destNodeCopyNode = Node(copy.deepcopy(destNode.get()))
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        
        
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(sourceNodeCopy.get())))
        
        self._doRequest(sourceNodeCopy, destNode, data, method="PUT", status="PROMOTION_REQUEST")

    def handlePacket(self, packet):
        
        packetData = b64decode(packet['data'])
        friend = self.node.getFriend(packet['public_key'])
        if not friend and packet.get('status', None) not in ['FRIEND_REQUEST', "REGISTER_REQUEST"]:
            raise("No identity found for packet.")
        else:
            node = friend
        
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
            response = self.node.handlePromotionRequest(decrypted)
            
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
            self.node.handleRoutedFriendRequest(decrypted)
            requestedFriend = self.node.getFriend(decrypted['routed_public_key'])
            node = self.node.getClassInstanceFromNodeForNode(requestedFriend)
            self.updateRelationship(node)
            friendNode = self.node.getClassInstanceFromNodeForNode(friend)
            return self.updateRelationship(friendNode)
        
        elif packet.get('status', None) == 'ROUTED_MESSAGE':
            
            data = decrypt(friend['private_key'], friend['private_key'], packetData)
            self.node.handleRoutedMessage(data['data'])
            
        elif packet.get('status', None) == 'MANAGE_REQUEST':
            
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
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
            self.node.updateFromNode(json.loads(packetData))
            responseData = self.node.respondWithRelationship(Node(json.loads(packetData)))
            responseData = Node(responseData)
            return \
                {
                    "method" : "PUT",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }
        elif packet.get('method', None) == 'SYNC':
            node = self.node.get()
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
            responseData = self.node.sync(json.loads(data))
            responseData = Node(responseData)
            return responseData
    def newTimeStamp(self):
        return time.time()
