"""The globe figure.

Colours are the first three slots of a categorical palette checked for
colour-blind separation in both themes: orbit, ascent, launch pad. The other
pads are context, so they are drawn in a neutral grey rather than a series
colour.
"""

from dataclasses import dataclass

import plotly.graph_objects as go


@dataclass(frozen=True)
class Theme:
    surface: str
    ocean: str
    land: str
    border: str
    grid: str
    text: str
    muted: str
    orbit: str
    ascent: str
    pad: str


THEMES = {
    "light": Theme(
        surface="#ffffff",
        ocean="#ffffff",
        land="#efefef",
        border="#c4c4c4",
        grid="#e4e4e4",
        text="#191919",
        muted="#8a8a8a",
        orbit="#257de0",
        ascent="#f47230",
        pad="#00b894",
    ),
    "dark": Theme(
        surface="#191919",
        ocean="#191919",
        land="#303030",
        border="#565656",
        grid="#2a2a2a",
        text="#efefef",
        muted="#9c9c9c",
        orbit="#338ced",
        ascent="#e76624",
        pad="#00a888",
    ),
}


def unique_pads(launches: list[dict]) -> list[dict]:
    """Each pad once, in the order first seen."""
    pads: dict[int, dict] = {}
    for launch in launches:
        pads.setdefault(launch["pad"]["id"], launch["pad"])
    return list(pads.values())


def _path(points: list[dict], name: str, colour: str) -> go.Scattergeo:
    return go.Scattergeo(
        name=name,
        lat=[point["lat"] for point in points],
        lon=[point["lon"] for point in points],
        mode="lines",
        line={"width": 2, "color": colour},
        customdata=[
            [point["time"][:19].replace("T", " "), round(point["alt_km"])] for point in points
        ],
        hovertemplate=f"<b>{name}</b><br>%{{customdata[0]}} UTC<br>"
        "Altitude %{customdata[1]:,} km<extra></extra>",
    )


def globe_figure(
    launches: list[dict],
    selected: dict | None = None,
    trajectory: dict | None = None,
    theme: str = "light",
) -> go.Figure:
    """A globe with every pad, and the selected launch's pad, ascent and orbit."""
    colours = THEMES[theme]
    selected_pad = selected["pad"] if selected else None
    others = [pad for pad in unique_pads(launches) if not selected_pad or pad != selected_pad]

    figure = go.Figure()
    figure.add_trace(
        go.Scattergeo(
            name="Other launch pads",
            lat=[pad["latitude"] for pad in others],
            lon=[pad["longitude"] for pad in others],
            mode="markers",
            marker={
                "size": 8,
                "color": colours.muted,
                "line": {"width": 2, "color": colours.surface},
            },
            customdata=[[pad["name"], pad["location_name"] or ""] for pad in others],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        )
    )
    if trajectory and trajectory["track"]:
        figure.add_trace(_path(trajectory["track"], "Orbit", colours.orbit))
        figure.add_trace(_path(trajectory["ascent"], "Ascent", colours.ascent))
    if selected_pad:
        figure.add_trace(
            go.Scattergeo(
                name="Launch pad",
                lat=[selected_pad["latitude"]],
                lon=[selected_pad["longitude"]],
                mode="markers+text",
                marker={
                    "size": 12,
                    "color": colours.pad,
                    "line": {"width": 2, "color": colours.surface},
                },
                text=[selected_pad["name"]],
                textposition="top center",
                textfont={"color": colours.text, "size": 13},
                customdata=[[selected_pad["location_name"] or ""]],
                hovertemplate="<b>%{text}</b><br>%{customdata[0]}<extra></extra>",
            )
        )

    centre = selected_pad or {"latitude": 20.0, "longitude": -40.0}
    figure.update_geos(
        projection_type="orthographic",
        projection_rotation={"lat": centre["latitude"], "lon": centre["longitude"]},
        bgcolor="rgba(0,0,0,0)",
        showocean=True,
        oceancolor=colours.ocean,
        showland=True,
        landcolor=colours.land,
        showcountries=True,
        countrycolor=colours.border,
        coastlinecolor=colours.border,
        showframe=True,
        framecolor=colours.border,
        lataxis={"showgrid": True, "gridcolor": colours.grid, "dtick": 30},
        lonaxis={"showgrid": True, "gridcolor": colours.grid, "dtick": 30},
    )
    figure.update_layout(
        height=640,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": colours.text},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.0,
            "x": 0,
            "traceorder": "reversed",
        },
        hoverlabel={"bgcolor": colours.surface, "font": {"color": colours.text}},
        # Keep the viewer's rotation and zoom until another launch is picked.
        uirevision=selected["id"] if selected else "none",
    )
    return figure
