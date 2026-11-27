import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from globe_db import ll2
from globe_db.models import Base, Launch, Pad


def ll2_record(launch_id="a", net="2026-11-27T00:15:00Z", latitude=28.6, longitude=-80.6):
    """A launch as Launch Library 2 returns it, plus one field the app does not use."""
    return {
        "id": launch_id,
        "name": f"Rocket | Mission {launch_id}",
        "net": net,
        "window_start": net,
        "window_end": net,
        "last_updated": net,
        "image": {"image_url": "https://example.invalid/rocket.jpg"},
        "status": {"id": 1, "name": "Go for Launch", "abbrev": "Go", "description": "..."},
        "launch_service_provider": {"id": 44, "name": "NASA", "abbrev": "NASA", "type": {}},
        "rocket": {"id": 1, "configuration": {"id": 2, "name": "SLS", "full_name": "SLS Block 1"}},
        "mission": {
            "id": 3,
            "name": f"Mission {launch_id}",
            "type": "Earth Science",
            "description": "A test mission.",
            "orbit": {
                "id": 8,
                "name": "Low Earth Orbit",
                "abbrev": "LEO",
                "celestial_body": {"id": 1, "name": "Earth"},
            },
        },
        "pad": {
            "id": 87,
            "name": "Launch Complex 39B",
            "latitude": latitude,
            "longitude": longitude,
            "country": {"name": "United States of America", "alpha_3_code": "USA"},
            "location": {"id": 27, "name": "Kennedy Space Center, FL, USA", "timezone_name": "UTC"},
        },
    }


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_trim_keeps_shape_and_drops_unused_fields():
    trimmed = ll2.trim(ll2_record())

    assert "image" not in trimmed
    assert "description" not in trimmed["status"]
    assert trimmed["pad"]["latitude"] == 28.6
    assert trimmed["mission"]["orbit"]["celestial_body"] == {"id": 1, "name": "Earth"}


def test_trim_keeps_a_missing_mission_as_none():
    record = ll2_record() | {"mission": None}

    assert ll2.trim(record)["mission"] is None


def test_fetch_launches_merges_upcoming_and_previous_without_duplicates():
    pages = {
        "/2.3.0/launches/upcoming/": [ll2_record("b", net="2026-12-01T00:00:00Z"), ll2_record("a")],
        "/2.3.0/launches/previous/": [ll2_record("a"), ll2_record("c", net="2026-01-01T00:00:00Z")],
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"results": pages[request.url.path]})
    )

    with httpx.Client(base_url=ll2.BASE_URL, transport=transport) as client:
        records = ll2.fetch_launches(client)

    assert [record["id"] for record in records] == ["c", "a", "b"]


def test_fetch_launches_raises_on_an_error_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(429))

    with (
        httpx.Client(base_url=ll2.BASE_URL, transport=transport) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        ll2.fetch_launches(client)


def test_load_launches_maps_fields(session):
    assert ll2.load_launches(session, [ll2.trim(ll2_record())]) == 1
    session.flush()

    launch = session.get(Launch, "a")
    assert launch.rocket == "SLS Block 1"
    assert launch.provider == "NASA"
    assert launch.status == "Go"
    assert launch.orbit_abbrev == "LEO"
    assert launch.orbit_body == "Earth"
    assert launch.net.isoformat().startswith("2026-11-27T00:15:00")
    assert (launch.pad.latitude, launch.pad.longitude) == (28.6, -80.6)
    assert launch.pad.country_code == "USA"


def test_load_launches_twice_updates_instead_of_duplicating(session):
    ll2.load_launches(session, [ll2_record()])
    renamed = ll2_record() | {"name": "Rocket | Renamed"}
    ll2.load_launches(session, [renamed])
    session.flush()

    assert session.scalar(select(func.count()).select_from(Launch)) == 1
    assert session.scalar(select(func.count()).select_from(Pad)) == 1
    assert session.get(Launch, "a").name == "Rocket | Renamed"


def test_load_launches_skips_records_that_cannot_be_drawn(session):
    records = [ll2_record("no-pad-position", latitude=None), ll2_record("no-time", net=None)]

    assert ll2.load_launches(session, records) == 0


def test_load_launches_accepts_a_launch_with_no_mission(session):
    ll2.load_launches(session, [ll2_record() | {"mission": None}])
    session.flush()

    launch = session.get(Launch, "a")
    assert launch.mission_name is None
    assert launch.orbit_abbrev is None


def test_snapshot_is_real_data_that_loads(session):
    records = ll2.read_snapshot()

    assert len(records) >= 50
    assert ll2.load_launches(session, records) == len(records)
    session.flush()
    for pad in session.scalars(select(Pad)):
        assert -90 <= pad.latitude <= 90
        assert -180 <= pad.longitude <= 180


def test_snapshot_holds_only_trimmed_fields():
    for record in ll2.read_snapshot():
        assert ll2.trim(record) == record
