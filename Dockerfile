FROM python:3.11-slim

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation and configure uv cache directory
ENV UV_COMPILE_BYTECODE=1
ENV UV_CACHE_DIR=/tmp/.uv-cache

# Copy project configuration files
COPY pyproject.toml uv.lock ./

# Install the dependencies without dev groups and use frozen lockfile.
# Keep this before source copy to leverage Docker layer cache in all environments.
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY src ./src
COPY README.md ./
COPY alembic.ini ./
COPY migrations ./migrations

# Install the application itself
RUN uv sync --frozen --no-dev

# Ensure the virtual environment is available
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["sh", "-c", "alembic upgrade head && uvicorn books_rec_api.main:app --host 0.0.0.0 --port 8000"]
