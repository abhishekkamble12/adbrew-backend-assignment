# Adbrew Test: TODO app (Django + MongoDB + React)

My solution to the [Adbrew test](https://github.com/adbrew/adb_test). It's a TODO list where a React form creates TODOs through a Django REST API that stores them in MongoDB. All three parts run in Docker containers.

- [Setup](#setup)
- [What I built](#what-i-built)
- [Architecture](#architecture)
- [API contract](#api-contract)
- [Running the tests](#running-the-tests)
- [Docker changes](#docker-changes)
- [Configuration](#configuration)
- [Known issues and limitations](#known-issues-and-limitations)

## Setup

Requirements: Docker with Docker Compose v2 (`docker compose`). The older `docker-compose` v1 command also works.

1. Clone the repository and change into it:

   ```
   git clone https://github.com/abhishekkamble12/adbrew-backend-assignment.git
   cd adbrew-backend-assignment
   ```

2. Point `ADBREW_CODEBASE_PATH` at the repository's `src` directory. `docker-compose.yml` uses it to mount the source code and Mongo data into the containers. Run the command for your shell from the repository root:

   | Shell | Command |
   |---|---|
   | Linux / macOS (bash, zsh) | `export ADBREW_CODEBASE_PATH="$(pwd)/src"` |
   | Windows PowerShell | `$env:ADBREW_CODEBASE_PATH = "$PWD\src"` |
   | Windows cmd | `set ADBREW_CODEBASE_PATH=%cd%\src` |

   The variable only lasts for the current terminal session. Set it again in any new terminal before running `docker compose`.

3. Build the images. This is only needed the first time, or after changing the `Dockerfile`, and it takes several minutes:

   ```
   docker compose build
   ```

4. Start the containers:

   ```
   docker compose up -d
   ```

5. Check that all three containers are up:

   ```
   docker ps
   ```

   You should see `app` (port 3000), `api` (port 8000) and `mongo` (port 27017).

6. Wait for the services to be ready:
   - **app:** the first start runs `yarn install` into the bind-mounted `src/app/node_modules`. That takes a few minutes on Linux/macOS, but took about 15 minutes on Docker Desktop for Windows, where bind mounts are slow. Later starts are much faster. It's ready when `docker logs app` shows `Compiled successfully!`.
   - **mongo:** it can take up to about a minute to accept connections, especially on Windows (see [Known issues](#known-issues-and-limitations)). Until it does, the API returns `503`.

7. Open http://localhost:3000 for the UI. The API is at http://localhost:8000/todos.

Useful commands:

| Action | Command |
|---|---|
| Follow a container's logs | `docker logs -f --tail=100 api` (or `app` / `mongo`) |
| Open a shell in a container | `docker exec -it api bash` |
| Stop everything | `docker compose down` |

TODOs are stored in `src/db/` on the host, so they survive `docker compose down` / `up`. Delete that directory to start from an empty database.

## What I built

The task was:
1. Submitting the form creates a TODO via `POST /todos`.
2. The list shows TODOs from `GET /todos` instead of hardcoded ones.
3. The list refreshes after each submit.

The constraints were: React hooks only, and no Django models, serializers or SQLite.

**Backend:**
- `GET /todos` and `POST /todos` are implemented on top of the existing Mongo `db` instance.
- Input is validated: the description must be a non-blank string of at most 500 characters, and surrounding whitespace is trimmed.
- Every error, including validation, malformed JSON, wrong HTTP method, database unavailable and unexpected exceptions, returns the same JSON shape with the correct status code. Tracebacks are never sent to the client.
- SQLite and the Django apps that need a relational database (admin, auth, sessions, ...) are removed, because nothing used them.
- The secret key, debug flag, allowed hosts and CORS origins are read from environment variables. CORS is restricted to the React dev server; previously it allowed any origin, with credentials.
- Both `/todos` and `/todos/` work. Without this, a `POST /todos` (the URL in the task) would fail on Django's slash redirect, because a redirect can't carry a POST body.

**Frontend:**
- The hardcoded list is replaced with data from the API.
- The list reloads from the backend after every successful create.
- The form clears after a successful submit, keeps the text if the submit fails, and disables the button while a request is in progress or the input is blank.
- The list has loading, empty and error states, and a Retry button.

**Docker:** the original image no longer builds. See [Docker changes](#docker-changes).

## Architecture

```
React (localhost:3000)                      Django (localhost:8000)                 MongoDB
------------------------------------        -------------------------------------   ---------------
TodoForm / TodoList  (components/)          views.py       TodoListView (HTTP only)
        |                                           |
useTodos            (hooks/useTodos.js) --> validators.py  validate_todo_payload
        |                                           |
todoApi             (api/todoApi.js)  HTTP  repositories.py TodoRepository  ---------> test_db.todos
                                                    |
                                            exceptions.py  turns every error into one JSON shape
```

**Backend** (`src/rest/rest/`):

| File | Responsibility |
|---|---|
| `db.py` | Creates the one shared `MongoClient` from `MONGO_HOST`, `MONGO_PORT` and `MONGO_DB_NAME`. It has a 5s server-selection timeout, so requests fail fast when Mongo is down instead of hanging for 30s. |
| `repositories.py` | `TodoRepository` is the only code that talks to Mongo. It turns Mongo documents into plain dicts (`ObjectId` becomes a string `id`). The collection is passed in, so tests can use an in-memory fake. |
| `validators.py` | Checks the POST body and returns the cleaned description. It raises DRF's `ValidationError` if the input is invalid. |
| `views.py` | `TodoListView` is kept thin: it validates, calls the repository and returns a response. It contains no error handling. |
| `exceptions.py` | The project-wide DRF exception handler. It turns every error into `{"error", "details"}`: `PyMongoError` becomes a 503, anything unexpected becomes a logged, generic 500. |

There is no separate "service" layer. With one entity and no business rules beyond validation, it would only pass calls through to the repository. To add one later, put it between the view and the repository.

**Frontend** (`src/app/src/`):

| File | Responsibility |
|---|---|
| `api/todoApi.js` | All HTTP calls. It reads the base URL from `REACT_APP_API_URL` (default `http://localhost:8000`) and turns error responses and network failures into an `ApiError` with a readable message. |
| `hooks/useTodos.js` | Holds the list, loading and error state. It loads on mount and reloads after a create. Each load cancels the previous in-flight request, so an older, slower response can't overwrite a newer one, and no state is updated after unmount. |
| `components/TodoForm.js` | Holds the input and submit state, and shows submit errors inline. |
| `components/TodoList.js` | Renders the loading, error (with Retry), empty and list states. |
| `App.js` | Connects the hook to the two components. |

## API contract

### `GET /todos`

Returns all TODOs, oldest first.

```
$ curl http://localhost:8000/todos
[
  {"id": "6abe6c9f17de540f535ab6fe", "description": "Learn Docker", "created_at": "2026-10-01T14:22:23.100000Z"}
]
```

### `POST /todos`

The body is `{"description": "<1-500 characters>"}`. Surrounding whitespace is trimmed. It returns `201` with the created TODO.

```
$ curl -X POST http://localhost:8000/todos -H "Content-Type: application/json" -d '{"description": "Learn React"}'
{"id": "6abe6c9f17de540f535ab6ff", "description": "Learn React", "created_at": "2026-10-01T14:22:23.218000Z"}
```

### Errors

Every error response has the same shape. `error` is a message the UI can show as-is. `details` holds per-field messages for validation errors and is `{}` otherwise.

```
{"error": "This field may not be blank.", "details": {"description": ["This field may not be blank."]}}
```

| Case | Status | `error` |
|---|---|---|
| Empty or whitespace-only description | 400 | `This field may not be blank.` |
| Missing or non-string description | 400 | `This field is required and must be a string.` |
| Description over 500 characters | 400 | `Must be at most 500 characters.` |
| Body is not a JSON object | 400 | `Expected a JSON object.` |
| Malformed JSON | 400 | `JSON parse error - ...` |
| Method other than GET/POST | 405 | `Method "PUT" not allowed.` |
| Unsupported `Content-Type` | 415 | `Unsupported media type "..." in request.` |
| MongoDB unreachable | 503 | `The database is currently unavailable. Please try again later.` |
| Any unexpected server error | 500 | `An unexpected error occurred.` (details are only logged) |

## Running the tests

Run these with the containers up:

```
# Backend: Django test runner, 18 tests. No running Mongo needed; an in-memory fake collection is used.
docker exec api bash -c "cd /src/rest && python manage.py test rest"

# Frontend: Jest + React Testing Library, 8 tests. fetch is mocked.
docker exec -e CI=true app bash -c "cd /src/app && yarn test --watchAll=false"

# Lint
docker exec app bash -c "cd /src/app && ./node_modules/.bin/eslint --max-warnings=0 --ext .js src"
```

The backend tests cover:
- the repository: create, ordering, and the empty case;
- every error case in the table above;
- that a 500 response doesn't leak exception details.

The frontend tests cover:
- loading and rendering the list, and the empty state;
- create followed by a reload;
- validation, server, non-JSON and network errors;
- Retry, and the disabled button for blank input.

## Docker changes

`docker-compose.yml` is unchanged. In the `Dockerfile`, `docker-compose build` failed on the original version, for three reasons:

| Change | Why |
|---|---|
| `FROM python:3.8` changed to `FROM python:3.8-bullseye` | The floating `python:3.8` tag now resolves to Debian 12 (bookworm). The MongoDB 4.4 packages depend on `libssl1.1`, which bookworm doesn't have, so `apt-get install mongodb-org` failed. Debian 11 (bullseye) still has `libssl1.1`. Pinning the release also stops the base image changing underneath the build. |
| Added `RUN echo "deb http://archive.debian.org/debian bullseye main" > /etc/apt/sources.list` | Bullseye has reached end of life, and its packages are being moved off the regular mirrors. Fetching from `deb.debian.org` / `bullseye-security` returned 404s. `archive.debian.org` is the permanent home for EOL releases. |
| Each `apt-get update` merged with the `apt-get install` after it, in one `RUN` | As separate layers, Docker can reuse an old cached `apt-get update` with a newer `install` step, which then asks for package versions that no longer exist. One layer keeps the index and the install consistent. |
| Removed `RUN easy_install pip` | `easy_install` was removed from setuptools, so the step fails. pip already ships with the official Python image. |

Trade-off: pinning to an EOL Debian release with no security updates is acceptable for a local development setup, not for production. The proper fix is to use the official `mongo` image for the database service and a current Python base image for the others. I didn't do that, to avoid changing the provided setup more than necessary.

## Configuration

All of these are optional. The defaults suit the local Docker setup.

| Variable | Used by | Default |
|---|---|---|
| `MONGO_HOST`, `MONGO_PORT` | api | `mongo`, `27017` (set in the `Dockerfile`) |
| `MONGO_DB_NAME` | api | `test_db` |
| `DJANGO_SECRET_KEY` | api | a development-only placeholder |
| `DJANGO_DEBUG` | api | `true` |
| `DJANGO_ALLOWED_HOSTS` | api | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | api | `http://localhost:3000,http://127.0.0.1:3000` |
| `REACT_APP_API_URL` | app | `http://localhost:8000` |

## Known issues and limitations

- **Mongo cold start:** `mongo` stores its data in a bind mount (`src/db/`). On Docker Desktop for Windows, bind mounts are slow, and WiredTiger took about 60 seconds to open the data files after `docker compose up`. During that time the API returns `503` and the UI shows the error with a Retry button. This is expected; wait and retry.
- **Error format outside the API:** the error format covers every request handled by the API view. URLs that don't exist (for example `/foo`) still get Django's default 404 page.
- **Scope:** there is no pagination, update or delete, because the task didn't ask for them. A new operation would be a repository method, a validator if it takes input, and a view method. The error handling and frontend API module are shared, so they need no changes.
