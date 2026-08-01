# ============================================================
# Stage 1: Builder
# Install dependencies into a clean layer so the final image
# doesn't need pip or build tools at runtime.
# ============================================================
FROM python:3.13-slim AS builder

WORKDIR /install

# Copy only the requirements first so Docker caches this layer.
# The layer is only invalidated when requirements.txt changes.
COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# ============================================================
# Stage 2: Runtime
# ============================================================
FROM python:3.13-slim AS runtime

# Non-root user — running as root inside a container is unnecessary
# and increases the blast radius of any security issue.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /install/deps /usr/local

# Copy application source
COPY app/ ./app/

# Pre-create the directories that the app writes to at runtime.
# These are overridden by volume mounts in docker-compose, but
# they ensure the app starts cleanly even when run standalone.
RUN mkdir -p data/uploads data/vector_index \
    && chown -R appuser:appuser /app

USER appuser

# Port uvicorn will listen on inside the container
EXPOSE 8000

# Health check — Docker will mark the container unhealthy if this
# fails, and orchestrators (ECS, Cloud Run) will restart it.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the server.
# --host 0.0.0.0 is required so the port is reachable from outside the container.
# --workers 1 keeps things simple for a demo; increase for production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
