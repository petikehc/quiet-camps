from datetime import date
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, MetaData, String, UniqueConstraint, false
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quiet_camps.ingest.clean import State


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Park(Base):
    __tablename__ = "park"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    areas: Mapped[list[CampingArea]] = relationship(back_populates="park")


class CampingArea(Base):
    __tablename__ = "camping_area"
    __table_args__ = (
        UniqueConstraint(
            "park_id",
            "name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    park_id: Mapped[int] = mapped_column(ForeignKey("park.id"))
    # Set after each load by assign_campgrounds; None only in between.
    campground_id: Mapped[int | None] = mapped_column(ForeignKey("campground.id"))

    park: Mapped[Park] = relationship(back_populates="areas")
    campground: Mapped[Campground | None] = relationship(back_populates="areas")


class Campground(Base):
    """One place, under every name it has had: see quiet_camps.ingest.campgrounds."""

    __tablename__ = "campground"
    __table_args__ = (UniqueConstraint("park_key", "area_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    park_key: Mapped[str]
    area_key: Mapped[str]
    # The names from the most recent booking, for display.
    name: Mapped[str]
    park_name: Mapped[str]
    # A third of campgrounds are retired sites or old names: search only recent ones.
    last_night: Mapped[date | None]

    # Where it is, from quiet_camps.ingest.locations. None until `qc locations` has run.
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    location_source: Mapped[str | None]  # osm, park_osm, park_qld or manual
    # Why the location needs a look (weak_name, tie, rejected_osm...); empty when it's clean.
    location_flags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    # The OSM campsite matched, or the one rejected (with the rejected_osm flag).
    osm_type: Mapped[str | None]
    osm_id: Mapped[int | None] = mapped_column(BigInteger)
    osm_name: Mapped[str | None]
    match_score: Mapped[float | None]
    # GeoJSON, for the campgrounds OSM draws as an area.
    osm_outline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    park_outline_id: Mapped[int | None] = mapped_column(ForeignKey("park_outline.id"))

    areas: Mapped[list[CampingArea]] = relationship(back_populates="campground")
    park_outline: Mapped[ParkOutline | None] = relationship()


class ParkOutline(Base):
    """A protected area's boundary (Queensland Government, CC BY 4.0), simplified to ~100 m."""

    __tablename__ = "park_outline"

    # The service's objectid: the table is replaced on every run, so it only has to be unique.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str]
    kind: Mapped[str]  # NP, CP, SF...
    area_ha: Mapped[float]
    # GeoJSON Polygon or MultiPolygon, [lon, lat], ready for a map.
    geometry: Mapped[dict[str, Any]] = mapped_column(JSONB)


class PostcodeCentroid(Base):
    """Roughly where a postcode's campers live: its postal area's centre (ABS, CC BY 4.0)."""

    __tablename__ = "postcode_centroid"

    postcode: Mapped[str] = mapped_column(String(4), primary_key=True)
    lat: Mapped[float]
    lon: Mapped[float]


class Place(Base):
    """A Queensland suburb, town or council area at its centre (ABS, CC BY 4.0): where a camper
    starts from or wants to be near. Parks and campgrounds join these when matching."""

    __tablename__ = "place"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[str]  # locality or council
    lat: Mapped[float]
    lon: Mapped[float]


class CalendarDay(Base):
    """Every night with its kind, from quiet_camps.ingest.day_kinds: "week 14 6", "easter +1"."""

    __tablename__ = "calendar_day"

    night: Mapped[date] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(index=True)
    holiday: Mapped[str | None]
    # A broader kind for when `kind` comes too seldom: "fortnight 26 3", "easter", "christmas".
    # None only before the next refresh fills it.
    fallback_kind: Mapped[str | None]
    # In Queensland's state school holidays, where known (ingest/qld_school_holidays.csv).
    school_holiday: Mapped[bool] = mapped_column(server_default=false())


class CampNight(Base):
    __tablename__ = "camp_night"
    # One campground's bookings over a date range (its lead times) without a 7.8M-row scan.
    __table_args__ = (Index("ix_camp_night_area_id_night", "area_id", "night"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("camping_area.id"))
    night: Mapped[date]
    booked_on: Mapped[date]
    adults: Mapped[int | None]
    children: Mapped[int | None]
    infants: Mapped[int | None]
    postcode: Mapped[str | None] = mapped_column(String(4))
    state: Mapped[State]
    reservation_id: Mapped[str | None]
    source_file: Mapped[str]
