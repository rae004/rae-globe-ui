"""Orbit maths: from a launch pad and a target orbit to a ground track.

The model is deliberately simple, and good enough to draw:

- The Earth is a sphere for positions on the ground; latitudes are geocentric.
- The ascent is a fixed-length arc along a great circle, not a simulated flight,
  and it ignores the Earth turning underneath it.
- The vehicle is inserted at perigee, flying horizontally. Its state there is
  turned into a two-line element set (TLE), and SGP4 propagates the orbit from
  that TLE, so a real TLE can be drawn by the same ``ground_track`` function.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sgp4.api import WGS72, Satrec, jday
from sgp4.exporter import export_tle

MU_KM3_S2 = 398600.4418
EARTH_RADIUS_KM = 6378.137
ASCENT_DURATION_S = 540.0
ASCENT_DOWNRANGE_KM = 1800.0

_J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)
_TLE_EPOCH_JD = 2433281.5  # 1949-12-31 00:00 UT, the zero of SGP4's epoch argument


@dataclass(frozen=True)
class Point:
    time: datetime
    lat: float
    lon: float
    alt_km: float


def reachable_inclination(lat_deg: float, inclination_deg: float) -> float:
    """Clamp an inclination to what a direct launch from this latitude can reach.

    A pad at latitude L cannot launch straight into an orbit inclined less than
    |L| or more than 180 - |L|.
    """
    lowest = abs(lat_deg)
    return min(max(inclination_deg, lowest), 180.0 - lowest)


def launch_azimuth(lat_deg: float, inclination_deg: float, southbound: bool = False) -> float:
    """Compass heading at lift-off, in degrees, that gives the inclination.

    Each reachable inclination has a northbound and a southbound heading.
    """
    ratio = math.cos(math.radians(inclination_deg)) / math.cos(math.radians(lat_deg))
    if abs(ratio) > 1 + 1e-9:
        raise ValueError(f"inclination {inclination_deg} is not reachable from latitude {lat_deg}")
    northbound = math.degrees(math.asin(max(-1.0, min(1.0, ratio))))
    return (180.0 - northbound if southbound else northbound) % 360.0


def destination(
    lat_deg: float, lon_deg: float, azimuth_deg: float, distance_km: float
) -> tuple[float, float, float]:
    """Travel along a great circle. Returns latitude, longitude and the heading on arrival."""
    lat, azimuth = math.radians(lat_deg), math.radians(azimuth_deg)
    arc = distance_km / EARTH_RADIUS_KM
    lat2 = math.asin(
        math.sin(lat) * math.cos(arc) + math.cos(lat) * math.sin(arc) * math.cos(azimuth)
    )
    lon2 = math.radians(lon_deg) + math.atan2(
        math.sin(azimuth) * math.sin(arc) * math.cos(lat),
        math.cos(arc) - math.sin(lat) * math.sin(lat2),
    )
    heading = math.atan2(
        math.sin(azimuth) * math.cos(lat),
        math.cos(arc) * math.cos(lat) * math.cos(azimuth) - math.sin(arc) * math.sin(lat),
    )
    return math.degrees(lat2), _wrap_lon(math.degrees(lon2)), math.degrees(heading) % 360.0


def ascent(
    lat_deg: float,
    lon_deg: float,
    azimuth_deg: float,
    altitude_km: float,
    launch_time: datetime,
    steps: int = 30,
) -> list[Point]:
    """The arc from the pad to the insertion point: slow start, levelling off at altitude."""
    points = []
    for step in range(steps + 1):
        fraction = step / steps
        lat, lon, _ = destination(lat_deg, lon_deg, azimuth_deg, ASCENT_DOWNRANGE_KM * fraction**2)
        points.append(
            Point(
                time=launch_time + timedelta(seconds=ASCENT_DURATION_S * fraction),
                lat=lat,
                lon=lon,
                alt_km=altitude_km * math.sin(fraction * math.pi / 2),
            )
        )
    return points


def insertion_tle(
    lat_deg: float,
    lon_deg: float,
    azimuth_deg: float,
    perigee_km: float,
    apogee_km: float,
    launch_time: datetime,
    satellite_number: int = 99999,
) -> tuple[str, str]:
    """The TLE of the orbit entered at the end of the ascent from this pad."""
    lat, lon, heading = destination(lat_deg, lon_deg, azimuth_deg, ASCENT_DOWNRANGE_KM)
    jd, fraction = _julian(launch_time + timedelta(seconds=ASCENT_DURATION_S))

    # Position and velocity directions in the inertial frame at insertion.
    phi, beta = math.radians(lat), math.radians(heading)
    theta = _gmst(jd + fraction) + math.radians(lon)
    position = (math.cos(phi) * math.cos(theta), math.cos(phi) * math.sin(theta), math.sin(phi))
    east = (-math.sin(theta), math.cos(theta), 0.0)
    north = (-math.sin(phi) * math.cos(theta), -math.sin(phi) * math.sin(theta), math.cos(phi))
    velocity = tuple(
        math.sin(beta) * e + math.cos(beta) * n for e, n in zip(east, north, strict=True)
    )

    # Orbital plane from the angular momentum direction.
    momentum = _cross(position, velocity)
    inclination = math.acos(max(-1.0, min(1.0, momentum[2])))
    node = (-momentum[1], momentum[0], 0.0)
    node_length = math.hypot(node[0], node[1])
    if node_length < 1e-9:  # equatorial: no ascending node, measure from the x axis
        raan = 0.0
        arg_latitude = math.atan2(position[1], position[0])
    else:
        node = (node[0] / node_length, node[1] / node_length, 0.0)
        raan = math.atan2(node[1], node[0])
        arg_latitude = math.atan2(_dot(position, _cross(momentum, node)), _dot(position, node))

    perigee_radius = EARTH_RADIUS_KM + perigee_km
    apogee_radius = EARTH_RADIUS_KM + apogee_km
    semi_major_axis = (perigee_radius + apogee_radius) / 2
    eccentricity = (apogee_radius - perigee_radius) / (apogee_radius + perigee_radius)
    mean_motion_rad_min = math.sqrt(MU_KM3_S2 / semi_major_axis**3) * 60.0

    satellite = Satrec()
    satellite.sgp4init(
        WGS72,
        "i",
        satellite_number,
        jd + fraction - _TLE_EPOCH_JD,
        0.0,  # drag term
        0.0,  # first derivative of mean motion (unused by SGP4)
        0.0,  # second derivative of mean motion (unused by SGP4)
        eccentricity,
        arg_latitude % math.tau,  # argument of perigee: insertion is at perigee
        inclination,
        0.0,  # mean anomaly: at perigee
        mean_motion_rad_min,
        raan % math.tau,
    )
    return export_tle(satellite)


def tle_summary(line1: str, line2: str) -> tuple[float, float]:
    """Inclination in degrees and period in minutes, read from a TLE."""
    satellite = Satrec.twoline2rv(line1, line2)
    return math.degrees(satellite.inclo), math.tau / satellite.no_kozai


def ground_track(
    line1: str, line2: str, orbits: float = 3.0, points_per_orbit: int = 180
) -> list[Point]:
    """Propagate a TLE with SGP4 from its epoch and return where it flies over."""
    satellite = Satrec.twoline2rv(line1, line2)
    period_s = math.tau / satellite.no_kozai * 60.0
    step_s = period_s / points_per_orbit
    epoch_days = (satellite.jdsatepoch - 2451545.0) + satellite.jdsatepochF

    points = []
    for index in range(round(orbits * points_per_orbit) + 1):
        elapsed_days = index * step_s / 86400.0
        error, position, _ = satellite.sgp4(
            satellite.jdsatepoch, satellite.jdsatepochF + elapsed_days
        )
        if error:
            raise ValueError(f"SGP4 could not propagate this orbit (error code {error})")
        # Rotate from the inertial frame into the Earth-fixed one.
        theta = _gmst(satellite.jdsatepoch + satellite.jdsatepochF + elapsed_days)
        x = math.cos(theta) * position[0] + math.sin(theta) * position[1]
        y = -math.sin(theta) * position[0] + math.cos(theta) * position[1]
        radius = math.sqrt(_dot(position, position))
        points.append(
            Point(
                time=_J2000 + timedelta(days=epoch_days + elapsed_days),
                lat=math.degrees(math.asin(position[2] / radius)),
                lon=math.degrees(math.atan2(y, x)),
                alt_km=radius - EARTH_RADIUS_KM,
            )
        )
    return points


def _julian(moment: datetime) -> tuple[float, float]:
    moment = moment.astimezone(UTC)
    return jday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second + moment.microsecond / 1e6,
    )


def _gmst(julian_date: float) -> float:
    """Greenwich mean sidereal time in radians (IAU 1982)."""
    centuries = (julian_date - 2451545.0) / 36525.0
    seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * centuries
        + 0.093104 * centuries**2
        - 6.2e-6 * centuries**3
    )
    return math.radians((seconds % 86400.0) / 240.0)


def _wrap_lon(lon_deg: float) -> float:
    return (lon_deg + 180.0) % 360.0 - 180.0


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
