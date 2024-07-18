from pymongo import MongoClient
import os
class Database:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.labels_collection = self.get_collection('labelsInfo')

    def get_collection(self, collection_name):
        return self.db[collection_name]

db = Database(os.environ.get('MONGO_URI'), 
'labels')
