from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .db import db
from .repositories import TodoRepository
from .validators import validate_todo_payload

todo_repository = TodoRepository(db["todos"])


class TodoListView(APIView):
    """List all TODOs or create a new one.

    Errors are not handled here: validation and database exceptions propagate
    to `rest.exceptions.exception_handler`, which builds the error response.
    """

    repository = todo_repository

    def get(self, request: Request) -> Response:
        todos = self.repository.list_all()
        return Response(todos, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        description = validate_todo_payload(request.data)
        todo = self.repository.create(description)
        return Response(todo, status=status.HTTP_201_CREATED)
