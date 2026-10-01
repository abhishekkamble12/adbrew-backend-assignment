import os

from pymongo import MongoClient
from pymongo.database import Database

MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", "27017"))
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "test_db")

# One client per process (it pools connections). The short timeout makes requests
# fail with a 503 after 5s when Mongo is down, instead of hanging for the default 30s.
client: MongoClient = MongoClient(
    host=MONGO_HOST,
    port=MONGO_PORT,
    serverSelectionTimeoutMS=5000,
    tz_aware=True,
)
db: Database = client[MONGO_DB_NAME]
