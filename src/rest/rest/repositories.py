"""Data access layer for TODO items.

Keeps all MongoDB-specific details (collection access, ObjectId, document
shape) out of the HTTP layer. Views only deal with plain dicts.
"""
from datetime import datetime, timezone

from pymongo import ASCENDING


class TodoRepository:
    """Persists and retrieves TODO items from a MongoDB collection.

    The collection is injected rather than created here, which keeps the class
    independent of connection setup and lets tests pass in a fake collection.
    """

    def __init__(self, collection):
        self._collection = collection

    def list_all(self):
        """Return all TODOs, oldest first."""
        cursor = self._collection.find().sort("created_at", ASCENDING)
        return [self._to_dict(document) for document in cursor]

    def create(self, description):
        """Insert a new TODO and return it in its serialized form."""
        document = {
            "description": description,
            "created_at": self._utc_now_millis(),
        }
        result = self._collection.insert_one(document)
        return self._to_dict({**document, "_id": result.inserted_id})

    @staticmethod
    def _utc_now_millis():
        """Current UTC time truncated to milliseconds.

        BSON dates only store milliseconds, so truncating up front keeps the
        timestamp returned on create identical to the one later read back.
        """
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=now.microsecond // 1000 * 1000)

    @staticmethod
    def _to_dict(document):
        """Convert a Mongo document into a JSON-friendly dict.

        ObjectId is not JSON serializable, so it is exposed as a string `id`.
        """
        return {
            "id": str(document["_id"]),
            "description": document.get("description", ""),
            "created_at": document.get("created_at"),
        }
