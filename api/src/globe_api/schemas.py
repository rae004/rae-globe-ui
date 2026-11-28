"""Response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location_name: str | None
    country_code: str | None
    latitude: float
    longitude: float


class LaunchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    net: datetime
    status: str | None
    provider: str | None
    rocket: str | None
    mission_name: str | None
    mission_type: str | None
    mission_description: str | None
    orbit_name: str | None
    orbit_abbrev: str | None
    pad: PadOut


class PointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    time: datetime
    lat: float
    lon: float
    alt_km: float


class OrbitOut(BaseModel):
    """The assumed orbit. See ``globe_api.profiles`` for where the numbers come from."""

    model_config = ConfigDict(from_attributes=True)

    perigee_km: float
    apogee_km: float
    inclination_deg: float
    azimuth_deg: float
    period_min: float
    line1: str
    line2: str


class TrajectoryOut(BaseModel):
    launch_id: str
    # Null when the launch's orbit type has no profile; ascent and track are then empty.
    orbit: OrbitOut | None
    note: str
    ascent: list[PointOut]
    track: list[PointOut]
