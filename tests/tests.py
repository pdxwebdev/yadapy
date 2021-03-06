import json, time, unittest, os
from uuid import uuid4
from yadapy.node import Node
from yadapy.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from twisted.web import server, resource
from twisted.internet import reactor

class UnitTests(unittest.TestCase):
    
    def setUp(self):
        #signup two new users
        self.user1 = Node({}, {"name" : "user1"})
        
        self.user2 = Node({}, {"name" : "user2"})
        
    def test_Node_sync_simple(self):
        
        time.sleep(1)
        
        newName = 'mike'
        newPhone = {
                  "prefix" : "503",
                  "area_code" : "257",
                  "number" : "0484",
                  "country_code" : "1",
                  "label" : "home"
                }
        self.user2.set('data/identity/name', newName)
        self.user2.add('data/identity/location/0/phone', newPhone, True)
        self.user2.set('data/identity/location/0/phone/0', newPhone, True)
        self.user2.set('data/identity/location/0/phone/0/area_code', '360', True)
        
        self.user1.set('data/identity/location/0/guid', u'asdf', True)
        self.user2.set('data/identity/location/0/guid', u'asdf', True)
        
        self.assertTrue(self.user2.get('data/identity/location/0/phone/0/area_code') == '360')
        self.assertTrue(self.user2.get('data/identity/name') == newName)
        
        self.user1.sync(self.user2.get())
        self.assertTrue(self.user1.get('data/identity/name') == newName)
        self.assertTrue(self.user1.get('data/identity/location/0/phone/0/area_code') == '360')
        
        
    def Node_sync_friend(self):
        
        user3 = Node({}, {"name" : "user3"})
        
        self.user2.add('data/friends', user3.get())
        self.assertFalse(len(self.user1.get('data/friends')) == len(self.user2.get('data/friends')))
        
        self.user1.sync(self.user2.get())
        self.assertTrue(len(self.user1.get('data/friends')) == len(self.user2.get('data/friends')))
    
    def forceJoinFriends(self):
        serverObject = YadaServer({}, {"name" : "yada server"})
        
        data = Node({}, { 'name' : 'node 1'})
        
        host = str(uuid4()).replace('-','') + '.com'
        indexer = Node({}, {"name" : host})

        serverObject.add('data/managed_nodes', [data.get(), indexer.get()], True)
        
        self.assertTrue(indexer.matchFriend(data)==None)
        
        serverObject.forceJoinNodes(data, indexer)
        
        self.assertTrue(len(indexer.matchFriend(data))>0)
    
    def Indexer_managedFriendRequest(self):
        
        #setup the server
        serverObject = YadaServer({}, {"name" : "yada server"})
        
        #setup the nodes
        data = Node({}, { 'name' : 'node 1'})
        friend = Node({}, { 'name' : 'node 2'})
        
        #setup the indexer
        host = str(uuid4()).replace('-','') + '.com'
        indexer = Node({}, {"name" : host})

        #make the nodes and indexer hosted on server
        serverObject.add('data/managed_nodes', [data.get(), friend.get(), indexer.get()], True)
        
        #for the sake of the test, just force approved friendships on the nodes and indexer with the server
        serverObject.forceJoinNodes(data, serverObject)
        serverObject.forceJoinNodes(friend, serverObject)
        serverObject.forceJoinNodes(indexer, serverObject)
        
        #also force joining the nodes to the indexer so they will be able to route and retrieve friend requests
        newFriend = serverObject.forceJoinNodes(data, indexer)
        newFriend = serverObject.forceJoinNodes(friend, indexer)
        
        #test to see if any friend requests exists in the indexer already, this should fail
        self.assertEqual([], indexer.get('data/routed_friend_requests'))
        
        nc = NodeCommunicator(serverObject)
        #now we do the actual friend request where we route a request from data to indexer
        newFriend = nc.routeRequestThroughNode(indexer, newFriend['public_key'])
        #we now assert that the friend request was added successfully to the routed_friend_requests array of the indexer
        self.assertTrue(len(indexer.get('data/routed_friend_requests')) > 0)
        
        friendRequests = serverObject.getFriendRequestsFromIndexer(friend, indexer)
        self.assertEqual(friendRequests.keys(),{'friend_requests' : ''}.keys())
        self.assertEqual(friendRequests['friend_requests'][0]['public_key'], newFriend['public_key'])
    
    def addRemoteManager(self):
                
        if not os.getenv('PRODUCTION'):
            host1 = 'localhost'
            host2 = 'localhost'
        else:
            host1 = 'yadaproject.com'
            host2 = 'yadaproject.com'
            
        node1name = str(uuid4())
        node2name = str(uuid4())
        node1 = Node({}, {"name" : node1name})
        node2 = Node({}, {"name" : node2name})
        
 
        #we're trying to recreate the above test but with a remote manager
        #this is the code we need to make remote.
        nc1 = NodeCommunicator(node1)
        nc2 = NodeCommunicator(node2)
         
        #make the node hosted on server
        response = nc1.addManager("%s:8040" % host1)
        response = nc2.addManager("%s:8041" % host2)
        
        #we need to know about node 2 in the manager's friends list before we can request them.
        #we need another update from the manager before we can route a request to them, legally.
        nc1ServerFriend = Node(node1.get('data/friends')[0])
        nc1.updateRelationship(nc1ServerFriend)
        self.assertEqual(nc1ServerFriend.get('data/identity/name'), "node 1")
        
        nc1.requestFriend("%s:8041" % host2)
        
        #request to be friends with the manager's other friend (node 2)
        response = nc1.routeRequestThroughNode(Node(node1.get('data/friends')[1]), json.loads(response[1])['public_key'])
        self.assertEqual(len(nc1.node.get('data/friends')), 3)
        
        #lets pull down our new friend request
        nc2.updateRelationship(Node(node2.get('data/friends')[0]))
        self.assertEqual(len(node2.get('data/friends')[0]['data']['routed_friend_requests']), 1)
        
        #get the request
        request = node2.get('data/friends')[0]['data']['routed_friend_requests'][0]
        
        #accept the friend request
        node2.addFriend(request)
        
        #now we need to push the identity back because we just added a friend
        response = nc1.syncManager()
        response = nc2.syncManager()
        
        #now lets try to sync with the new friend, should automatically go to their manager
        nc2.updateRelationship(Node(node2.get('data/friends')[1]))
        
        response = nc1.syncManager()
        
        #now we verify that we can pull down the information from the new friend
        self.assertEqual(Node(node1.get('data/friends')[2]).get('data/identity/name'), node2name)
        
    def Messaging(self):
                
        if os.getenv('PRODUCTION'):
            host1 = 'localhost:8040'
        else:
            host1 = 'yadaproject.com:8040'
            
        node1name = str(uuid4())
        
        node1 = Node({}, {"name" : node1name})
        
 
        nc1 = NodeCommunicator(node1)
         
        nc1.requestFriend(host1)
        
        uuidSubject = str(uuid4())
        nc1.sendMessage(nc1.node.getFriendPublicKeysArray(), uuidSubject, "message")
        import urllib2
        json = urllib2.urlopen("http://" + host1).read()
        self.assertTrue(uuidSubject in json)

        

if __name__ == '__main__':
    unittest.main()