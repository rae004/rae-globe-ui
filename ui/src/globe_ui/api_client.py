"""HTTP client for the Globe API. The UI reads everything through here."""

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class UiSettings(BaseSettings):
    """Read from the environment, falling back to the root ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = "http://localhost:8001"


def _client() -> httpx.Client:
    return httpx.Client(base_url=UiSettings().api_base_url, timeout=30)


def list_launches(client: httpx.Client | None = None) -> list[dict]:
    """Every launch the API has, earliest first."""
    with client or _client() as http:
        response = http.get("/launches", params={"limit": 500})
        response.raise_for_status()
        return response.json()


def get_trajectory(launch_id: str, orbits: float, client: httpx.Client | None = None) -> dict:
    with client or _client() as http:
        response = http.get(f"/launches/{launch_id}/trajectory", params={"orbits": orbits})
        response.raise_for_status()
        return response.json()
