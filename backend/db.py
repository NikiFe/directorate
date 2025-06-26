from pymongo import MongoClient
from pymongo.database import Database
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/directorate")
_client = MongoClient(MONGO_URI)
db: Database = _client.get_default_database()
