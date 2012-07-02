yadapy
======

Quick start instructions: 
1. python setup.py install
2. clone this repo https://github.com/pdxwebdev/yadaproject
3. python server.py hostname:port sqlite.database.path manager
* You now have a server running that can host multiple identities.
* This server must be accessible from the anywhere on the internet.

Now on your client machine:

4. python
. >>> from yadapy.node import Node
. >>> from yadapy.nodecommunicator import NodeCommunicator
. >>> node = Node({}, {"name" : "Node Name"})
 >>> nc = NodeCommunicator(node)
 >>> ncServerFriend = Node(node.get('data/friends')[0])
 >>> nc.updateRelationship(ncServerFriend)
* You now have a friendship with your server from your client machine
* You are also now hosting your identity on this server.
* This relationship can be used for authentication of apps, create new friendships, send messages, host additional identities, etc.



yadapy is a python implementation of the Yada Project Protocol.


What is the Yada Project Protocol?
-
The Yada Project Protocol allows you to host your identity on any device capable of sending, receiving and storing data. Once hosted, you are able to create relationships and communicate with other identities hosted elsewhere on the internet.  


Features / Capabilities:
---
- Identity Management (Kind of like web hosting, only you're hosting identities instead of web sites.)
- O-Auth style authentication
- Automatic account registration
- Integration capabilities enabling multiple web sites to share one social network
- Enhanced control over privacy

Proof of Concepts Completed:
---
- iPhone App
- Generic forum web site demonstrating automatic account registration and login
- Server web site demonstrating identity management / hosting

Road Map:
---
- Testing
- Refactoring
- Gathering User input / feature requests