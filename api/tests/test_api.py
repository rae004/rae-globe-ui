import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from globe_api.main import app
from globe_api.profiles import PROFILES
from globe_db import ll2
from globe_db.models import Base, Launch
from globe_db.session import get_session


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite holding the real launch snapshot."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        ll2.load_launches(session, ll2.read_snapshot())
    return engine


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def launch_id_with_orbit(engine, abbrev):
    with Session(engine) as session:
        launch_id = session.scalar(select(Launch.id).where(Launch.orbit_abbrev == abbrev).limit(1))
    assert launch_id, f"the snapshot has no {abbrev} launch"
    return launch_id


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_launches_are_listed_earliest_first_with_their_pad(client):
    launches = client.get("/launches").json()

    assert len(launches) == len(ll2.read_snapshot())
    assert [launch["net"] for launch in launches] == sorted(launch["net"] for launch in launches)
    assert {"id", "name", "latitude", "longitude"} <= launches[0]["pad"].keys()


def test_launches_can_be_paged(client):
    everything = client.get("/launches").json()

    page = client.get("/launches", params={"limit": 5, "offset": 10}).json()

    assert page == everything[10:15]


def test_a_page_size_out_of_range_is_rejected(client):
    assert client.get("/launches", params={"limit": 0}).status_code == 422


def test_one_launch(client, engine):
    launch_id = launch_id_with_orbit(engine, "LEO")

    launch = client.get(f"/launches/{launch_id}").json()

    assert launch["id"] == launch_id
    assert launch["orbit_abbrev"] == "LEO"


def test_an_unknown_launch_is_a_404(client):
    assert client.get("/launches/nope").status_code == 404
    assert client.get("/launches/nope/trajectory").status_code == 404


def test_trajectory_of_a_low_earth_orbit_launch(client, engine):
    launch_id = launch_id_with_orbit(engine, "LEO")
    pad = client.get(f"/launches/{launch_id}").json()["pad"]

    body = client.get(
        f"/launches/{launch_id}/trajectory", params={"orbits": 2, "points_per_orbit": 90}
    ).json()

    assert body["launch_id"] == launch_id
    assert body["orbit"]["perigee_km"] == body["orbit"]["apogee_km"] == 500.0
    assert body["orbit"]["azimuth_deg"] == pytest.approx(90.0)
    assert body["orbit"]["inclination_deg"] == pytest.approx(abs(pad["latitude"]), abs=0.01)
    assert len(body["orbit"]["line1"]) == 69
    assert "Assumed orbit" in body["note"]
    assert body["ascent"][0]["lat"] == pytest.approx(pad["latitude"])
    assert body["ascent"][0]["lon"] == pytest.approx(pad["longitude"])
    assert len(body["track"]) == 2 * 90 + 1


def test_a_sun_synchronous_launch_heads_south_into_a_retrograde_orbit(client, engine):
    launch_id = launch_id_with_orbit(engine, "SSO")

    body = client.get(f"/launches/{launch_id}/trajectory").json()

    assert 90.0 < body["orbit"]["azimuth_deg"] < 270.0
    assert body["orbit"]["inclination_deg"] > 90.0
    assert body["ascent"][-1]["lat"] < body["ascent"][0]["lat"]


def test_a_launch_with_no_supported_orbit_has_no_trajectory(client, engine):
    launch_id = launch_id_with_orbit(engine, "Sub")

    body = client.get(f"/launches/{launch_id}/trajectory").json()

    assert body["orbit"] is None
    assert body["ascent"] == [] and body["track"] == []
    assert "Suborbital" in body["note"]


def test_every_launch_in_the_snapshot_gets_an_answer(client):
    for launch in client.get("/launches").json():
        response = client.get(
            f"/launches/{launch['id']}/trajectory", params={"orbits": 1, "points_per_orbit": 30}
        )

        assert response.status_code == 200, launch["name"]
        has_orbit = response.json()["orbit"] is not None
        assert has_orbit == (launch["orbit_abbrev"] in PROFILES), launch["name"]
        assert has_orbit == launch["trajectory_supported"], launch["name"]
