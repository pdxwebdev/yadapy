yadapy
======
Pull Requests Very Welcome
---

This is an open project that welcomes any and all contributors, for example:
http://spencermoran.me/2013/08/13/open-source-on-github-your-first-contribution/

Quick start instructions: 
https://github.com/pdxwebdev/yadapy/wiki/Quick-Start-Instructions


yadapy is a python implementation of the Yada Project Protocol.


The purpose of this identity management framework is to more accurately represent real-life social interaction. What we currently know as “social networking” is a square forced through the circular hole of, “every website has its own social network and every social network belongs to its containing website.”

The mission is to break this model. In doing so, privacy is improved, ownership of data is granted, and information sharing is promoted, ultimately benefiting site owners in ways outlined in the features section below.

Consumer Features:
-	Graph analysis
o	Spot fake identities by analyzing their social graph, automatically.
-	Take your friends with you
o	Users want to leave walled gardens like Facebook and take their friends with them.  Interacting with the same contacts in multiple environments/situations is an extremely powerful social component the web is missing.
-	Automatic friend grouping
o	Express things to a few of your friends without having to manually add them to “circles” or groups. 
o	Using tags and where the communication is written, users will automatically reach the correct audience. 
-	All of your identity data (name, address, etc.) is stored on your phone
o	Your phone is a virtualized version of your identity.
o	All of your relationships (friends) are part of that identity 
o	Contact information updates automatically based on friend activity

Technical Features:
-	Users are identified by their relationships IDs rather than a single ID number.
o	Harder to spam and easier to block spammers
o	The source of any communication can be located in your social graph
-	Relationships with different entity types: 
o	People (friends)
o	Websites / people indexers
-	Users will exchange relationship information to authenticate with a site or app. 
-	Web sites are one form of “glue” for users, enabling the knowledge of who has a mutual friend and to provide context for communication. Users will always request other friends through a web site or tag.
o	Symbols (tags)
-	Another form of “glue”, answering the question commonly asked, “how do you two know each other?”
-	Create or add context for relationships, posts, comments, etc.


Proof of Concepts Completed:
---
- iPhone App - http://itunes.apple.com/us/app/yada-project/id426657120?mt=8&ls=1#
- Generic forum web site demonstrating automatic account registration and login
- Server web site demonstrating identity management / hosting

Road Map:
---
- Testing
- Refactoring
- Gathering User input / feature requests
