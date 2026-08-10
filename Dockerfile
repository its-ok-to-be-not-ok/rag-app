# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Stage 1: Build dependencies
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --prefix=/install --no-cache-dir -r requirements.txt && \
    find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /install -type f -name "*.pyc" -delete && \
    find /install -type f -name "*.pyo" -delete

# Stage 2: Runtime
FROM base AS runner

COPY --from=builder /install /usr/local
COPY . .

RUN adduser --disabled-password --gecos "" raguser && \
    chown -R raguser:raguser /app
USER raguser

EXPOSE 8045

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8045/health')" || exit 1

# Sử dụng sh -c để đọc biến PORT từ Render (fallback 8045)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8045}"]