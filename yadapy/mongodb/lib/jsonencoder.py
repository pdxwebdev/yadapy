from json import JSONEncoder
from pymongo.objectid import ObjectId

class JsonEncoder(JSONEncoder):      
    def _iterencode(self, o, markers=None):
        if isinstance(o, ObjectId):
            return '""'
        else:
            return JSONEncoder._iterencode(self, o, markers)