# --------------------------------------------------------------------------------
# STAGE 1: Builder (Compiles dependencies)
# --------------------------------------------------------------------------------
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies (needed for headers, gcc, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# --------------------------------------------------------------------------------
# STAGE 2: Base Runtime (Common setup for API and Worker)
# --------------------------------------------------------------------------------
FROM python:3.12-slim as base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime libraries (libpq) to keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY . .

# Create required directories and set permissions
RUN mkdir -p uploads logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# --------------------------------------------------------------------------------
# STAGE 3: API Target (Matches 'target: api' in compose)
# --------------------------------------------------------------------------------
FROM base as api
EXPOSE 8000
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# --------------------------------------------------------------------------------
# STAGE 4: Worker Target (Matches 'target: worker' in compose)
# --------------------------------------------------------------------------------
FROM base as worker
CMD ["celery", "-A", "app.worker.tasks.celery_app", "worker", "--loglevel=info"]