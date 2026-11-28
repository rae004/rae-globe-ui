"""The API: launches from Postgres and the trajectory each would fly."""

from datetime import UTC
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from globe_api.profiles import PROFILES, plan_trajectory
from globe_api.schemas import LaunchOut, OrbitOut, TrajectoryOut
from globe_db.models import Launch
from globe_db.session import get_session

app = FastAPI(
    title="Globe API",
    description="Launches from Launch Library 2 and the orbital path each would take.",
)

DbSession = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/launches", response_model=list[LaunchOut])
def list_launches(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Launches, earliest first."""
    query = select(Launch).order_by(Launch.net, Launch.id).limit(limit).offset(offset)
    return session.scalars(query).all()


def _get_launch(session: Session, launch_id: str) -> Launch:
    launch = session.get(Launch, launch_id)
    if launch is None:
        raise HTTPException(status_code=404, detail="Launch not found")
    return launch


@app.get("/launches/{launch_id}", response_model=LaunchOut)
def get_launch(launch_id: str, session: DbSession):
    return _get_launch(session, launch_id)


@app.get("/launches/{launch_id}/trajectory", response_model=TrajectoryOut)
def get_trajectory(
    launch_id: str,
    session: DbSession,
    orbits: Annotated[float, Query(ge=0.5, le=10)] = 3.0,
    points_per_orbit: Annotated[int, Query(ge=30, le=720)] = 180,
):
    """The ascent from the pad and the ground track of the orbit that follows.

    The orbit is an assumption based on the launch's orbit type, not mission data.
    """
    launch = _get_launch(session, launch_id)
    net = launch.net if launch.net.tzinfo else launch.net.replace(tzinfo=UTC)
    trajectory = plan_trajectory(
        launch.orbit_abbrev,
        launch.pad.latitude,
        launch.pad.longitude,
        net,
        orbits,
        points_per_orbit,
    )
    if trajectory is None:
        described = launch.orbit_name or "not given"
        return TrajectoryOut(
            launch_id=launch.id,
            orbit=None,
            note=(
                f"No trajectory: the target orbit is {described}. "
                f"Supported orbit types: {', '.join(PROFILES)}."
            ),
            ascent=[],
            track=[],
        )
    return TrajectoryOut(
        launch_id=launch.id,
        orbit=OrbitOut.model_validate(trajectory),
        note=(
            f"Assumed orbit for {launch.orbit_name}: typical altitude and inclination, "
            "not this mission's actual orbit."
        ),
        ascent=trajectory.ascent,
        track=trajectory.track,
    )
