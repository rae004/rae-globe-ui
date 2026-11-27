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
```

There is no Makefile, by choice. Use the commands directly.

## Launch data

- Source: Launch Library 2 (`db/src/globe_db/ll2.py`). Keep its field names
  and nesting; `_FIELDS` lists what is kept.
- `snapshot/launches.json` is real data written by `uv run globe-db snapshot`.
  Never edit it by hand or invent records.
- The free tier allows 15 requests an hour; `refresh` and `snapshot` use 2
  each. Tests must not call the live API.
- Tests run on in-memory SQLite. Check schema changes against real Postgres
  with `uv run globe-db init` before opening a PR.

## Rules (from rae004/.github)

- Never commit to `main`. Branch, open a PR, squash-merge.
- PR titles are Conventional Commits; the title decides the release.
- Versions stay `0.0.0` in every `pyproject.toml`; the version lives in tags.
- Pin every GitHub Action to a commit SHA with the version in a comment.
- A new required CI job goes into `.github/repo-settings.json` in the same PR.
