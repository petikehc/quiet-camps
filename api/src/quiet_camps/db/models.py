from datetime import date

from sqlalchemy import ForeignKey, MetaData, String, UniqueConstraint
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

    areas: Mapped[list[CampingArea]] = relationship(back_populates="campground")


class CalendarDay(Base):
    """Every night with its kind, from quiet_camps.ingest.day_kinds: "week 14 6", "easter +1"."""

    __tablename__ = "calendar_day"

    night: Mapped[date] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(index=True)
    holiday: Mapped[str | None]


class CampNight(Base):
    __tablename__ = "camp_night"

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
