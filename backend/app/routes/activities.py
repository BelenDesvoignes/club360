from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database import get_db
from ..models.activity import Activity
from ..models.shift_template import ShiftTemplate
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..services import shift_service, refund_service
from ..time_override import business_today

import asyncio
from ..mail import send_template_cancellation
from datetime import date
from ..models.credit import Credit   # 👈 Import correcto

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("/")
def get_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).options(
        joinedload(Activity.templates)
    ).filter(Activity.is_active == True).all()
    for act in activities:
        act.templates = [t for t in act.templates if t.is_active]
    return activities

@router.get("/inactive")
def get_inactive_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).options(
        joinedload(Activity.templates)
    ).all()

    result = []
    for act in activities:
        inactive_templates = [t for t in act.templates if not t.is_active]
        if inactive_templates:
            act.templates = inactive_templates
            result.append(act)
    return result

@router.post("/")
def create_activity(data: dict, db: Session = Depends(get_db)):
    shifts_incoming = data.get('shifts', [])
    seen = set()
    for s in shifts_incoming:
        key = (s['day_of_week'], s['start_time'])
        if key in seen:
            raise HTTPException(status_code=400, detail=f"Turno repetido en el formulario: {key[0]} {key[1]}")
        seen.add(key)

    activity = db.query(Activity).filter(Activity.name == data['name']).first()
    if not activity:
        raise HTTPException(status_code=404, detail=f"Actividad '{data['name']}' no encontrada")

    for s in shifts_incoming:
        shift_service.validate_unique_shift(db, activity.id, s['day_of_week'], s['start_time'])
        new_template = ShiftTemplate(
            activity_id=activity.id,
            day_of_week=s['day_of_week'],
            start_time=s['start_time'],
            capacity=s['capacity'],
            price=activity.price
        )
        db.add(new_template)
        db.flush()
        shift_service.create_instances_for_month(db, new_template)

    db.commit()
    return {"message": "Turno creado con éxito"}

@router.get("/templates/{template_id}/check-bookings")
def check_template_bookings(template_id: int, db: Session = Depends(get_db)):
    instances = db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).all()
    inst_ids = [i.id for i in instances]
    if not inst_ids:
        return {"has_confirmed_bookings": False, "confirmed_count": 0}

    confirmed_bookings = db.query(Booking).filter(
        Booking.instance_id.in_(inst_ids),
        Booking.status == "Confirmed"
    ).all()

    return {
        "has_confirmed_bookings": bool(confirmed_bookings),
        "confirmed_count": len(confirmed_bookings)
    }

@router.delete("/templates/{template_id}")
def delete_shift_template(
    template_id: int,
    cancel_bookings: bool = False,
    db: Session = Depends(get_db)
):
    template = db.query(ShiftTemplate).filter(
        ShiftTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    activity_name = template.activity.name if template.activity else "la actividad"
    dia = template.day_of_week
    hora = template.start_time

    # Instancias del turno
    all_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id
    ).all()
    all_inst_ids = [i.id for i in all_instances]

    # Usuarios a notificar
    users_to_notify = {}
    if all_inst_ids:
        active_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(all_inst_ids),
            Booking.status.in_(["Confirmed", "Pending"])
        ).all()
        for booking in active_bookings:
            user = booking.user
            if user and user.email and user.id_user not in users_to_notify:
                users_to_notify[user.id_user] = user

    # Reservas activas
    active_bookings = []
    if all_inst_ids:
        active_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(all_inst_ids),
            Booking.status.in_(["Confirmed", "Pending"])
        ).all()

    # CASO 1
    if active_bookings and not cancel_bookings:
        template.is_active = False
        db.commit()
        try:
            _send_template_cancellation_mails(users_to_notify, activity_name, dia, hora)
        except Exception as e:
            print("Error enviando mails:", e)
        return {"message": "Turno desactivado correctamente"}

    # CASO 2
    if active_bookings and cancel_bookings:
        db.query(Booking).filter(
            Booking.instance_id.in_(all_inst_ids)
        ).update({"status": "Cancelled"}, synchronize_session=False)

        for booking in active_bookings:
            instance = db.query(ShiftInstance).filter(
        ShiftInstance.id == booking.instance_id
    ).first()
    if instance:
        refund_service.procesar_reembolso_clase_suelta(db, booking, instance)


        template.is_active = False
        db.commit()

        try:
            _send_template_cancellation_mails(users_to_notify, activity_name, dia, hora)
        except Exception as e:
            print("Error enviando mails:", e)

        return {"message": "Turno eliminado y reservas canceladas con reembolso"}

    # CASO 3
    template.is_active = False
    db.commit()
    return {"message": "Turno eliminado correctamente"}

