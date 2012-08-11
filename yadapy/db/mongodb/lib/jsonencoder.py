from json import JSONEncoder
try:
    from pymongo.objectid import ObjectId
except:
    from bson.objectid import ObjectId

class MongoEncoder(JSONEncoder):      
    def iterencode(self, o, markers=None):
        if isinstance(o, ObjectId):
            return '""'
        else:
            return JSONEncoder._iterencode(self, o, markers)