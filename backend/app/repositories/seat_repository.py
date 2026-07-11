import uuid
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.enums import SeatStatus
from app.models.seat import Seat, SeatAllocation
from app.repositories.base import BaseRepository


class SeatRepository(BaseRepository[Seat]):
    model = Seat

    async def list_vacant(self, zone_id: uuid.UUID | None = None, floor_id: uuid.UUID | None = None) -> list[Seat]:
        from app.models.location import Zone  # local import to avoid circularity

        stmt = select(Seat).where(Seat.status == SeatStatus.VACANT)
        if zone_id:
            stmt = stmt.where(Seat.zone_id == zone_id)
        if floor_id:
            stmt = stmt.join(Zone, Seat.zone_id == Zone.id).where(Zone.floor_id == floor_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_allocation_for_seat(self, seat_id: uuid.UUID) -> SeatAllocation | None:
        stmt = select(SeatAllocation).where(
            SeatAllocation.seat_id == seat_id, SeatAllocation.release_date.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_active_allocation_for_employee(self, employee_id: uuid.UUID) -> SeatAllocation | None:
        stmt = select(SeatAllocation).where(
            SeatAllocation.employee_id == employee_id, SeatAllocation.release_date.is_(None)
        ).options(selectinload(SeatAllocation.seat))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_history_for_seat(self, seat_id: uuid.UUID) -> list[SeatAllocation]:
        stmt = (
            select(SeatAllocation)
            .where(SeatAllocation.seat_id == seat_id)
            .order_by(SeatAllocation.allocation_date.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_history_for_employee(self, employee_id: uuid.UUID) -> list[SeatAllocation]:
        stmt = (
            select(SeatAllocation)
            .where(SeatAllocation.employee_id == employee_id)
            .order_by(SeatAllocation.allocation_date.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_allocation(self, allocation: SeatAllocation) -> SeatAllocation:
        self.db.add(allocation)
        await self.db.flush()
        await self.db.refresh(allocation)
        return allocation

    async def floor_utilization(self) -> list[dict]:
        """Powers dashboard's 'Floor Utilization' / heat map data. Uses two
        simple grouped queries (totals, then occupied) rather than one
        conditional-aggregate query — conditional SUM/CASE syntax varies
        subtly across SQL dialects, and this is easier to read and safer
        against a driver upgrade than getting that cast exactly right."""
        from app.models.location import Building, Floor, Zone

        total_stmt = (
            select(Building.name, Floor.floor_number, func.count(Seat.id))
            .join(Zone, Seat.zone_id == Zone.id)
            .join(Floor, Zone.floor_id == Floor.id)
            .join(Building, Floor.building_id == Building.id)
            .group_by(Building.name, Floor.floor_number)
        )
        occupied_stmt = total_stmt.where(Seat.status == SeatStatus.OCCUPIED)

        totals = {(b, f): c for b, f, c in (await self.db.execute(total_stmt)).all()}
        occupied = {(b, f): c for b, f, c in (await self.db.execute(occupied_stmt)).all()}

        results = []
        for (building, floor_num), total in totals.items():
            occ = occupied.get((building, floor_num), 0)
            results.append({
                "building": building,
                "floor": floor_num,
                "total_seats": total,
                "occupied_seats": occ,
                "utilization_percent": round((occ / total) * 100, 1) if total else 0.0,
            })
        return sorted(results, key=lambda r: (r["building"], r["floor"]))

    async def recent_allocations(self, limit: int = 10) -> list[SeatAllocation]:
        stmt = (
            select(SeatAllocation)
            .where(SeatAllocation.event_type.in_(["allocate", "transfer"]))
            .order_by(SeatAllocation.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def recent_releases(self, limit: int = 10) -> list[SeatAllocation]:
        stmt = (
            select(SeatAllocation)
            .where(SeatAllocation.release_date.is_not(None))
            .order_by(SeatAllocation.updated_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_vacant_by_floor_number(self, floor_number: int) -> int:
        from app.models.location import Floor, Zone

        stmt = (
            select(func.count())
            .select_from(Seat)
            .join(Zone, Seat.zone_id == Zone.id)
            .join(Floor, Zone.floor_id == Floor.id)
            .where(Floor.floor_number == floor_number, Seat.status == SeatStatus.VACANT)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def get_zone_neighbors(self, employee_id: uuid.UUID) -> tuple[str | None, list[str]]:
        """Returns (zone_name, [names of other employees currently seated in
        the same zone]) — backs 'Who sits beside John?' style queries."""
        from app.models.employee import Employee

        active = await self.get_active_allocation_for_employee(employee_id)
        if active is None:
            return None, []

        seat = await self.get_by_id(active.seat_id)
        zone_stmt = select(Seat.id).where(Seat.zone_id == seat.zone_id, Seat.id != seat.id)
        seat_ids_in_zone = [row[0] for row in (await self.db.execute(zone_stmt)).all()]
        if not seat_ids_in_zone:
            return None, []

        neighbor_stmt = (
            select(Employee.full_name)
            .join(SeatAllocation, SeatAllocation.employee_id == Employee.id)
            .where(SeatAllocation.seat_id.in_(seat_ids_in_zone), SeatAllocation.release_date.is_(None))
        )
        names = [row[0] for row in (await self.db.execute(neighbor_stmt)).all()]
        from app.models.location import Zone

        zone = await self.db.get(Zone, seat.zone_id)
        return (zone.name if zone else None), names

    async def occupancy_summary(self) -> dict:
        """Powers the dashboard's Total/Occupied/Vacant/Utilization % cards
        in a single grouped query rather than 3 separate COUNT calls."""
        stmt = select(Seat.status, func.count()).group_by(Seat.status)
        rows = (await self.db.execute(stmt)).all()
        counts = {status.value: 0 for status in SeatStatus}
        for status, count in rows:
            counts[status.value] = count
        total = sum(counts.values())
        utilization = round((counts[SeatStatus.OCCUPIED.value] / total) * 100, 1) if total else 0.0
        return {**counts, "total": total, "utilization_percent": utilization}
