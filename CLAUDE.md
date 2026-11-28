# CLAUDE.md

Example globe UI: Launch Library 2 launch data in Postgres, a FastAPI service
that computes trajectories, and a Streamlit globe.

## Layout

- `pyproject.toml`: the root config. uv workspace (`db`, `api`, `ui`), ruff and
  pytest settings. Do not add tool config to the member `pyproject.toml` files.
- `db/` (`globe_db`), `api/` (`globe_api`), `ui/` (`globe_ui`): one package
  each, `src/` layout, tests in `<member>/tests/`.
- The UI talks to the API only; only `api` and `db` touch Postgres.

## Commands

```
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
docker compose up --build --wait     # whole stack: UI on 8501, API on 8001
```

There is no Makefile, by choice. Use the commands directly.

## Docker

- One Dockerfile per service (`db/`, `api/`, `ui/`), each built from the repo
  root because the uv workspace and `uv.lock` live there.
- The virtualenv is at `/opt/venv`, outside `/app`, so the source bind mounts
  in `docker-compose.yml` cannot hide it.
- Host ports 5432 and 8000 are in use on the owner's machine; keep the
  defaults at 55432, 8001 and 8501.
- After changing a Dockerfile or the compose file, run the stack and check it
  comes up healthy before opening a PR. CI does not build the images.

## Launch data

- Source: Launch Library 2 (`db/src/globe_db/ll2.py`). Keep its field names
  and nesting; `_FIELDS` lists what is kept.
- `snapshot/launches.json` is real data written by `uv run globe-db snapshot`.
  Never edit it by hand or invent records.
- The free tier allows 15 requests an hour; `refresh` and `snapshot` use 2
  each. Tests must not call the live API.
- Tests run on in-memory SQLite. Check schema changes against real Postgres
  with `uv run globe-db init` before opening a PR.

## Trajectories

- `api/src/globe_api/orbit.py` is the maths; `profiles.py` is the table of
  assumed orbits per Launch Library 2 orbit type. The assumptions must stay
  labelled as assumptions in the API's `note` and in the README.
- Launch Library 2's `celestial_body` is unreliable (the snapshot has a "Mars
  Orbit" marked as Earth), so orbit support is decided by `orbit_abbrev` only.
- API tests load the real snapshot into in-memory SQLite.

## UI

- `ui/src/globe_ui/figures.py` builds the globe; `app.py` is the Streamlit
  script; `api_client.py` is the only place that calls the API.
- The series colours (orbit, ascent, pad) were checked for colour-blind
  separation in both themes. Do not swap them for arbitrary colours, and keep
  other pads in neutral grey.
- UI tests stub `api_client` and run the script with Streamlit's `AppTest`.
  After a visual change, also run the app and look at it in both themes.

## Rules (from rae004/.github)

- Never commit to `main`. Branch, open a PR, squash-merge.
- PR titles are Conventional Commits; the title decides the release.
- Versions stay `0.0.0` in every `pyproject.toml`; the version lives in tags.
- Pin every GitHub Action to a commit SHA with the version in a comment.
- A new required CI job goes into `.github/repo-settings.json` in the same PR.
