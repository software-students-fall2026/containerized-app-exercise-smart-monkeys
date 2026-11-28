FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COVERAGE_FILE=/tmp/.coverage

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libegl1 libgl1 libgles2 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && python -c "import ctypes; ctypes.CDLL('libGLESv2.so.2')"

COPY download_model.py ./
RUN python download_model.py

COPY . .

USER 10001:10001

HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "from ml_db import check_connection; raise SystemExit(not check_connection())"

CMD ["python", "-m", "pipeline"]
