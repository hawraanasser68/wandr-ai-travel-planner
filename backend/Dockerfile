# ── Stage 1: dependency install ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# uv is much faster than pip for installing packages
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
# Install CPU-only PyTorch first (~250MB vs ~2GB for GPU version).
# Must happen before the main install so uv reuses it for sentence-transformers.
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python --no-cache \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    uv pip install --python /app/.venv/bin/python --no-cache .

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy the pre-built venv from the builder stage (keeps the image smaller)
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Copy application source
COPY . .

# Create directories that may not exist yet
RUN mkdir -p artifacts rag_documents

# Run as non-root for security
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# On container start:
#   1. Apply any pending Alembic migrations
#   2. Start the uvicorn server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
