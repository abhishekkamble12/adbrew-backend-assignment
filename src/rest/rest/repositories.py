from datetime import datetime, timezone
from typing import Any, Dict, List

from pymongo import ASCENDING
from pymongo.collection import Collection

Todo = Dict[str, Any]


class TodoRepository:
    """All Mongo access for todos. Takes the collection as an argument so tests can pass a fake."""

    def __init__(self, collection: Collection) -> None:
        self._collection = collection

    def list_all(self) -> List[Todo]:
        cursor = self._collection.find().sort("created_at", ASCENDING)
        return [self._to_dict(document) for document in cursor]

    def create(self, description: str) -> Todo:
        document = {
            "description": description,
            "created_at": self._utc_now_millis(),
        }
        result = self._collection.insert_one(document)
        return self._to_dict({**document, "_id": result.inserted_id})

    @staticmethod
    def _utc_now_millis() -> datetime:
        # BSON stores milliseconds only; truncating here keeps the POST response
        # identical to what a later GET returns.
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=now.microsecond // 1000 * 1000)

    @staticmethod
    def _to_dict(document: Dict[str, Any]) -> Todo:
        # ObjectId isn't JSON serializable, so expose it as a string id.
        return {
            "id": str(document["_id"]),
            "description": document.get("description", ""),
            "created_at": document.get("created_at"),
        }
