FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COVERAGE_FILE=/tmp/.coverage

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libegl1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check

COPY download_model.py ./
RUN python download_model.py

COPY . .

USER 10001:10001

CMD ["python", "-m", "pytest", "-p", "no:cacheprovider", "--cov=.", "--cov-report=term-missing", "--cov-fail-under=80"]
