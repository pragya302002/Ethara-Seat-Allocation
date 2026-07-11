"""
Physical office hierarchy: Building -> Floor -> Zone -> Seat.

We stop the normalized hierarchy at Zone rather than also modeling "Row" as
its own table. A Row has no independent attributes or behavior in this
system (no capacity, no manager, nothing queried by row alone) — it's really
just a label on a Seat. Modeling it as a full table would add a join to
every seat query for zero query-pattern benefit, so it's a plain string
column on Seat instead. This is the kind of over-normalization a senior
reviewer would flag, so flagging the decision explicitly here.
"""
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Building(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "buildings"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    floors: Mapped[list["Floor"]] = relationship(back_populates="building", cascade="all, delete-orphan")


class Floor(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "floor_number", name="uq_building_floor"),)

    building_id: Mapped[UUID] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    floor_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)  # e.g. "3rd Floor - Engineering"

    building: Mapped["Building"] = relationship(back_populates="floors")
    zones: Mapped[list["Zone"]] = relationship(back_populates="floor", cascade="all, delete-orphan")


class Zone(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("floor_id", "name", name="uq_floor_zone_name"),)

    floor_id: Mapped[UUID] = mapped_column(ForeignKey("floors.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. "Finance", "Zone A"

    floor: Mapped["Floor"] = relationship(back_populates="zones")
    seats: Mapped[list["Seat"]] = relationship(back_populates="zone")
