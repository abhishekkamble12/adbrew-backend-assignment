# Run with: docker exec api bash -c "cd /src/rest && python manage.py test rest"
# FakeCollection stands in for Mongo, so no database is needed.
from types import SimpleNamespace
from unittest import mock

from bson import ObjectId
from django.test import SimpleTestCase
from pymongo.errors import ServerSelectionTimeoutError
from rest_framework.test import APIClient

from .exceptions import DATABASE_UNAVAILABLE_MESSAGE, INTERNAL_ERROR_MESSAGE
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

    def assertErrorResponse(self, response, status_code, message=None, details=None):
        """Every error must use the shape {"error": str, "details": dict}."""
        self.assertEqual(response.status_code, status_code)
        body = response.json()
        self.assertEqual(set(body), {"error", "details"})
        self.assertIsInstance(body["error"], str)
        self.assertIsInstance(body["details"], dict)
        if message is not None:
            self.assertEqual(body["error"], message)
        if details is not None:
            self.assertEqual(body["details"], details)

    def test_post_rejects_empty_description(self):
        response = self.client.post("/todos", {"description": ""}, format="json")

        self.assertErrorResponse(
            response, 400,
            message="This field may not be blank.",
            details={"description": ["This field may not be blank."]},
        )

    def test_post_rejects_whitespace_only_description(self):
        response = self.client.post("/todos", {"description": "   "}, format="json")

        self.assertErrorResponse(response, 400, message="This field may not be blank.")

    def test_post_rejects_missing_description(self):
        response = self.client.post("/todos", {}, format="json")

        self.assertErrorResponse(response, 400, message="This field is required and must be a string.")

    def test_post_rejects_non_string_description(self):
        response = self.client.post("/todos", {"description": 42}, format="json")

        self.assertErrorResponse(response, 400, message="This field is required and must be a string.")

    def test_post_rejects_too_long_description(self):
        response = self.client.post("/todos", {"description": "a" * 501}, format="json")

        self.assertErrorResponse(response, 400, message="Must be at most 500 characters.")

    def test_post_accepts_description_at_max_length(self):
        response = self.client.post("/todos", {"description": "a" * 500}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_post_rejects_non_object_body(self):
        response = self.client.post("/todos", ["not", "an", "object"], format="json")

        self.assertErrorResponse(
            response, 400,
            message="Expected a JSON object.",
            details={"non_field_errors": ["Expected a JSON object."]},
        )

    def test_post_rejects_invalid_json(self):
        response = self.client.post("/todos", "{bad json", content_type="application/json")

        self.assertErrorResponse(response, 400, details={})
        self.assertIn("JSON parse error", response.json()["error"])

    def test_unsupported_methods_return_405(self):
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertErrorResponse(method("/todos"), 405, details={})

    def test_get_returns_503_when_database_is_down(self):
        failing = mock.Mock()
        failing.list_all.side_effect = ServerSelectionTimeoutError("mongo down")

        with mock.patch.object(TodoListView, "repository", failing), \
                self.assertLogs("rest.exceptions", level="ERROR"):
            response = self.client.get("/todos")

        self.assertErrorResponse(response, 503, message=DATABASE_UNAVAILABLE_MESSAGE, details={})

    def test_post_returns_503_when_database_is_down(self):
        failing = mock.Mock()
        failing.create.side_effect = ServerSelectionTimeoutError("mongo down")

        with mock.patch.object(TodoListView, "repository", failing), \
                self.assertLogs("rest.exceptions", level="ERROR"):
            response = self.client.post("/todos", {"description": "x"}, format="json")

        self.assertErrorResponse(response, 503, message=DATABASE_UNAVAILABLE_MESSAGE)

    def test_unexpected_error_returns_generic_500(self):
        failing = mock.Mock()
        failing.list_all.side_effect = KeyError("secret internal detail")

        with mock.patch.object(TodoListView, "repository", failing), \
                self.assertLogs("rest.exceptions", level="ERROR"):
            response = self.client.get("/todos")

        self.assertErrorResponse(response, 500, message=INTERNAL_ERROR_MESSAGE, details={})
        self.assertNotIn("secret", response.content.decode())
