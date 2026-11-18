from datetime import date

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quiet_camps.ingest.clean import State


class Base(DeclarativeBase):
    pass


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

    park: Mapped[Park] = relationship(back_populates="areas")


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
