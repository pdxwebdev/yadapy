import json, logging, os, copy
from uuid import uuid4
from yadapy.lib.crypt import decrypt, encrypt
from pymongo import Connection
from base64 import b64encode, b64decode
from yadapy.db.mongodb.node import Node
from yadapy.db.mongodb.manager import YadaServer
from yadapy.managercommunicator import ManagerCommunicator
from yadapy.db.mongodb.lib.jsonencoder import MongoEncoder
from node import MongoApi


class MongoApiManager(MongoApi):
    
    def __init__(self, nodeComm=None):
        self.nodeComm = nodeComm
        
    def postRoutedFriendRequest(self, data, decrypted):
    
        node = Node(public_key=data['public_key'])
        node.set('data/friends', node.getFriends(), True)
        nodeComm = ManagerCommunicator(node)
        yadaserver = YadaServer()
        serverFriend = Node(node.getFriend(yadaserver.matchFriend(node)['public_key']))
        friendTest = Node.db.friends.find({'public_key': data['public_key'], 'friend.routed_public_key': decrypted['routed_public_key']})
        if friendTest.count() == 0:
            nodeComm.routeRequestThroughNode(serverFriend, decrypted['routed_public_key'], decrypted.get('name', decrypted['routed_public_key']), decrypted.get('avatar', ''))
            Node.db.friends.update({'public_key': data['public_key'], 'friend.routed_public_key': decrypted['routed_public_key']}, {"$set": {"friend.subscribed": "*"}})
            friend = Node.db.friends.find({'public_key': data['public_key'], 'friend.routed_public_key': decrypted['routed_public_key']})
            return {"status": "request sent", "friend": friend[0]['friend']}
        return {"status": "already friends"}