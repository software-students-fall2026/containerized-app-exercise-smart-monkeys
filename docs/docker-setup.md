# Flask container setup

This step packages the merged Flask backend and checks it against MongoDB.
The ML worker and full three-service Compose stack will be added separately.

## Image and configuration

- Build context: `web-app/`; base: `python:3.12-slim-bookworm`.
- Dependencies come from Rwan's pinned `requirements.txt`; no Pipenv is used.
- `app.py` provides the Flask application. It listens on `0.0.0.0:5000` inside
  the container, with debugging and automatic reload disabled.
- Processes run as UID/GID 10001. Local environment files and caches are excluded
  by `.dockerignore`; provide `MONGO_URI` at runtime rather than baking it in.
- The image health check calls `/health`. This endpoint returns 200 when MongoDB
  is reachable and 503 when unavailable. An unhealthy status alone does not
  automatically restart the container.
- The Flask development server is for the local class demo, not public hosting.
- The image includes the existing subsystem tests and development dependencies so
  CI can test the same image. Splitting runtime/dev requirements belongs to the
  dependency owner and is not required for this step.

## Run locally

Install/start a Docker engine first. From the repository root:

```bash
docker build -t monkeymoves-web:dev ./web-app
docker network create monkeymoves-web-dev
docker volume create monkeymoves-web-dev-data
docker run -d --name monkeymoves-db-dev --network monkeymoves-web-dev \
  --network-alias db -v monkeymoves-web-dev-data:/data/db mongo:8.0.16
docker run -d --name monkeymoves-web-dev --network monkeymoves-web-dev \
  -p 127.0.0.1:5000:5000 \
  -e MONGO_URI=mongodb://db:27017/monkeymoves \
  monkeymoves-web:dev
```

Wait for `docker ps` to show the web container as healthy, then check
`http://localhost:5000/health`. MongoDB has no published host port. The named volume
retains its data when the containers are removed. If localhost port 5000 is busy,
change only the host port in the mapping (for example `127.0.0.1:5001:5000`).

Current backend routes are `/health` and `POST /api/rounds`. The root page,
result/history endpoints and ML processing are separate teammates' work; this
container PR does not claim a playable game yet.

View logs with `docker logs monkeymoves-web-dev`. To stop and remove these two
containers and their network, preserving the database volume:

```bash
docker rm -f monkeymoves-web-dev monkeymoves-db-dev
docker network rm monkeymoves-web-dev
```

## Tests and CI

`.github/workflows/web-ci.yml` runs on PRs to main and pushes to main. It builds
the actual web image, runs the existing web tests with at least 80% coverage
(excluding test files through `.coveragerc`), and checks the smoke script style.
It then starts a private MongoDB/web network, waits for healthy status, checks
non-root execution and performs a real HTTP JPEG upload. The smoke test queries
MongoDB to verify the pending record and exact JPEG bytes, then deletes only its
own record. Finally CI stops MongoDB and checks that `/health` returns 503.
Test containers and their anonymous volumes are removed even after a failure.

`integration/web_smoke_test.py` uses a generated solid-color JPEG, not a webcam
photo. It validates transport and storage, not hand recognition. Run it only
against a disposable test database with the ML worker stopped, since it expects
the uploaded round to remain pending. `MONGO_URI` must target the same database
as the Flask server; `BASE_URL` defaults to `http://127.0.0.1:5000`.

To run the unit tests in the image:

```bash
docker run --rm -e COVERAGE_FILE=/tmp/.coverage monkeymoves-web:dev \
  python -m pytest -p no:cacheprovider --cov=. \
  --cov-report=term-missing --cov-fail-under=80
```

A green hosted web CI run and teammate review are required before merging.
Local Python tests alone do not establish that a Docker image builds and runs.

## Local verification (November 26, 2026)

- Python 3.12.16: all 16 existing web unit tests passed; application/database
  coverage was 95.52%, above the 80% gate.
- A temporary native MongoDB 8.0.16 and the real Flask CLI server passed the
  live smoke test: healthy response, rejected missing upload, accepted JPEG,
  matching stored bytes and removal of the smoke test's own record.
- Stopping that MongoDB process produced the expected HTTP 503 response.
- Black, Pylint (10/10), Actionlint and whitespace checks passed for the changes.
  Actionlint ran without the optional external ShellCheck tool.
- The official Python and MongoDB image tags were verified to provide Linux
  amd64 and arm64 manifests. No image was built locally: this machine has no
  working Docker engine. The PR's web workflow must pass before merging.
