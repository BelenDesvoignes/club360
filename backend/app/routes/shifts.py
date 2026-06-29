from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.activity import Activity
from sqlalchemy import and_, or_
from ..database import get_db
from ..schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut, ShiftDetailResponse
from ..models.shift_template import ShiftTemplate
from ..models.waiting_list import WaitingList
from ..services import shift_service
from ..time_override import business_today, business_utcnow

router = APIRouter(prefix="/shifts", tags=["shifts"])

@router.get("/templates", response_model=List[ShiftTemplateOut])
def get_templates(db: Session = Depends(get_db)):
    return db.query(ShiftTemplate).all()

@router.get("/templates/inactive")
def get_inactive_templates(db: Session = Depends(get_db)):
    inactive_templates = (
        db.query(ShiftTemplate)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == False)
        .order_by(Activity.name.asc(), ShiftTemplate.day_of_week.asc(), ShiftTemplate.start_time.asc())
        .all()
    )

    return [
        {
            "id": template.id,
            "templateId": template.id,
            "activity_id": template.activity_id,
            "name": template.activity.name if template.activity else f"Actividad {template.activity_id}",
            "court": template.activity.court if template.activity else "",
            "day": template.day_of_week,
            "time": template.start_time,
            "capacity": template.capacity,
            "price": float(template.price) if template.price is not None else None,
        }
        for template in inactive_templates
    ]

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

@router.get("/templates/{template_id}/check-bookings")
def check_template_bookings(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    future_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ShiftInstance.date >= business_today(),
        ShiftInstance.is_cancelled == False
    ).all()

    instance_ids = [instance.id for instance in future_instances]
    if not instance_ids:
        return {
            "has_active_bookings": False,
            "has_confirmed_bookings": False,
            "active_count": 0,
            "confirmed_count": 0,
        }

    active_bookings = db.query(Booking).filter(
        Booking.instance_id.in_(instance_ids),
        Booking.status != "Cancelled"
    ).all()

    confirmed_count = sum(1 for booking in active_bookings if booking.status == "Confirmed")

    return {
        "has_active_bookings": bool(active_bookings),
        "has_confirmed_bookings": confirmed_count > 0,
        "active_count": len(active_bookings),
        "confirmed_count": confirmed_count,
    }

@router.patch("/templates/{template_id}/reactivate")
def reactivate_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    # 🔹 Validar que no exista un turno activo con mismos datos
    exists_active = db.query(ShiftTemplate).filter(
        ShiftTemplate.activity_id == template.activity_id,
        ShiftTemplate.day_of_week == template.day_of_week,
        ShiftTemplate.start_time == template.start_time,
        ShiftTemplate.is_active == True
    ).first()

    if exists_active:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un turno activo con los mismos datos"
        )

    # Si no existe, se puede reactivar
    template.is_active = True
    created_instances = shift_service.create_instances_for_month(db, template, commit=False)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al reactivar el turno: {str(e)}"
        )

    return {
        "message": "Turno reactivado correctamente.",
        "created_instances": len(created_instances),
    }

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

    now = business_utcnow()
    active_waiting_sq = (
        db.query(
            WaitingList.instance_id,
            func.count(WaitingList.id).label('count')
        )
        .filter(
            or_(
                WaitingList.status == "waiting",
                and_(
                    WaitingList.status == "notified",
                    or_(
                        WaitingList.promotion_expires_at == None,
                        WaitingList.promotion_expires_at >= now,
                    ),
                ),
            )
        )
        .group_by(WaitingList.instance_id)
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
            func.coalesce(booking_count_sq.c.count, 0).label('booked_count'),
            func.coalesce(active_waiting_sq.c.count, 0).label('active_waiting_count')
        )
        .join(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .outerjoin(booking_count_sq, ShiftInstance.id == booking_count_sq.c.instance_id)
        .outerjoin(active_waiting_sq, ShiftInstance.id == active_waiting_sq.c.instance_id)
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
            "has_active_waiting_queue": bool(row.active_waiting_count),
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

import asyncio
from ..mail import send_shift_cancellation, send_template_cancellation


@router.delete("/templates/{template_id}/safe-clean")
def delete_empty_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    # 1. Buscar todas las instancias futuras
    future_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ShiftInstance.date >= business_today(),
        ShiftInstance.is_cancelled == False
    ).all()

    # 2. Validar que NINGUNA tenga inscriptos
    instance_ids = [i.id for i in future_instances]
    if instance_ids:
        has_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(instance_ids),
            Booking.status != "Cancelled"
        ).first() is not None
        
        if has_bookings:
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar: el turno tiene clases futuras con alumnos inscriptos."
            )

    # 3. Como está vacío, apagamos todo sin procesar reembolsos (porque no hay nadie)
    for instance in future_instances:
        instance.is_cancelled = True
    template.is_active = False
    
    db.commit()
    return {"message": "Turno eliminado correctamente."}

@router.delete("/templates/{template_id}/keep-active-classes")
def delete_template_keeping_inscriptions(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    all_future_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ShiftInstance.date >= business_today(),
        ShiftInstance.is_cancelled == False
    ).all()

    instances_to_cancel = []

    for instance in all_future_instances:
        has_bookings = db.query(Booking).filter(
            Booking.instance_id == instance.id,
            Booking.status != "Cancelled"
        ).first() is not None

        if not has_bookings:
            instances_to_cancel.append(instance)

    shift_service.delete_template_and_instances_logic(
        db, template, instances_to_cancel, cancel_all_instances=False
    )

    return {"message": "Turno eliminado correctamente. Las clases con inscriptos se mantendrán activas."}

@router.delete("/templates/{template_id}/cancel-everything")
def delete_template_and_cancel_all(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")

    activity_name = template.activity.name if template.activity else "la actividad"
    dia = template.day_of_week
    hora = template.start_time

    future_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ShiftInstance.date >= business_today(),
        ShiftInstance.is_cancelled == False
    ).all()

    instance_ids = [i.id for i in future_instances]
    users_to_notify = {}
    if instance_ids:
        active_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(instance_ids),
            Booking.status != "Cancelled"
        ).all()
        for booking in active_bookings:
            user = booking.user
            if user and user.email and user.id_user not in users_to_notify:
                users_to_notify[user.id_user] = user

    # LLAMADA AL SERVICIO: Procesar abonos pagados y clases sueltas (cancel_all_instances=True)
    shift_service.delete_template_and_instances_logic(
        db, template, future_instances, cancel_all_instances=True
    )

    # Enviar notificaciones por mail
    for user in users_to_notify.values():
        try:
            asyncio.run(send_template_cancellation(
                email=user.email, nombre=user.first_name, actividad=activity_name, dia=dia, hora=hora
            ))
        except Exception as e:
            print(f"Error enviando mail a {user.email}: {e}")

    return {"message": "Turno eliminado correctamente. Reembolsos procesados con éxito."}


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
            Booking.status != "Cancelled"
        )
        .all()
    )

    # Ejecutar devoluciones antes de cerrar la clase
    if active_bookings:
        shift_service.procesar_devoluciones_por_cancelacion_de_clase(db, active_bookings, instance)

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
        "message": "Clase cancelada y usuarios reembolsados exitosamente",
        "id": instance_id,
        "notified": len(active_bookings)
    }
