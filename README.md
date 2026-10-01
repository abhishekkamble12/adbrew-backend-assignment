# Adbrew test: TODO app

My solution to the [Adbrew test](https://github.com/adbrew/adb_test). A React form creates TODOs through a Django API that stores them in MongoDB. All three parts run in Docker through `docker-compose.yml`.

## Running it

You need Docker with Compose v2 (`docker compose`). The old `docker-compose` command works too.

```
git clone https://github.com/abhishekkamble12/adbrew-backend-assignment.git
cd adbrew-backend-assignment
```

Point `ADBREW_CODEBASE_PATH` at the repo's `src` folder. Compose uses it to mount the code and the Mongo data into the containers. Run one of these from the repo root:

```
export ADBREW_CODEBASE_PATH="$(pwd)/src"      # Linux / macOS
$env:ADBREW_CODEBASE_PATH = "$PWD\src"        # Windows PowerShell
set ADBREW_CODEBASE_PATH=%cd%\src             # Windows cmd
```

The variable only lasts for the current terminal, so set it again in a new one.

Then build and start the containers:

```
docker compose build      # first time only, takes a few minutes
docker compose up -d
docker ps                 # should list app (3000), api (8000) and mongo (27017)
```

The UI is at http://localhost:3000 and the API is at http://localhost:8000/todos.

Give it some time on the first start:
- The `app` container runs `yarn install` into the mounted `src/app/node_modules` before compiling. That took me about 15 minutes on Docker Desktop for Windows, where bind mounts are slow. It's ready when `docker logs app` shows `Compiled successfully!`.
- Mongo can also take up to a minute to open its data files. Until then the API answers `503`, and the UI shows an error with a Retry button.

Data is stored in `src/db/` on the host, so it survives `docker compose down`. Delete that folder to start empty.

## What I changed

**Backend.** I implemented `GET /todos` and `POST /todos` on top of MongoDB using pymongo, with no models or serializers, as the task asks.
- The structure is a thin view, a validator, and a repository that does all the Mongo access.
- One exception handler turns every error into the same JSON shape.
- I removed the SQLite config and the Django apps that need a SQL database (admin, auth, sessions, messages), since nothing used them.
- The secret key, debug flag, allowed hosts and CORS origins are now read from env vars. CORS used to allow any origin with credentials; it now only allows the React dev server.
- `/todos` and `/todos/` both work. The task uses `/todos`, and Django's automatic redirect to the trailing-slash URL can't carry a POST body.

**Frontend.** The hardcoded list now comes from the API, and it's fetched again after every create.
- The form clears after a successful submit, keeps the text if the request fails, and is disabled while a request is in flight.
- The list has loading, empty and error states.

**Docker.** The original image didn't build anymore; see [Docker fixes](#docker-fixes).

## How the code is organised

Backend, in `src/rest/rest/`:
- `db.py` creates one `MongoClient` from `MONGO_HOST`, `MONGO_PORT` and `MONGO_DB_NAME`. Its 5 second timeout means a dead database gives a quick 503 instead of a 30 second hang.
- `repositories.py` has `TodoRepository`, the only code that talks to Mongo. It returns plain dicts with the `ObjectId` as a string `id`. It takes the collection as an argument, so the tests pass in an in-memory fake.
- `validators.py` checks the POST body.
- `views.py` has `TodoListView`, which validates, calls the repository and returns the result, with no error handling of its own.
- `exceptions.py` is set as DRF's `EXCEPTION_HANDLER` and builds every error response.

I didn't add a separate service layer. With one entity and no rules beyond validation, it would only forward calls to the repository. If business rules show up, it would go between the view and the repository.

Frontend, in `src/app/src/`:
- `api/todoApi.js` makes all the HTTP calls and turns failed responses into an `ApiError` with a readable message.
- `hooks/useTodos.js` holds the list, loading and error state, and reloads after a create. Each reload aborts the previous request, so a slow old response can't overwrite a newer one.
- `components/TodoForm.js` and `components/TodoList.js` render the form and the list.
- `App.js` connects them.

## API

`GET /todos` returns all TODOs, oldest first:

```
[{"id": "6abe6c9f17de540f535ab6fe", "description": "Learn Docker", "created_at": "2026-10-01T14:22:23.100000Z"}]
```

`POST /todos` with `{"description": "Learn React"}` returns `201` and the created TODO in the same format. The description is trimmed, and must be 1 to 500 characters long after trimming.

Every error has the same shape. `error` is a message the UI can show directly, and `details` holds per-field messages for validation errors (`{}` otherwise):

```
{"error": "This field may not be blank.", "details": {"description": ["This field may not be blank."]}}
```

Status codes:
- `400` for a blank, missing, non-string or too-long description, a body that isn't a JSON object, or malformed JSON;
- `405` for methods other than GET and POST;
- `415` for an unsupported content type;
- `503` when Mongo is unreachable;
- `500` (with a generic message, and the real error only in the logs) for anything unexpected.

## Tests

With the containers running:

```
docker exec api bash -c "cd /src/rest && python manage.py test rest"
docker exec -e CI=true app bash -c "cd /src/app && yarn test --watchAll=false"
docker exec app bash -c "cd /src/app && ./node_modules/.bin/eslint --max-warnings=0 --ext .js src"
```

**Backend tests (18).** They cover the repository and every error case above. Mongo is replaced by a fake collection.

**Frontend tests (8).** They use React Testing Library with a mocked `fetch`. They cover loading the list, creating a TODO and the reload after it, and the validation, server and network errors.

## Docker fixes

`docker-compose.yml` is unchanged. The `Dockerfile` failed to build, so I changed four things:
- **`FROM python:3.8` became `python:3.8-bullseye`.** The unpinned tag now points to Debian 12, which doesn't have `libssl1.1`, and MongoDB 4.4 needs it.
- **apt now uses `archive.debian.org`.** Debian 11 has reached end of life, and the regular mirrors were returning 404s for its packages.
- **Each `apt-get update` is in the same `RUN` as its `apt-get install`.** Otherwise Docker can reuse an old cached package index and try to download versions that no longer exist.
- **I removed `easy_install pip`.** `easy_install` no longer exists, and pip already comes with the Python image.

I also added a `.dockerignore`. The Dockerfile only copies `requirements.txt`, but the build context included `node_modules` and the Mongo data files, about 500 MB.

Pinning an EOL Debian release is fine for local development but not for production. With more time I'd use the official `mongo` image and a current Python base.

## Config

Everything has a default that works with the Docker setup:

| Variable | Default |
|---|---|
| `MONGO_HOST` / `MONGO_PORT` | `mongo` / `27017`, set in the Dockerfile |
| `MONGO_DB_NAME` | `test_db` |
| `DJANGO_SECRET_KEY` | a development-only placeholder |
| `DJANGO_DEBUG` | `true` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` |
| `REACT_APP_API_URL` (frontend) | `http://localhost:8000` |

## Known limitations

- Unknown URLs such as `/foo` still get Django's default 404 page, not the JSON error format.
- There's no update, delete or pagination, since the task didn't ask for them.
