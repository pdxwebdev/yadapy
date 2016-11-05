import unittest
from node import Identity, NewNode, NewRelation, NewRelationship

class TestMongoNode(unittest.TestCase):

    def test_relationship_identifier(self):
        pass

    def test_shared_secret(self):
        pass

    def test_identity(self):
        assert Identity('foo', 'http://imgur.com')

    def test_new_node(self):
        identity = Identity('foo', 'http://imgur.com')
        assert NewNode(identity)

    def test_relation(self):
        identity = Identity('foo', 'http://imgur.com')
        assert NewRelation(identity)

    def test_relationship(self):
        identity = Identity('foo', 'http://imgur.com')
        relation1 = NewRelation(identity)

        identity = Identity('bar', 'http://imgur.com')
        relation2 = NewRelation(identity)

        assert NewRelationship(relation1, relation2)

    def test_add_relation(self):
        identity = Identity('foo', 'http://imgur.com')
        node = NewNode(identity)

        identity = Identity('bar', 'http://imgur.com')
        node = NewNode(identity)
        relation = NewRelation(node)

        node.addRelation(relation)
        assert node.relations