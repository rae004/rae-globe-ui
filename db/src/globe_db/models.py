"""ORM models. Ids are Launch Library 2's own, so a reload updates rows in place."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Pad(Base):
    __tablename__ = "pad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255))
    location_name: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(8))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class Launch(Base):
    __tablename__ = "launch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # "No earlier than": Launch Library 2's name for the planned launch time.
    net: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str | None] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(255))
    rocket: Mapped[str | None] = mapped_column(String(255))
    mission_name: Mapped[str | None] = mapped_column(String(255))
    mission_type: Mapped[str | None] = mapped_column(String(64))
    mission_description: Mapped[str | None] = mapped_column(Text)
    orbit_name: Mapped[str | None] = mapped_column(String(64))
    orbit_abbrev: Mapped[str | None] = mapped_column(String(32))
    # The body the target orbit is around, e.g. "Earth" or "Moon".
    orbit_body: Mapped[str | None] = mapped_column(String(64))
    pad_id: Mapped[int] = mapped_column(ForeignKey("pad.id"))

    pad: Mapped[Pad] = relationship(lazy="joined")
