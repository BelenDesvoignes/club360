from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.activity import Activity
from sqlalchemy import and_
from ..database import get_db
from ..schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut, ShiftDetailResponse
from ..models.shift_template import ShiftTemplate
from ..services import shift_service
from ..time_override import business_today

router = APIRouter(prefix="/shifts", tags=["shifts"])

@router.get("/templates", response_model=List[ShiftTemplateOut])
def get_templates(db: Session = Depends(get_db)):
    return db.query(ShiftTemplate).all()

@router.post("/templates", response_model=ShiftTemplateOut)
def create_template(data: ShiftTemplateCreate, db: Session = Depends(get_db)):
    new_template = ShiftTemplate(**data.dict())
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    shift_service.create_instances_for_month(db, new_template)
    return new_template

@router.put("/templates/{template_id}", response_model=ShiftTemplateOut)
def update_template(template_id: int, data: ShiftTemplateCreate, db: Session = Depends(get_db)):
    updated = shift_service.update_template_and_recreate_instances(db, template_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")
    return updated

@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    shift_service.delete_template_and_instances(db, template_id)
    return {"message": "Turno base y sus clases eliminadas correctamente"}

@router.get("/instances")
def get_instances(db: Session = Depends(get_db)):
    from sqlalchemy import func

    active_templates = (
        db.query(ShiftTemplate)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == True)
        .all()
    )

    booking_count_sq = (
        db.query(
            Booking.instance_id,
            func.count(Booking.id).label('count')
        )
        .filter(Booking.status != "Cancelled")
        .group_by(Booking.instance_id)
        .subquery()
    )

    result = (
        db.query(
            ShiftInstance.id,
            ShiftInstance.date,
            ShiftInstance.is_cancelled,
            ShiftInstance.capacity.label('instance_capacity'),
            ShiftTemplate.id.label('template_id'),
            ShiftTemplate.activity_id,
            ShiftTemplate.day_of_week,
            ShiftTemplate.start_time,
            ShiftTemplate.capacity.label('template_capacity'),
            ShiftTemplate.price,
            Activity.name.label('activity_name'),
            Activity.court.label('court'),
            func.coalesce(booking_count_sq.c.count, 0).label('booked_count')
        )
        .join(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .outerjoin(booking_count_sq, ShiftInstance.id == booking_count_sq.c.instance_id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == True)
        .filter(ShiftInstance.date >= business_today())
        .filter(ShiftInstance.is_cancelled == False)
        .order_by(ShiftInstance.date.asc(), ShiftTemplate.start_time.asc())
        .all()
    )

    instances_list = []
    for row in result:
        instances_list.append({
            "id": row.id,
            "date": str(row.date),
            "is_cancelled": row.is_cancelled,
            "booked_count": row.booked_count if row.booked_count else 0,
            "activity_name": row.activity_name or f"Actividad {row.activity_id}",
            "court": row.court or "",
            "capacity": row.instance_capacity,
            "template": {
                "id": row.template_id,
                "activity_id": row.activity_id,
                "day_of_week": row.day_of_week,
                "start_time": row.start_time,
                "capacity": row.instance_capacity,
                "price": float(row.price) if row.price else 100.0
            }
        })

    return instances_list

@router.get("/instances/{instance_id}", response_model=ShiftDetailResponse)
def get_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    detail = shift_service.get_shift_instance_detail(db, instance_id)
    if not detail:
        raise HTTPException(status_code=404, detail="El detalle del turno no existe")
    return detail


@router.patch("/instances/{instance_id}")
def update_instance_capacity(instance_id: int, capacity: int, db: Session = Depends(get_db)):
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(status_code=404, detail="La clase específica no existe")

    booked_count = db.query(Booking).filter(
        Booking.instance_id == instance_id,
        Booking.status != "Cancelled"
    ).count()

    if capacity < booked_count:
        raise HTTPException(
            status_code=400,
            detail=f"No puedes bajar el cupo a {capacity} porque ya hay {booked_count} personas anotadas."
        )
    instance.capacity = capacity
    db.commit()

    return {"message": "Cupo de la clase actualizado", "new_capacity": instance.capacity}

@router.patch("/instances/{instance_id}/cancel")
def cancel_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(status_code=404, detail="La clase no existe")

    instance.is_cancelled = True
    db.commit()

    return {"message": "Clase cancelada exitosamente", "id": instance_id}

import asyncio
from ..mail import send_shift_cancellation, send_template_cancellation

# ── Cancelar clase puntual ──────────────────────────────────────────
@router.patch("/instances/{instance_id}/cancel")
def cancel_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(status_code=404, detail="La clase no existe")

    active_bookings = (
        db.query(Booking)
        .filter(
            Booking.instance_id == instance_id,
            Booking.status.in_(["Confirmed", "Pending"])
        )
        .all()
    )

    instance.is_cancelled = True
    db.commit()

    if active_bookings:
        template = instance.template
        activity_name = template.activity.name if template and template.activity else "la actividad"
        fecha = instance.date.strftime("%d/%m/%Y")
        hora = template.start_time if template else ""

        for booking in active_bookings:
            user = booking.user
            if user and user.email:
                try:
                    asyncio.run(send_shift_cancellation(
                        email=user.email,
                        nombre=user.first_name,
                        actividad=activity_name,
                        fecha=fecha,
                        hora=hora
                    ))
                except Exception as e:
                    print(f"Error enviando mail a {user.email}: {e}")

    return {
        "message": "Clase cancelada exitosamente",
        "id": instance_id,
        "notified": len(active_bookings)
    }


# ── Cancelar turno completo (template) ─────────────────────────────
@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    activity_name = template.activity.name if template.activity else "la actividad"
    dia = template.day_of_week
    hora = template.start_time

    # Buscar instancias futuras con reservas activas, sin repetir usuarios
    future_instances = (
        db.query(ShiftInstance)
        .filter(
            ShiftInstance.template_id == template_id,
            ShiftInstance.date >= business_today(),
            ShiftInstance.is_cancelled == False
        )
        .all()
    )

    instance_ids = [i.id for i in future_instances]

    users_to_notify = {}  # dict para no notificar dos veces al mismo usuario
    if instance_ids:
        active_bookings = (
            db.query(Booking)
            .filter(
                Booking.instance_id.in_(instance_ids),
                Booking.status.in_(["Confirmed", "Pending"])
            )
            .all()
        )
        for booking in active_bookings:
            user = booking.user
            if user and user.email and user.id_user not in users_to_notify:
                users_to_notify[user.id_user] = user

    # Ejecutar la eliminación
    shift_service.delete_template_and_instances(db, template_id)

    # Mandar mails sin repetir
    for user in users_to_notify.values():
        try:
            asyncio.run(send_template_cancellation(
                email=user.email,
                nombre=user.first_name,
                actividad=activity_name,
                dia=dia,
                hora=hora
            ))
        except Exception as e:
            print(f"Error enviando mail a {user.email}: {e}")

    return {
        "message": "Turno base y sus clases eliminadas correctamente",
        "notified": len(users_to_notify)
    }