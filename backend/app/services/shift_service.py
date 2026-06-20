from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.activity import Activity
from ..models.booking import Booking
from ..models.shift_instance import ShiftInstance
from ..models.shift_template import ShiftTemplate


def _last_day_of_month(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _first_day_of_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _normalize_day_of_week(value: str | None) -> str | None:
    if not value:
        return None

    v = str(value).strip()
    # Defensive: tolerate values stored/typed without accents.
    if v == "Miercoles":
        return "Miércoles"
    if v == "Sabado":
        return "Sábado"
    return v


def create_instances_for_month(db: Session, template: ShiftTemplate, *, commit: bool = True):
    """Ensure weekly ShiftInstances exist for the remainder of this month + next month.

    IMPORTANT: uses real date (`date.today()`), not business_today().
    Idempotent: creates missing instances and updates capacity safely.
    """

    days_map = {
        "Lunes": 0,
        "Martes": 1,
        "Miércoles": 2,
        "Miercoles": 2,
        "Jueves": 3,
        "Viernes": 4,
        "Sábado": 5,
        "Sabado": 5,
        "Domingo": 6,
    }

    normalized_day = _normalize_day_of_week(template.day_of_week)
    target_day = days_map.get(normalized_day)
    if target_day is None:
        return []

    today = date.today()
    start = today
    end = _last_day_of_month(_first_day_of_next_month(today))

    # Find the first occurrence in [start..end]
    cursor = start
    while cursor.weekday() != target_day:
        cursor += timedelta(days=1)
        if cursor > end:
            return []

    found_dates: list[date] = []
    while cursor <= end:
        found_dates.append(cursor)
        cursor += timedelta(days=7)

    if not found_dates:
        return []

    existing = (
        db.query(ShiftInstance)
        .filter(
            ShiftInstance.template_id == template.id,
            ShiftInstance.date >= start,
            ShiftInstance.date <= end,
        )
        .all()
    )
    existing_by_date = {inst.date: inst for inst in existing}

    new_instances: list[ShiftInstance] = []
    for instance_date in found_dates:
        inst = existing_by_date.get(instance_date)
        if inst is None:
            db_instance = ShiftInstance(
                template_id=template.id,
                date=instance_date,
                capacity=template.capacity,
                is_cancelled=False,
            )
            db.add(db_instance)
            new_instances.append(db_instance)
            continue

        # Update capacity only if safe (never below booked count)
        booked_count = (
            db.query(Booking)
            .filter(
                Booking.instance_id == inst.id,
                Booking.status != "Cancelled",
            )
            .count()
        )
        if template.capacity >= booked_count:
            inst.capacity = template.capacity

    if commit:
        db.commit()
    else:
        db.flush()

    return new_instances


def delete_template_and_instances(db: Session, template_id: int):
    # Delete instances that have no active bookings
    instances_with_bookings = db.query(Booking.instance_id).filter(Booking.status != "Cancelled")

    db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ~ShiftInstance.id.in_(instances_with_bookings),
    ).delete(synchronize_session=False)

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if template:
        try:
            db.delete(template)
            db.commit()
        except Exception:
            db.rollback()
            # Best-effort: keep template if historical instances/bookings still reference it.
            raise HTTPException(
                status_code=400,
                detail="No se pudo borrar el template porque tiene clases con reservas históricas.",
            )


def update_template_and_recreate_instances(db: Session, template_id: int, new_data):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        return None

    template.day_of_week = new_data.day_of_week
    template.start_time = new_data.start_time
    template.capacity = new_data.capacity
    db.commit()

    # Re-generate instances for the remainder of the current month.
    create_instances_for_month(db, template)

    return template


def get_shift_instance_detail(db: Session, instance_id: int):
    row = (
        db.query(
            ShiftInstance.id,
            Activity.name.label("activity_name"),
            Activity.court,
            ShiftInstance.date,
            ShiftTemplate.start_time,
            ShiftTemplate.capacity,
            ShiftInstance.is_cancelled,
        )
        .join(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .filter(ShiftInstance.id == instance_id)
        .first()
    )

    if not row:
        return None

    return {
        "id": row.id,
        "activity_name": row.activity_name,
        "court": row.court,
        "date": str(row.date),
        "start_time": row.start_time,
        "capacity": row.capacity,
        "is_cancelled": row.is_cancelled,
    }


def validate_unique_shift(db: Session, activity_id, day_of_week, start_time, exclude_id=None):
    duplicate = (
        db.query(ShiftTemplate)
        .filter(
            ShiftTemplate.activity_id == activity_id,
            ShiftTemplate.day_of_week == day_of_week,
            ShiftTemplate.start_time == start_time,
            ShiftTemplate.id != exclude_id,
            ShiftTemplate.is_active == True,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=400,
            detail="Este turno ya existe",
        )


def reactivate_inactive_shift(db: Session, activity_id, shift_data: dict, price: float | None = None):
    template = (
        db.query(ShiftTemplate)
        .filter(
            ShiftTemplate.activity_id == activity_id,
            ShiftTemplate.day_of_week == shift_data["day_of_week"],
            ShiftTemplate.start_time == shift_data["start_time"],
            ShiftTemplate.is_active == False,
        )
        .first()
    )

    if not template:
        return None

    template.capacity = shift_data["capacity"]
    template.price = price if price is not None else template.price
    template.is_active = True

    db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template.id,
        ShiftInstance.date >= date.today(),
    ).update(
        {
            "capacity": shift_data["capacity"],
            "is_cancelled": False,
        },
        synchronize_session=False,
    )

    db.flush()
    create_instances_for_month(db, template, commit=False)
    return template
