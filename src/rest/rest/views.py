from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .db import db
from .repositories import TodoRepository
from .validators import validate_todo_payload

todo_repository = TodoRepository(db["todos"])


class TodoListView(APIView):
    # No try/except here: errors propagate to rest.exceptions.exception_handler.

    repository = todo_repository

    def get(self, request: Request) -> Response:
        todos = self.repository.list_all()
        return Response(todos, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        description = validate_todo_payload(request.data)
        todo = self.repository.create(description)
        return Response(todo, status=status.HTTP_201_CREATED)
