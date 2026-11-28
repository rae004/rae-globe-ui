"""Assumed orbits for Launch Library 2's orbit types.

Launch Library 2 names the kind of orbit a launch is aiming for ("Low Earth
Orbit", "Sun-Synchronous Orbit") but gives no altitude or inclination. The
numbers below are typical values chosen for this example. They are this app's
assumptions, not source data; a real mission's orbit will differ.
"""

from dataclasses import dataclass
from datetime import datetime

from globe_api import orbit


@dataclass(frozen=True)
class OrbitProfile:
    perigee_km: float
    apogee_km: float
    # None: launch due east, which gives an inclination equal to the pad's latitude.
    inclination_deg: float | None
    # Polar and sun-synchronous launches are flown southbound from most ranges.
    southbound: bool = False


_TRANSFER_TO_GEOSTATIONARY = OrbitProfile(250.0, 35786.0, None)

# Keyed by Launch Library 2's orbit abbreviation.
PROFILES: dict[str, OrbitProfile] = {
    "LEO": OrbitProfile(500.0, 500.0, None),
    "PO": OrbitProfile(600.0, 600.0, 90.0, southbound=True),
    "SSO": OrbitProfile(600.0, 600.0, 97.8, southbound=True),
    "MEO": OrbitProfile(20200.0, 20200.0, 55.0),
    "GTO": _TRANSFER_TO_GEOSTATIONARY,
    # A geostationary satellite stays over one spot, so its transfer orbit is
    # drawn instead: that is the path the launch vehicle itself flies.
    "GEO": _TRANSFER_TO_GEOSTATIONARY,
    "Direct-GEO": _TRANSFER_TO_GEOSTATIONARY,
}


@dataclass(frozen=True)
class Trajectory:
    perigee_km: float
    apogee_km: float
    inclination_deg: float
    azimuth_deg: float
    period_min: float
    line1: str
    line2: str
    ascent: list[orbit.Point]
    track: list[orbit.Point]


def plan_trajectory(
    orbit_abbrev: str | None,
    pad_lat: float,
    pad_lon: float,
    launch_time: datetime,
    orbits: float = 3.0,
    points_per_orbit: int = 180,
) -> Trajectory | None:
    """The ascent and orbit for a launch, or None if its orbit type has no profile."""
    profile = PROFILES.get(orbit_abbrev or "")
    if profile is None:
        return None

    target = abs(pad_lat) if profile.inclination_deg is None else profile.inclination_deg
    azimuth = orbit.launch_azimuth(
        pad_lat, orbit.reachable_inclination(pad_lat, target), profile.southbound
    )
    line1, line2 = orbit.insertion_tle(
        pad_lat, pad_lon, azimuth, profile.perigee_km, profile.apogee_km, launch_time
    )
    inclination, period = orbit.tle_summary(line1, line2)
    return Trajectory(
        perigee_km=profile.perigee_km,
        apogee_km=profile.apogee_km,
        inclination_deg=inclination,
        azimuth_deg=azimuth,
        period_min=period,
        line1=line1,
        line2=line2,
        ascent=orbit.ascent(pad_lat, pad_lon, azimuth, profile.perigee_km, launch_time),
        track=orbit.ground_track(line1, line2, orbits, points_per_orbit),
    )
