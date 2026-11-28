from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from globe_ui import api_client
from globe_ui.figures import THEMES, globe_figure, unique_pads

APP = str(Path(__file__).parents[1] / "src" / "globe_ui" / "app.py")


def make_launch(
    launch_id="a", net="2999-01-01T00:00:00Z", pad_id=1, orbit="Low Earth Orbit", supported=True
):
    return {
        "trajectory_supported": supported,
        "id": launch_id,
        "name": f"Rocket | Mission {launch_id}",
        "net": net,
        "status": "Go",
        "provider": "NASA",
        "rocket": "SLS Block 1",
        "mission_name": f"Mission {launch_id}",
        "mission_type": "Earth Science",
        "mission_description": "A test mission.",
        "orbit_name": orbit,
        "orbit_abbrev": "LEO",
        "pad": {
            "id": pad_id,
            "name": f"Pad {pad_id}",
            "location_name": "Kennedy Space Center, FL, USA",
            "country_code": "USA",
            "latitude": 28.6,
            "longitude": -80.6,
        },
    }


def make_trajectory(launch_id="a"):
    point = {"time": "2999-01-01T00:09:00Z", "lat": 28.0, "lon": -62.0, "alt_km": 500.0}
    return {
        "launch_id": launch_id,
        "orbit": {
            "perigee_km": 500.0,
            "apogee_km": 500.0,
            "inclination_deg": 28.6,
            "azimuth_deg": 90.0,
            "period_min": 94.6,
            "line1": "1 99999U",
            "line2": "2 99999",
        },
        "note": "Assumed orbit for Low Earth Orbit.",
        "ascent": [point, point],
        "track": [point, point, point],
    }


NO_TRAJECTORY = {
    "launch_id": "a",
    "orbit": None,
    "note": "No trajectory: the target orbit is Suborbital.",
    "ascent": [],
    "track": [],
}


def trace_names(figure):
    return [trace.name for trace in figure.data]


# --- figures ---------------------------------------------------------------


def test_unique_pads_lists_each_pad_once():
    launches = [make_launch("a", pad_id=1), make_launch("b", pad_id=1), make_launch("c", pad_id=2)]

    assert [pad["id"] for pad in unique_pads(launches)] == [1, 2]


def test_globe_with_nothing_selected_shows_only_the_pads():
    figure = globe_figure([make_launch("a", pad_id=1), make_launch("b", pad_id=2)])

    assert trace_names(figure) == ["Other launch pads"]
    assert len(figure.data[0].lat) == 2
    assert figure.layout.geo.projection.type == "orthographic"


def test_globe_draws_the_selected_launch_and_centres_on_its_pad():
    launches = [make_launch("a", pad_id=1), make_launch("b", pad_id=2)]

    figure = globe_figure(launches, launches[0], make_trajectory(), theme="dark")

    assert trace_names(figure) == ["Other launch pads", "Orbit", "Ascent", "Launch pad"]
    assert len(figure.data[0].lat) == 1  # the selected pad is not also drawn as "other"
    assert len(figure.data[1].lat) == 3
    assert figure.data[3].text == ("Pad 1",)
    assert figure.layout.geo.projection.rotation.lon == -80.6
    assert figure.data[1].line.color == THEMES["dark"].orbit


def test_globe_without_a_trajectory_still_marks_the_pad():
    launch = make_launch()

    figure = globe_figure([launch], launch, NO_TRAJECTORY)

    assert trace_names(figure) == ["Other launch pads", "Launch pad"]


def test_series_colours_differ_within_each_theme():
    for theme in THEMES.values():
        assert len({theme.orbit, theme.ascent, theme.pad, theme.muted}) == 4


# --- api client --------------------------------------------------------------


def test_client_requests_launches_and_trajectories():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/launches":
            return httpx.Response(200, json=[make_launch()])
        return httpx.Response(200, json=make_trajectory())

    def client():
        return httpx.Client(base_url="http://api", transport=httpx.MockTransport(handler))

    assert api_client.list_launches(client())[0]["id"] == "a"
    assert api_client.get_trajectory("a", 2, client())["launch_id"] == "a"
    assert seen == ["http://api/launches?limit=500", "http://api/launches/a/trajectory?orbits=2"]


def test_client_raises_on_an_error_response():
    client = httpx.Client(
        base_url="http://api", transport=httpx.MockTransport(lambda request: httpx.Response(500))
    )

    with pytest.raises(httpx.HTTPStatusError):
        api_client.list_launches(client)


# --- the app -----------------------------------------------------------------


@pytest.fixture
def run_app(monkeypatch):
    """Run the Streamlit script against a stubbed API client."""

    def run(launches, trajectory=None):
        def list_launches():
            if isinstance(launches, Exception):
                raise launches
            return launches

        st.cache_data.clear()
        monkeypatch.setattr(api_client, "list_launches", list_launches)
        monkeypatch.setattr(api_client, "get_trajectory", lambda launch_id, orbits: trajectory)
        return AppTest.from_file(APP, default_timeout=30).run()

    return run


def test_app_shows_the_next_launch_with_its_orbit(run_app):
    past = make_launch("old", net="2000-01-01T00:00:00Z")
    upcoming = make_launch("new", net="2999-01-01T00:00:00Z")

    app = run_app([past, upcoming], make_trajectory("new"))

    assert not app.exception
    assert app.sidebar.selectbox[0].value == upcoming
    assert app.subheader[0].value == "Rocket | Mission new"
    assert [metric.label for metric in app.metric] == [
        "Perigee",
        "Apogee",
        "Inclination",
        "Period",
        "Launch heading",
    ]
    assert app.metric[0].value == "500 km"
    assert any("Assumed orbit" in caption.value for caption in app.caption)
    assert app.code[0].value == "1 99999U\n2 99999"


def test_app_opens_on_the_next_launch_whose_orbit_can_be_drawn(run_app):
    sooner = make_launch("sooner", net="2998-01-01T00:00:00Z", orbit="Unknown", supported=False)
    later = make_launch("later", net="2999-01-01T00:00:00Z")

    app = run_app([sooner, later], make_trajectory("later"))

    assert app.sidebar.selectbox[0].value == later


def test_app_explains_a_launch_with_no_trajectory(run_app):
    app = run_app([make_launch(orbit="Suborbital", supported=False)], NO_TRAJECTORY)

    assert not app.exception
    assert len(app.metric) == 0
    assert app.info[0].value == "No trajectory: the target orbit is Suborbital."


def test_app_reports_an_unreachable_api(run_app):
    app = run_app(httpx.ConnectError("connection refused"))

    assert not app.exception
    assert "Could not reach the API" in app.error[0].value


def test_app_reports_an_empty_database(run_app):
    app = run_app([])

    assert not app.exception
    assert "no launches" in app.warning[0].value
