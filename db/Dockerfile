# Runs the globe-db command (migrations and launch data). Build from the repo
# root, because the uv workspace and its lockfile live there:
#   docker build -f db/Dockerfile .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

# The virtualenv lives outside /app so a source bind mount cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so editing source does not reinstall them. uv needs every
# workspace member's pyproject.toml to read the lockfile.
COPY pyproject.toml uv.lock .python-version ./
COPY db/pyproject.toml db/
COPY api/pyproject.toml api/
COPY ui/pyproject.toml ui/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-workspace --package globe-db

COPY db db
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package globe-db

RUN useradd --create-home app
USER app

CMD ["globe-db", "init"]
