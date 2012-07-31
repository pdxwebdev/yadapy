import logging, os, json, time, copy, time, datetime, re, urllib, httplib
from base64 import b64encode, b64decode
from uuid import uuid4
from lib.crypt import encrypt, decrypt
from node import Node
from manager import YadaServer


class GetOutOfLoop( Exception ):
     pass
 
class NodeCommunicator(object):
    
    def __init__(self, node):
        self.node = node
    
    def _doRequest(self, toNode, hostNode, data, method='PUT', status=None):
        
        response = None
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
    
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
            
            packet = \
                {
                    "public_key" : toNode.get('public_key'), 
                    "method" : method, 
                    "data" : b64encode(data)
                }
                
            if status:
                packet.update({"status" : status})
                
            dataToSend = json.dumps(packet)
            
            params = urllib.urlencode({'data': dataToSend})
            
            for ipEl in self.node.get('data/identity/ip_address'):
                if str(host) == str(ipEl['address']) and str(port) == str(ipEl['port']):
                    managedNodeRelationship = self.node.publicKeyLookup(hostNode.get('public_key'))
                    node = None
                    if managedNodeRelationship:
                        node = self.node.chooseRelationshipNode(managedNodeRelationship, toNode, impersonate = True)
                    node = self.getClassInstanceFromNodeForNode(node.get())
                    nodeComm = NodeCommunicator(node)
                    return nodeComm.handlePacket(json.loads(dataToSend))
                    
                elif host + ":" + str(port) == ipEl['address']:
                    managedNodeRelationship = self.node.publicKeyLookup(inboundNode.get('public_key'))
                    node = None
                    if managedNodeRelationship:
                        node = self.node.chooseRelationshipNode(managedNodeRelationship, toNode, impersonate = True)
                    node = self.getClassInstanceFromNodeForNode(node.get())
                    nodeComm = NodeCommunicator(node)
                    return nodeComm.handlePacket(json.loads(dataToSend))
            
            conn = httplib.HTTPConnection(host, port)
            conn.request("POST", "", params, headers)
            
            response = conn.getresponse()
            response = response.read()
            conn.close()
            return response
            
        
        

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
        friendResponse = self._doRequest(meToSend, managerFriendNode, json.dumps(meToSend.get()), status="FRIEND_REQUEST")
        try:
            self.handlePacket(json.loads(friendResponse))
        except:
            print "Friend does not auto approve friend requests. There was no response from friend request."

        #simply send my entire object to manager
        response = self._doRequest(self.node, managerFriendNode, json.dumps(self.node.get()), status="MANAGE_REQUEST")
        
        return (response, friendResponse)
    
    def sendMessage(self, pub_keys, subject, message, thread_id=None):
        self.node.addMessage(self.node.sendMessage(pub_keys, subject, message, thread_id))
        for pub_key in pub_keys:
            self.updateRelationship(Node(self.node.getFriend(pub_key)))

    def syncManager(self):
        
        data = b64decode(encrypt(self.node.get('private_key'), self.node.get('private_key'), json.dumps(self.node.get())))
        #simply send my entire object to manager
        response = self._doRequest(self.node, self.node, data, status="MANAGE_SYNC")
        node = json.loads(decrypt(self.node.get('private_key'), self.node.get('private_key'), json.loads(response)['data']))
        self.node.sync(node)
        self.node.save()
        return response

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
        selectedFriend.set('source_indexer_key', self.node.matchFriend(destNode)['public_key'], True)
        
        sourceNodeCopy.set('public_key', newFriend.get('public_key'))
        sourceNodeCopy.set('private_key', newFriend.get('private_key'))
        
        sourceNodeCopy.set('source_indexer_key', self.node.matchFriend(destNode)['public_key'], True)
        sourceNodeCopy.replaceIdentityOfFriendsWithPubKeys()
        
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(sourceNodeCopy.get())))
        
        sourceFriendNode = Node(self.node.matchFriend(destNode))
        
        self.node.add('data/friends', selectedFriend.get())
        self.node.save()
        
        return self._doRequest(sourceFriendNode, destNode, data, status="ROUTED_FRIEND_REQUEST")
        
    def updateRelationship(self, destNode):
        sourceNodeCopy = Node(copy.deepcopy(self.node.get()))
        sourceNodeCopy.set('public_key', destNode.get('public_key'))
        sourceNodeCopy.set('private_key', destNode.get('private_key'))
        data = b64decode(encrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(sourceNodeCopy.get())))
        response = self._doRequest(sourceNodeCopy, destNode, data, method="GET")
        if response:
            if not type(response) == type({}):
                response = json.loads(response)
            packetData = decrypt(destNode.get('private_key'), destNode.get('private_key'), json.dumps(response['data']))
            self.node.updateFromNode(json.loads(packetData))
    
    def handlePacket(self, packet):
        
        packetData = b64decode(packet['data'])
        
        if packet.get('status', None) == 'FRIEND_REQUEST':
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
            
        elif packet.get('status', None) == 'ROUTED_FRIEND_REQUEST':
            friend = self.node.getFriend(packet['public_key'])
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            decrypted = json.loads(data)
            self.node.handleRoutedFriendRequest(decrypted)
            requestedFriend = self.node.getFriend(decrypted['routed_public_key'])
            node = self.getClassInstanceFromNodeForNode(requestedFriend)
            self.updateRelationship(node)
            friendNode = self.getClassInstanceFromNodeForNode(friend)
            return self.updateRelationship(friendNode)
        
        elif packet.get('status', None) == 'ROUTED_MESSAGE':
            friend = self.node.getFriend(packet['public_key'])
            data = decrypt(friend['private_key'], friend['private_key'], packetData)
            self.node.handleRoutedMessage(data['data'])
            
        elif packet.get('status', None) == 'MANAGE_REQUEST':
            node = self.node.getFriend(packet['public_key'])
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
            self.node.handleManageRequest(json.loads(data))
            
        elif packet.get('status', None) == 'MANAGE_SYNC':
            node = self.node.getManagedNode(packet['public_key'])
            data = decrypt(node['private_key'], node['private_key'], b64encode(packetData))
            responseData = self.node.syncManagedNode(Node(json.loads(data)))
            responseData = Node(responseData)
            return \
                {
                    "method" : "PUT",
                    "public_key" : responseData.get('public_key'),
                    "data" : encrypt(responseData.get('private_key'), responseData.get('private_key'), json.dumps(responseData.get()))
                }  
            
        elif packet.get('method', None) == 'PUT':
            friend = self.node.getFriend(packet['public_key'])
            data = decrypt(friend['private_key'], friend['private_key'], b64encode(packetData))
            self.node.updateFromNode(json.loads(data))
        
        elif packet.get('method', None) == 'IMPERSONATE':
            friend = self.node.getFriend(packet['public_key'])
            data = decrypt(friend['private_key'], friend['private_key'], packetData)
            self.node.updateFromNode(packetData, impersonate = True)
            
        elif packet.get('method', None) == 'GET':
            friend = self.node.getFriend(packet['public_key'])
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
        
    def newTimeStamp(self):
        return time.time()
    
    def getClassInstanceFromNodeForNode(self, identity):
        module = self.node.__module__
        module = module.split(".")
        module = ".".join(module[:-1])
        m = self.my_import(module)
        try:
            node = m.manager.YadaServer(identity)
        except:
            node = m.node.Node(identity)
        return node
    
    def my_import(self, name):
        m = __import__(name)
        for n in name.split(".")[1:]:
            m = getattr(m, n)
        return m