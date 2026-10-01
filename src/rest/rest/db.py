"""MongoDB connection setup.

A single MongoClient is shared by the whole process: pymongo clients are
thread-safe and maintain their own connection pool, so creating one per
request would be wasteful.
"""
import os

from pymongo import MongoClient

MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", "27017"))
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "test_db")

# The client connects lazily, so importing this module never blocks on Mongo.
# A short server selection timeout makes requests fail fast (and surface as a
# 503) instead of hanging for pymongo's default 30s when Mongo is down.
client = MongoClient(
    host=MONGO_HOST,
    port=MONGO_PORT,
    serverSelectionTimeoutMS=5000,
    tz_aware=True,
)
db = client[MONGO_DB_NAME]
