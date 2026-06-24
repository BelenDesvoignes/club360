from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, String
from sqlalchemy.orm import Session

# Importaciones del proyecto (Modelos)
from ..models.activity import Activity
from ..models.booking import Booking
from ..models.payment import Payment
from ..models.shift_instance import ShiftInstance
from ..models.shift_template import ShiftTemplate
from ..models.subscription import Subscription

from ..time_override import business_utcnow
from .credit_service import otorgar_credito_individual
from .refund_service import procesar_reembolso_clase_suelta



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
            ShiftInstance.is_cancelled == False,
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

def delete_template_and_instances_logic(db: Session, template: ShiftTemplate, future_instances: list, cancel_all_instances: bool = True):
    """
    Ejecuta el flujo ordenado de desactivación lógica adaptándose a la opción elegida.
    """
    procesar_devoluciones_por_eliminacion_de_template(db, template.id, future_instances, cancel_all_instances)

    for instance in future_instances:
        instance.is_cancelled = True

    template.is_active = False

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la baja lógica del turno: {str(e)}"
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
        )
        .first()
    )

    if duplicate:
        detail = "Este turno ya existe"
        if not duplicate.is_active:
            detail = "Este turno fue eliminado. Para volver a usarlo, reactiválo desde la tabla de turnos eliminados."

        raise HTTPException(
            status_code=400,
            detail=detail,
        )
    
def procesar_devoluciones_por_cancelacion_de_clase(db: Session, active_bookings: list, instance: ShiftInstance):
    """
    Recorre todas las reservas activas de una clase cancelada por el club
    y ejecuta las devoluciones correspondientes de forma incondicional
    según el estado real del pago. Compatible con PostgreSQL y SQLite.
    """
    for booking in active_bookings:
        has_subscription = booking.subscription_id is not None
        monto_pagado = float(booking.amount_paid) if booking.amount_paid is not None else 0.0
        estado_pago = getattr(booking, 'payment_status', None)
        
        activity_id = instance.template.activity_id if instance.template else 1

        # ── 1. CASO ABONADOS ──
        if has_subscription:
            sub = booking.subscription
            
            # Traemos los pagos pendientes de suscripción de este usuario a memoria
            pagos_pendientes = db.query(Payment).filter(
                Payment.user_id == booking.user_id,
                Payment.type == "subscription",
                Payment.status == "pending"
            ).all()

            # Comparamos las fechas de forma segura en Python
            deuda_pendiente = None
            if sub and sub.purchase_date:
                for p in pagos_pendientes:
                    if p.date:
                        # Quitamos zonas horarias si existen para evitar líos al restar
                        p_date_naive = p.date.replace(tzinfo=None)
                        sub_date_naive = sub.purchase_date.replace(tzinfo=None)
                        
                        if abs((p_date_naive - sub_date_naive).total_seconds()) <= 5:
                            deuda_pendiente = p
                            break

            # Si NO tiene deuda pendiente, el abono está pagado -> Le corresponde crédito
            if deuda_pendiente is None:
                otorgar_credito_individual(db, user_id=booking.user_id, activity_id=activity_id)

        # ── 2. CASO RESERVA CON CRÉDITO PREVIO (No es abono, monto 0 y pagado) ──
        elif not has_subscription and monto_pagado == 0.0 and estado_pago == "paid":
            otorgar_credito_individual(db, user_id=booking.user_id, activity_id=activity_id)
            
        # ── 3. CASO CLASE SUELTA (Dinero real: seña o total) ──
        elif not has_subscription and monto_pagado > 0.0:
            procesar_reembolso_clase_suelta(db, booking, instance)
            
        booking.status = "Cancelled"
    
    db.commit()


def procesar_devoluciones_por_eliminacion_de_template(db: Session, template_id: int, future_instances: list, cancel_all_instances: bool):
    """
    Cancela y reembolsa de forma masiva todas las reservas e inscripciones afectadas.
    """
    if cancel_all_instances:
        abonos_afectados = db.query(Subscription).filter(Subscription.template_id == template_id).all()

        for sub in abonos_afectados:
            pagos_pendientes = db.query(Payment).filter(
                Payment.user_id == sub.user_id,
                Payment.type == "subscription",
                Payment.status == "pending"
            ).all()

            deuda_pendiente = None
            if sub.purchase_date:
                for p in pagos_pendientes:
                    if p.date:
                        p_date_naive = p.date.replace(tzinfo=None)
                        sub_date_naive = sub.purchase_date.replace(tzinfo=None)
                        
                        if abs((p_date_naive - sub_date_naive).total_seconds()) <= 5:
                            deuda_pendiente = p
                            break

            if deuda_pendiente is None:
                monto_a_devolver = float(sub.price_paid) if sub.price_paid is not None else 0.0
                if monto_a_devolver > 0.0:
                    refund_sub = Payment(
                        user_id=sub.user_id,
                        amount=monto_a_devolver,
                        status="completed",
                        type="refund_total",
                        date=business_utcnow()
                    )
                    db.add(refund_sub)
                sub.status = "refunded"
            else:
                sub.status = "cancelled"
                deuda_pendiente.status = "cancelled"

    for instance in future_instances:
        active_bookings = db.query(Booking).filter(
            Booking.instance_id == instance.id,
            Booking.status != "Cancelled"
        ).all()

        for booking in active_bookings:
            activity_id = instance.template.activity_id if instance.template else 1

            if booking.subscription_id is None:
                if float(booking.amount_paid or 0.0) == 0.0 and booking.payment_status == "paid":
                    otorgar_credito_individual(db, user_id=booking.user_id, activity_id=activity_id)
                elif float(booking.amount_paid or 0.0) > 0.0:
                    procesar_reembolso_clase_suelta(db, booking, instance)

            booking.status = "Cancelled"
