"""Database settings, engine and session handling."""

from collections.abc import Iterator
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class DbSettings(BaseSettings):
    """Read from the environment, falling back to the root ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "globe"
    postgres_password: str = "globe"
    postgres_db: str = "globe"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_engine() -> Engine:
    return create_engine(DbSettings().url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Yield a session that commits on success and rolls back on error."""
    with sessionmaker(get_engine(), expire_on_commit=False).begin() as session:
        yield session
