ML environment and tests

Use Python 3.12 and requirements.txt. The old Python 3.10 Pipenv starter files
have been removed; ML and web dependencies remain independent.

From the repository root, in an activated Python 3.12 virtual environment:
    python -m pip install -r machine-learning-client/requirements.txt
    python machine-learning-client/download_model.py
    cd machine-learning-client
    python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=80

The downloader verifies the versioned model's SHA-256 before saving it to
models/gesture_recognizer.task. Do not commit the generated model.

To build and run the same test environment used in CI, from the repository root:
    docker build -t monkeymoves-ml:test ./machine-learning-client
    docker run --rm --network none monkeymoves-ml:test

The image installs requirements, downloads the verified model at build time and
runs tests as a non-root user. The model is available without a runtime download.
Local models are excluded from the build context so they cannot overwrite it.

The ML workflow enforces at least 80% coverage independently of the web workflow.
It includes a real-model test with a blank JPEG, in addition to mocked gesture
unit tests. This checks model loading and no-hand inference, not accuracy on
real rock/paper/scissors photographs. No camera or live MongoDB is needed.

This is a build/test image: its default command runs pytest and exits. The queue
worker has not merged yet. Its runtime command and full Compose integration will
be added once the worker is available; this does not start a game service.

Local verification: Python 3.12.16 passed all 24 ML tests with 98.46% coverage,
including real model loading and blank-image inference. Black and Pylint passed.
Linux x86_64 dependency resolution passed; Docker execution remains subject to
the hosted ML CI check because this machine has no working Docker engine.
