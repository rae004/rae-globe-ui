# rae-globe-ui

An example of a globe UI in Python: read launch data, show the launch pad on a
globe and the orbital path the launched vehicle would take.

- **`db/`**: Postgres data layer (SQLAlchemy + Alembic). Launch data comes from
  [Launch Library 2](https://thespacedevs.com/llapi).
- **`api/`**: FastAPI service that serves launches and computes trajectories.
- **`ui/`**: Streamlit app that draws the globe.

Status: the data layer is in place. The API, UI and Docker stack land in the
pull requests that follow.

## Launch data

Launches and pads come from Launch Library 2 and are stored in Postgres under
Launch Library 2's own ids.

- `db/src/globe_db/snapshot/launches.json` is a snapshot of real Launch
  Library 2 records (the next 50 and the most recent 50 launches), cut down to
  the fields the app uses. The database is seeded from it, so the app works
  offline.
- `globe-db refresh` loads the same set live. The free Launch Library 2 tier
  allows 15 requests an hour; a refresh uses 2.

```
cp .env.example .env      # database settings; the values are local defaults
uv run globe-db init      # apply migrations, then load the snapshot
uv run globe-db refresh   # replace it with live data from Launch Library 2
uv run globe-db snapshot  # rewrite the snapshot file from Launch Library 2
```

`globe-db` needs a running Postgres that matches `.env`. Until the Docker
stack lands, start one with:

```
docker run -d --name globe-db -p 55432:5432 \
  -e POSTGRES_USER=globe -e POSTGRES_PASSWORD=globe -e POSTGRES_DB=globe \
  postgres:17-alpine
```

## Development

The repo is one [uv](https://docs.astral.sh/uv/) workspace. The root
`pyproject.toml` holds the workspace definition and the ruff and pytest
settings for all three packages.

```
uv sync                   # install db, api, ui and the dev tools into .venv
uv run pytest             # run all tests
uv run ruff check .       # lint
uv run ruff format .      # format
```

## Contributing

This repo follows the shared rules in
[rae004/.github](https://github.com/rae004/.github):

- Every change reaches `main` through a squash-merged pull request.
- The PR title is a Conventional Commit (`feat: ...`, `fix: ...`,
  `chore: ...`) and decides the release: `feat` cuts a minor, `fix` and `perf`
  a patch, anything else none.
- The version lives in git tags only; every `pyproject.toml` stays at `0.0.0`.
- GitHub Actions are pinned to a commit SHA.
