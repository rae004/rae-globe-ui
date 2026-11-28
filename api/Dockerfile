# The FastAPI service. Build from the repo root, because the uv workspace and
# its lockfile live there:
#   docker build -f api/Dockerfile .
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
    uv sync --locked --no-dev --no-install-workspace --package globe-api

# The API imports the data layer, so both packages are installed.
COPY db db
COPY api api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package globe-api

RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "globe_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
