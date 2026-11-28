# The Streamlit app. Build from the repo root, because the uv workspace and its
# lockfile live there:
#   docker build -f ui/Dockerfile .
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
    uv sync --locked --no-dev --no-install-workspace --package globe-ui

COPY ui ui
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package globe-ui

RUN useradd --create-home app
USER app

EXPOSE 8501
CMD ["streamlit", "run", "ui/src/globe_ui/app.py", \
     "--server.address", "0.0.0.0", "--server.port", "8501", \
     "--server.headless", "true", "--browser.gatherUsageStats", "false"]
