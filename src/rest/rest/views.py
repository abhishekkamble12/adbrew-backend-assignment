from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .db import db
from .repositories import TodoRepository
from .validators import validate_todo_payload

todo_repository = TodoRepository(db["todos"])


class TodoListView(APIView):
    """List all TODOs or create a new one.

    Validation errors and database failures are converted to HTTP responses
    by DRF and `rest.exceptions.exception_handler` respectively.
    """

    repository = todo_repository

    def get(self, request):
        todos = self.repository.list_all()
        return Response(todos, status=status.HTTP_200_OK)

    def post(self, request):
        description = validate_todo_payload(request.data)
        todo = self.repository.create(description)
        return Response(todo, status=status.HTTP_201_CREATED)
