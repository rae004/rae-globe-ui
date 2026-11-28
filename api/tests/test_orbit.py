import math
from datetime import UTC, datetime, timedelta

import pytest

from globe_api import orbit

KSC = (28.6, -80.6)
LAUNCH = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)


def distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    cosine = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(
        lon2 - lon1
    )
    return orbit.EARTH_RADIUS_KM * math.acos(max(-1.0, min(1.0, cosine)))


def test_due_east_gives_an_inclination_equal_to_the_latitude():
    assert orbit.launch_azimuth(28.6, 28.6) == pytest.approx(90.0)
    assert orbit.launch_azimuth(-39.3, 39.3) == pytest.approx(90.0)


def test_each_inclination_has_a_northbound_and_a_southbound_heading():
    north = orbit.launch_azimuth(28.6, 51.6)
    south = orbit.launch_azimuth(28.6, 51.6, southbound=True)

    assert north == pytest.approx(45.0, abs=0.1)
    assert south == pytest.approx(180.0 - north)


def test_retrograde_orbits_head_west_of_north_or_south():
    # asin(cos 97.8 / cos 34.6) = asin(-0.1649) = -9.49 degrees
    assert orbit.launch_azimuth(34.6, 97.8) == pytest.approx(350.51, abs=0.01)
    assert orbit.launch_azimuth(34.6, 97.8, southbound=True) == pytest.approx(189.49, abs=0.01)


def test_an_inclination_below_the_latitude_is_unreachable():
    with pytest.raises(ValueError, match="not reachable"):
        orbit.launch_azimuth(45.0, 10.0)


def test_reachable_inclination_clamps_to_the_pad_latitude():
    assert orbit.reachable_inclination(62.9, 55.0) == 62.9
    assert orbit.reachable_inclination(-62.9, 150.0) == pytest.approx(117.1)
    assert orbit.reachable_inclination(28.6, 51.6) == 51.6


def test_destination_along_the_equator_and_a_meridian():
    one_degree_km = math.radians(1.0) * orbit.EARTH_RADIUS_KM

    assert orbit.destination(0.0, 10.0, 90.0, one_degree_km) == pytest.approx((0.0, 11.0, 90.0))
    assert orbit.destination(10.0, 20.0, 0.0, one_degree_km) == pytest.approx((11.0, 20.0, 0.0))


def test_destination_wraps_longitude_across_the_date_line():
    _, lon, _ = orbit.destination(0.0, 179.5, 90.0, math.radians(1.0) * orbit.EARTH_RADIUS_KM)

    assert lon == pytest.approx(-179.5)


def test_ascent_runs_from_the_pad_to_orbit_altitude():
    points = orbit.ascent(*KSC, azimuth_deg=90.0, altitude_km=500.0, launch_time=LAUNCH)

    assert (points[0].lat, points[0].lon, points[0].alt_km) == pytest.approx((28.6, -80.6, 0.0))
    assert points[0].time == LAUNCH
    assert points[-1].alt_km == pytest.approx(500.0)
    assert points[-1].time == LAUNCH + timedelta(seconds=orbit.ASCENT_DURATION_S)
    assert distance_km(*KSC, points[-1].lat, points[-1].lon) == pytest.approx(
        orbit.ASCENT_DOWNRANGE_KM, rel=1e-6
    )


@pytest.mark.parametrize(
    ("pad", "inclination", "southbound"),
    [
        (KSC, 28.6, False),
        (KSC, 51.6, False),
        ((34.6, -120.6), 97.8, True),
        ((-39.3, 177.9), 90.0, True),
        ((5.3, -52.8), 5.3, False),
    ],
)
def test_the_orbit_has_the_inclination_asked_for(pad, inclination, southbound):
    azimuth = orbit.launch_azimuth(pad[0], inclination, southbound)
    line1, line2 = orbit.insertion_tle(*pad, azimuth, 500.0, 500.0, LAUNCH)

    tle_inclination, period = orbit.tle_summary(line1, line2)
    assert tle_inclination == pytest.approx(inclination, abs=0.01)
    assert period == pytest.approx(94.6, abs=0.2)


def test_the_tle_is_well_formed():
    line1, line2 = orbit.insertion_tle(*KSC, 90.0, 500.0, 500.0, LAUNCH)

    assert len(line1) == len(line2) == 69
    assert line1.startswith("1 99999") and line2.startswith("2 99999")


def test_the_orbit_starts_where_the_ascent_ends():
    azimuth = orbit.launch_azimuth(KSC[0], 51.6)
    end_of_ascent = orbit.ascent(*KSC, azimuth, 500.0, LAUNCH)[-1]
    line1, line2 = orbit.insertion_tle(*KSC, azimuth, 500.0, 500.0, LAUNCH)

    start_of_orbit = orbit.ground_track(line1, line2, orbits=1)[0]

    assert (
        distance_km(end_of_ascent.lat, end_of_ascent.lon, start_of_orbit.lat, start_of_orbit.lon)
        < 25.0
    )
    assert abs((start_of_orbit.time - end_of_ascent.time).total_seconds()) < 0.01
    assert start_of_orbit.alt_km == pytest.approx(500.0, abs=15.0)


def test_the_orbit_heads_the_way_it_was_launched():
    northbound = orbit.insertion_tle(*KSC, orbit.launch_azimuth(28.6, 51.6), 500.0, 500.0, LAUNCH)
    southbound = orbit.insertion_tle(
        *KSC, orbit.launch_azimuth(28.6, 51.6, southbound=True), 500.0, 500.0, LAUNCH
    )

    north_track = orbit.ground_track(*northbound, orbits=0.05)
    south_track = orbit.ground_track(*southbound, orbits=0.05)

    assert north_track[-1].lat > north_track[0].lat
    assert south_track[-1].lat < south_track[0].lat


def test_a_circular_track_stays_at_altitude_and_within_its_inclination():
    line1, line2 = orbit.insertion_tle(*KSC, orbit.launch_azimuth(28.6, 51.6), 500.0, 500.0, LAUNCH)

    track = orbit.ground_track(line1, line2, orbits=3, points_per_orbit=180)

    assert len(track) == 3 * 180 + 1
    assert max(abs(point.lat) for point in track) == pytest.approx(51.6, abs=0.3)
    assert all(470.0 < point.alt_km < 530.0 for point in track)
    assert all(-180.0 <= point.lon <= 180.0 for point in track)
    assert (track[-1].time - track[0].time).total_seconds() == pytest.approx(
        3 * 94.6 * 60, rel=0.01
    )


def test_a_transfer_orbit_climbs_from_perigee_to_geostationary_altitude():
    line1, line2 = orbit.insertion_tle(*KSC, 90.0, 250.0, 35786.0, LAUNCH)

    track = orbit.ground_track(line1, line2, orbits=1, points_per_orbit=360)
    altitudes = [point.alt_km for point in track]

    assert altitudes[0] == pytest.approx(250.0, abs=30.0)
    assert max(altitudes) == pytest.approx(35786.0, rel=0.01)
    assert orbit.tle_summary(line1, line2)[1] == pytest.approx(631.0, abs=5.0)
