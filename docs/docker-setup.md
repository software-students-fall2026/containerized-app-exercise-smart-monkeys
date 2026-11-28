# Flask container setup

Compose starts Flask and MongoDB. The ML worker will be added after it merges;
this is not yet the complete three-service game. Current routes are `/health`
and `POST /api/rounds`.

## Start and stop

Install/start Docker with Compose v2 or later. Copy `.env.example` to `.env`
once, preserving any existing settings. From the repository root:

```bash
docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
docker compose ps
```

Check `http://localhost:5000/health`. Set `WEB_PORT=5001` in `.env` if port 5000
is busy. `MONGO_DB` is a database name, not a URI; Compose generates `MONGO_URI`.
Shell environment variables override `.env` values.

Flask waits for MongoDB's ping health check, then serves on localhost only.
MongoDB has no published host port. Flask uses Python 3.12 and requirements.txt,
runs as UID/GID 10001, and uses the development server without debug/reload.
This setup is for the local class demo, not public hosting.

```bash
docker compose logs --tail=100 web-app db
docker compose down
```

`down` preserves `mongo-data`; `down --volumes` deletes its data. Keep the same
Compose project name to reuse the volume. Stop any old manually started web
containers if they occupy port 5000; their data is not automatically migrated.

## Tests

```bash
docker compose run --rm --no-deps -e COVERAGE_FILE=/tmp/.coverage web-app \
  python -m pytest -p no:cacheprovider --cov=. \
  --cov-report=term-missing --cov-fail-under=80
```

`web-ci.yml` checks coverage, uploads and database outages. `compose-ci.yml`
checks this configuration, then recreates containers and verifies persisted data.
It uses a separate test project/database and cleans its resources afterwards.

The upload smoke test uses a synthetic JPEG, not a real hand gesture. Run it
only against a disposable database with the worker stopped. Its `MONGO_URI`
must match Flask's database; `BASE_URL` defaults to `http://127.0.0.1:5000`.
Both smoke scripts remove only their own test records. Container execution must
pass in GitHub Actions before merge; local Python checks alone are insufficient.
