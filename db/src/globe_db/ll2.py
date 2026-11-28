"""Launch Library 2 (https://thespacedevs.com/llapi): fetch, snapshot and load.

Records keep Launch Library 2's own field names and nesting, cut down to the
fields this app uses. The snapshot in ``snapshot/launches.json`` is real data
in that shape, so seeding and a live refresh go through the same loader.
"""

import json
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from globe_db.models import Launch, Pad

BASE_URL = "https://ll.thespacedevs.com/2.3.0"
SNAPSHOT_PATH = Path(__file__).parent / "snapshot" / "launches.json"

# The fields kept from each launch record; True marks a value kept as is.
_FIELDS: dict[str, Any] = {
    "id": True,
    "name": True,
    "net": True,
    "window_start": True,
    "window_end": True,
    "last_updated": True,
    "status": {"id": True, "name": True, "abbrev": True},
    "launch_service_provider": {"id": True, "name": True, "abbrev": True},
    "rocket": {"configuration": {"id": True, "name": True, "full_name": True}},
    "mission": {
        "id": True,
        "name": True,
        "type": True,
        "description": True,
        "orbit": {
            "id": True,
            "name": True,
            "abbrev": True,
            "celestial_body": {"id": True, "name": True},
        },
    },
    "pad": {
        "id": True,
        "name": True,
        "latitude": True,
        "longitude": True,
        "country": {"name": True, "alpha_3_code": True},
        "location": {"id": True, "name": True, "timezone_name": True},
    },
}


def _pick(value: Any, spec: Any) -> Any:
    if spec is True or not isinstance(value, dict):
        return value
    return {key: _pick(value.get(key), sub) for key, sub in spec.items()}


def trim(record: dict) -> dict:
    """Cut a Launch Library 2 launch record down to the fields in ``_FIELDS``."""
    return _pick(record, _FIELDS)


def fetch_launches(client: httpx.Client, limit: int = 50) -> list[dict]:
    """Fetch the next and the most recent ``limit`` launches, trimmed, oldest first.

    Two requests. The free tier allows 15 an hour, so do not call this in a loop.
    """
    records: dict[str, dict] = {}
    for endpoint in ("upcoming", "previous"):
        response = client.get(f"/launches/{endpoint}/", params={"limit": limit, "mode": "normal"})
        response.raise_for_status()
        for record in response.json()["results"]:
            records[record["id"]] = trim(record)
    return sorted(records.values(), key=lambda record: record["net"] or "")


def read_snapshot() -> list[dict]:
    snapshot = resources.files("globe_db").joinpath("snapshot", "launches.json")
    return json.loads(snapshot.read_text(encoding="utf-8"))["results"]


def write_snapshot(records: list[dict]) -> None:
    body = {"count": len(records), "results": records}
    SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_launches(session: Session, records: list[dict]) -> int:
    """Insert or update launches and their pads. Returns the number loaded.

    A record with no launch time or no pad coordinates cannot be drawn on the
    globe, so it is skipped.
    """
    loaded = 0
    for record in records:
        pad = record.get("pad") or {}
        if not record.get("net") or pad.get("latitude") is None or pad.get("longitude") is None:
            continue
        mission = record.get("mission") or {}
        orbit = mission.get("orbit") or {}
        session.merge(
            Pad(
                id=pad["id"],
                name=pad["name"],
                location_name=(pad.get("location") or {}).get("name"),
                country_code=(pad.get("country") or {}).get("alpha_3_code"),
                latitude=float(pad["latitude"]),
                longitude=float(pad["longitude"]),
            )
        )
        session.merge(
            Launch(
                id=record["id"],
                name=record["name"],
                net=datetime.fromisoformat(record["net"]),
                status=(record.get("status") or {}).get("abbrev"),
                provider=(record.get("launch_service_provider") or {}).get("name"),
                rocket=((record.get("rocket") or {}).get("configuration") or {}).get("full_name"),
                mission_name=mission.get("name"),
                mission_type=mission.get("type"),
                mission_description=mission.get("description"),
                orbit_name=orbit.get("name"),
                orbit_abbrev=orbit.get("abbrev"),
                orbit_body=(orbit.get("celestial_body") or {}).get("name"),
                pad_id=pad["id"],
            )
        )
        loaded += 1
    return loaded
