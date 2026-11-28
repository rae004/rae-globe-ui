# rae-globe-ui

An example of a globe UI in Python: read launch data, show the launch pad on a
globe and the orbital path the launched vehicle would take.

- **`db/`**: Postgres data layer (SQLAlchemy + Alembic). Launch data comes from
  [Launch Library 2](https://thespacedevs.com/llapi).
- **`api/`**: FastAPI service that serves launches and computes trajectories.
- **`ui/`**: Streamlit app that draws the globe.

## Quick start

Needs Docker with Compose.

```
cp .env.example .env            # optional: every value has the same default
docker compose up --build --wait
```

| What | Where |
|---|---|
| The globe | http://localhost:8501 |
| API docs | http://localhost:8001/docs |
| Postgres | `localhost:55432`, user, password and database all `globe` |

The stack is Postgres, a one-off `migrate` job (applies migrations and loads
the launch snapshot into an empty database), the API and the UI. The `db/`,
`api/` and `ui/` source folders are mounted into the containers: saving a file
reloads the API or the UI, with no rebuild. Rebuild (`--build`) after changing
dependencies.

```
docker compose logs -f                             # follow the logs
docker compose run --rm migrate globe-db refresh   # load live Launch Library 2 data
docker compose down                                # stop; the database is kept
docker compose down -v                             # stop and delete the database
```

The host ports are set in `.env`. They default to 55432, 8001 and 8501 rather
than 5432 and 8000, which are often already taken on a development machine.

## UI

To run it outside Docker (the API must be running, see below):

```
uv run streamlit run ui/src/globe_ui/app.py
```

Open http://localhost:8501. Pick a launch in the sidebar to see its pad, the
ascent and the orbit on the globe; drag to rotate, scroll to zoom. The app
opens on the next launch whose orbit can be drawn. Below the globe are the
assumed orbit's figures, the TLE and the trajectory as a table.

The UI reads everything from the API at `API_BASE_URL` (see `.env.example`)
and never touches the database. It follows the browser's light or dark theme.

## API

To run it outside Docker (Postgres must be running and loaded, see Launch
data):

```
uv run uvicorn globe_api.main:app --reload --port 8001
```

Interactive docs are at http://localhost:8001/docs.

| Route | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /launches?limit=&offset=` | Launches with their pads, earliest first. `trajectory_supported` says whether an orbit can be drawn |
| `GET /launches/{id}` | One launch |
| `GET /launches/{id}/trajectory?orbits=&points_per_orbit=` | The ascent from the pad and the ground track of the orbit that follows |

### How a trajectory is worked out

Launch Library 2 gives the kind of orbit a launch is aiming for, not its
altitude or inclination. `api/src/globe_api/profiles.py` maps each orbit type
to typical values. **These are this example's assumptions, not mission data.**

| Orbit type | Assumed orbit | Launch heading |
|---|---|---|
| `LEO` | 500 km circular | Due east, so the inclination equals the pad's latitude |
| `PO` | 600 km circular, 90° | Southbound |
| `SSO` | 600 km circular, 97.8° | Southbound |
| `MEO` | 20,200 km circular, 55° | Northbound |
| `GTO`, `GEO`, `Direct-GEO` | 250 × 35,786 km transfer orbit | Due east |

An inclination the pad's latitude cannot reach directly is moved to the
nearest one it can. Any other orbit type (suborbital, unknown, another planet)
returns `"orbit": null` with a note and no points.

From the pad position, heading and assumed orbit, the API builds a two-line
element set (TLE) for the moment of orbit insertion and propagates it with
[SGP4](https://pypi.org/project/sgp4/). The TLE is included in the response.
The ascent is a fixed 540 s, 1,800 km arc for drawing, not a simulated flight.

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
uv run globe-db init      # apply migrations; load the snapshot if there are no launches
uv run globe-db seed      # load the snapshot, overwriting launches it contains
uv run globe-db refresh   # load live data from Launch Library 2
uv run globe-db snapshot  # rewrite the snapshot file from Launch Library 2
```

`globe-db` needs a running Postgres that matches `.env`. `docker compose up
--wait db` starts just the database.

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
