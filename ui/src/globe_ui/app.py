"""Streamlit app: pick a launch, see its pad and the orbit it would fly.

Run with ``uv run streamlit run ui/src/globe_ui/app.py``.
"""

from datetime import UTC, datetime

import httpx
import streamlit as st

from globe_ui import api_client
from globe_ui.figures import globe_figure


@st.cache_data(ttl=300, show_spinner="Loading launches")
def load_launches() -> list[dict]:
    return api_client.list_launches()


@st.cache_data(ttl=300, show_spinner="Working out the trajectory")
def load_trajectory(launch_id: str, orbits: int) -> dict:
    return api_client.get_trajectory(launch_id, orbits)


def page_theme() -> str:
    theme = getattr(st.context, "theme", None)
    return "dark" if getattr(theme, "type", None) == "dark" else "light"


def launch_label(launch: dict) -> str:
    return f"{launch['net'][:10]}  {launch['name']}"


def next_launch_index(launches: list[dict]) -> int:
    """The next launch to open on: preferably one whose orbit can be drawn.

    Falls back to the next launch of any kind, then to the last one in the list.
    """
    now = datetime.now(UTC).isoformat()
    upcoming = [index for index, launch in enumerate(launches) if launch["net"] >= now]
    drawable = [index for index in upcoming if launches[index].get("trajectory_supported")]
    return (drawable or upcoming or [len(launches) - 1])[0]


def main() -> None:
    st.set_page_config(page_title="Launch to orbit", page_icon=":satellite:", layout="wide")
    st.title("Launch to orbit")

    try:
        launches = load_launches()
    except httpx.HTTPError as error:
        st.error(
            f"Could not reach the API at {api_client.UiSettings().api_base_url}. "
            f"Is it running? ({error})"
        )
        st.stop()
    if not launches:
        st.warning("The API has no launches. Load them with `uv run globe-db init`.")
        st.stop()

    with st.sidebar:
        st.header("Launch")
        launch = st.selectbox(
            "Launch",
            launches,
            index=next_launch_index(launches),
            format_func=launch_label,
            label_visibility="collapsed",
        )
        orbits = st.slider("Orbits to draw", min_value=1, max_value=10, value=3)
        st.caption(
            "Launch data: Launch Library 2. Orbits are typical values for each "
            "orbit type, not the mission's actual orbit."
        )

    try:
        trajectory = load_trajectory(launch["id"], orbits)
    except httpx.HTTPError as error:
        st.error(f"Could not work out the trajectory. ({error})")
        trajectory = None

    pad = launch["pad"]
    st.subheader(launch["name"])
    st.markdown(
        f"**{launch['net'][:16].replace('T', ' ')} UTC** from **{pad['name']}**, "
        f"{pad['location_name'] or 'location not given'}  \n"
        f"{launch['rocket'] or 'Rocket not given'} · {launch['provider'] or 'Provider not given'}"
        f" · target: {launch['orbit_name'] or 'not given'}"
    )

    orbit = trajectory["orbit"] if trajectory else None
    if orbit:
        tiles = st.columns(5)
        tiles[0].metric("Perigee", f"{orbit['perigee_km']:,.0f} km")
        tiles[1].metric("Apogee", f"{orbit['apogee_km']:,.0f} km")
        tiles[2].metric("Inclination", f"{orbit['inclination_deg']:.1f}°")
        tiles[3].metric("Period", f"{orbit['period_min']:,.0f} min")
        tiles[4].metric("Launch heading", f"{orbit['azimuth_deg']:.0f}°")

    st.plotly_chart(
        globe_figure(launches, launch, trajectory, page_theme()),
        width="stretch",
        theme=None,
        config={"displaylogo": False, "scrollZoom": True},
    )

    if trajectory:
        (st.caption if orbit else st.info)(trajectory["note"])
    if launch["mission_description"]:
        st.markdown(f"**Mission.** {launch['mission_description']}")
    if orbit:
        with st.expander("Two-line element set (TLE)"):
            st.code(f"{orbit['line1']}\n{orbit['line2']}", language=None)
        with st.expander("Trajectory as a table"):
            st.dataframe(
                [
                    {
                        "Phase": phase,
                        "Time (UTC)": point["time"][:19].replace("T", " "),
                        "Latitude": round(point["lat"], 3),
                        "Longitude": round(point["lon"], 3),
                        "Altitude (km)": round(point["alt_km"], 1),
                    }
                    for phase, points in (
                        ("Ascent", trajectory["ascent"]),
                        ("Orbit", trajectory["track"]),
                    )
                    for point in points
                ],
                width="stretch",
                hide_index=True,
            )


main()
