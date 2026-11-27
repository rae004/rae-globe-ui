# rae-globe-ui

An example of a globe UI in Python: read launch data, show the launch pad on a
globe and the orbital path the launched vehicle would take.

- **`db/`**: Postgres data layer (SQLAlchemy + Alembic). Launch data comes from
  [Launch Library 2](https://thespacedevs.com/llapi).
- **`api/`**: FastAPI service that serves launches and computes trajectories.
- **`ui/`**: Streamlit app that draws the globe.

Status: workspace scaffold only. The data layer, API, UI and Docker stack land
in the pull requests that follow.

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
