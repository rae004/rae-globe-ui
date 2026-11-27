"""``globe-db``: apply migrations and load Launch Library 2 launch data."""

import argparse
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from globe_db import ll2
from globe_db.session import get_engine

ACTIONS = {
    "upgrade": "apply database migrations",
    "seed": "load the launch snapshot stored in the repo",
    "init": "upgrade, then seed",
    "refresh": "load live launches from Launch Library 2 (2 of its 15 requests an hour)",
    "snapshot": "rewrite the stored snapshot from Launch Library 2; touches no database",
}


def upgrade() -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    command.upgrade(config, "head")


def fetch_live() -> list[dict]:
    with httpx.Client(base_url=ll2.BASE_URL, timeout=30) as client:
        return ll2.fetch_launches(client)


def load(records: list[dict]) -> int:
    with Session(get_engine()) as session, session.begin():
        return ll2.load_launches(session, records)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="globe-db",
        description=__doc__,
        epilog="\n".join(f"  {name:<9} {text}" for name, text in ACTIONS.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("action", choices=ACTIONS)
    action = parser.parse_args().action

    if action in ("upgrade", "init"):
        upgrade()
        print("migrations applied")
    if action in ("seed", "init"):
        print(f"loaded {load(ll2.read_snapshot())} launches from the snapshot")
    if action == "refresh":
        print(f"loaded {load(fetch_live())} launches from Launch Library 2")
    if action == "snapshot":
        records = fetch_live()
        ll2.write_snapshot(records)
        print(f"wrote {len(records)} launches to {ll2.SNAPSHOT_PATH}")