@router.get("/users/{user_id}/credits")
def get_user_credits(user_id: int, db: Session = Depends(get_db)):
    transactions = db.query(Credit).filter(
        Credit.user_id == user_id
    ).order_by(Credit.created_at.desc()).all()
    return transactions
    
@router.patch("/templates/{template_id}/reactivate")
def reactivate_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    template = db.query(ShiftTemplate).filter(
        ShiftTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Turno no encontrado"
        )

    duplicate = db.query(ShiftTemplate).filter(
        ShiftTemplate.activity_id == template.activity_id,
        ShiftTemplate.day_of_week == template.day_of_week,
        ShiftTemplate.start_time == template.start_time,
        ShiftTemplate.is_active == True,
        ShiftTemplate.id != template.id
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un turno activo con ese día y horario."
        )

    # 🔴 Paso 1: borrar reservas
    db.query(Booking).filter(
        Booking.instance_id.in_(
            db.query(ShiftInstance.id).filter(
                ShiftInstance.template_id == template_id
            )
        )
    ).delete(synchronize_session=False)

    # 🔴 Paso 2: borrar instancias
    db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id
    ).delete(synchronize_session=False)

    # 🔴 Paso 3: reactivar template
    template.is_active = True
    db.commit()

    # 🔴 Paso 4: generar nuevas instancias
    from ..services import shift_service
    shift_service.create_instances_for_month(db, template)

    return {
        "message": "Turno reactivado correctamente"
    }

@router.put("/{activity_id}")
def update_activity(activity_id: int, data: dict, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    activity.name = data['name']
    activity.court = data.get('court', activity.court)
    shifts_incoming = data.get('shifts', [])

    for s_data in shifts_incoming:
        shift_id = s_data.get('id')
        shift_service.validate_unique_shift(db, activity_id, s_data['day_of_week'], s_data['start_time'], shift_id)

        if shift_id:
            template = db.query(ShiftTemplate).filter(ShiftTemplate.id == shift_id).first()
            if template:
                template.day_of_week = s_data['day_of_week']
                template.start_time = s_data['start_time']
                template.capacity = s_data['capacity']
                template.price = s_data.get('price', template.price)

                db.query(ShiftInstance).filter(
                    ShiftInstance.template_id == shift_id,
                    ShiftInstance.date >= date.today(),
                    ShiftInstance.is_cancelled == False
                ).update({"capacity": s_data['capacity']})
        else:
            new_template = ShiftTemplate(
                activity_id=activity_id,
                day_of_week=s_data['day_of_week'],
                start_time=s_data['start_time'],
                capacity=s_data['capacity']
            )
            db.add(new_template)
            db.flush()
            shift_service.create_instances_for_month(db, new_template)

    db.commit()
    return {"message": "Turno actualizado"}

@router.patch("/{activity_id}/price")
def update_activity_price(activity_id: int, price: float, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    if price < 1:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor o igual que 1")

    activity.price = price  # ← actualiza en Activity

    templates = db.query(ShiftTemplate).filter(ShiftTemplate.activity_id == activity_id).all()
    for t in templates:
        t.price = price  # ← sincroniza templates existentes

    db.commit()
    return {"message": "Precio actualizado", "price": price}