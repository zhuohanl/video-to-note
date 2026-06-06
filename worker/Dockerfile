FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY apps/api apps/api
COPY packages packages
COPY worker worker

RUN uv sync --frozen --only-group dev

CMD ["uv", "run", "python", "-m", "vtn_worker.main"]
