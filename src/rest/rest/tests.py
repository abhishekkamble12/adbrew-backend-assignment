"""Tests for the TODO API.

Run inside the api container:  cd /src/rest && python manage.py test rest
A small in-memory fake stands in for the Mongo collection, so these tests
need no running database.
"""
from types import SimpleNamespace
from unittest import mock

from bson import ObjectId
from django.test import SimpleTestCase
from pymongo.errors import ServerSelectionTimeoutError
from rest_framework.test import APIClient

from .repositories import TodoRepository
from .views import TodoListView


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda doc: doc[key], reverse=direction < 0))


class FakeCollection:
    def __init__(self):
        self.documents = []

    def find(self):
        return FakeCursor(dict(doc) for doc in self.documents)

    def insert_one(self, document):
        stored = {**document, "_id": ObjectId()}
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])


class TodoRepositoryTests(SimpleTestCase):
    def setUp(self):
        self.collection = FakeCollection()
        self.repository = TodoRepository(self.collection)

    def test_create_persists_and_returns_serialized_todo(self):
        todo = self.repository.create("Learn Docker")

        self.assertEqual(len(self.collection.documents), 1)
        self.assertEqual(todo["description"], "Learn Docker")
        self.assertEqual(todo["id"], str(self.collection.documents[0]["_id"]))
        self.assertIsNotNone(todo["created_at"])

    def test_list_all_returns_todos_oldest_first(self):
        self.repository.create("first")
        self.repository.create("second")

        descriptions = [todo["description"] for todo in self.repository.list_all()]

        self.assertEqual(descriptions, ["first", "second"])

    def test_list_all_is_empty_without_todos(self):
        self.assertEqual(self.repository.list_all(), [])


class TodoListViewTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        repository = TodoRepository(FakeCollection())
        patcher = mock.patch.object(TodoListView, "repository", repository)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_returns_empty_list(self):
        response = self.client.get("/todos")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_post_creates_todo_and_get_returns_it(self):
        response = self.client.post("/todos", {"description": "  Learn React  "}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["description"], "Learn React")

        todos = self.client.get("/todos").json()
        self.assertEqual([todo["description"] for todo in todos], ["Learn React"])

    def test_trailing_slash_is_accepted(self):
        response = self.client.post("/todos/", {"description": "x"}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_post_rejects_missing_description(self):
        response = self.client.post("/todos", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("description", response.json())

    def test_post_rejects_blank_description(self):
        response = self.client.post("/todos", {"description": "   "}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_post_rejects_non_string_description(self):
        response = self.client.post("/todos", {"description": 42}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_post_rejects_too_long_description(self):
        response = self.client.post("/todos", {"description": "a" * 501}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_post_rejects_non_object_body(self):
        response = self.client.post("/todos", ["not", "an", "object"], format="json")

        self.assertEqual(response.status_code, 400)

    def test_database_failure_returns_503(self):
        failing = mock.Mock()
        failing.list_all.side_effect = ServerSelectionTimeoutError("mongo down")

        with mock.patch.object(TodoListView, "repository", failing), \
                self.assertLogs("rest.exceptions", level="ERROR"):
            response = self.client.get("/todos")

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json())
