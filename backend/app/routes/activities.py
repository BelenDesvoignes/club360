from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database import get_db

# Importar modelos directamente desde sus archivos
from app.models.user import User
from app.models.activity import Activity
from app.models.booking import Booking
from app.models.shift_instance import ShiftInstance
from app.models.shift_template import ShiftTemplate

# Servicios y utilidades
from ..services import shift_service
from ..time_override import business_today
from ..mail import send_template_cancellation, send_price_update

import asyncio
from datetime import date, datetime

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("/")
def get_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).options(
        joinedload(Activity.templates)
    ).filter(Activity.is_active == True).all()
    for act in activities:
        act.templates = [t for t in act.templates if t.is_active]
    return activities

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
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    activity_name = template.activity.name if template.activity else "la actividad"
    dia = template.day_of_week
    hora = template.start_time

    future_instances = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == template_id,
        ShiftInstance.date >= business_today(),
        ShiftInstance.is_cancelled == False
    ).all()
    inst_ids = [i.id for i in future_instances]

    users_to_notify = {}
    if inst_ids:
        active_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(inst_ids),
            Booking.status.in_(["Confirmed", "Pending"])
        ).all()

        for booking in active_bookings:
            user = booking.user
            if user and user.email and user.id_user not in users_to_notify:
                users_to_notify[user.id_user] = user

    all_instances = db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).all()
    all_inst_ids = [i.id for i in all_instances]

    if all_inst_ids:
        confirmed_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(all_inst_ids),
            Booking.status == "Confirmed"
        ).all()

        if confirmed_bookings and not cancel_bookings:
            template.is_active = False
            db.commit()
            _send_template_cancellation_mails(users_to_notify, activity_name, dia, hora)
            return {"message": "Horario desactivado correctamente"}

        db.query(Booking).filter(
            Booking.instance_id.in_(all_inst_ids)
        ).delete(synchronize_session=False)
        db.flush()

        db.query(ShiftInstance).filter(
            ShiftInstance.id.in_(all_inst_ids)
        ).delete(synchronize_session=False)
        db.flush()

    db.delete(template)
    db.commit()
    _send_template_cancellation_mails(users_to_notify, activity_name, dia, hora)

    return {"message": "Horario eliminado correctamente"}


def _send_template_cancellation_mails(users_to_notify: dict, activity_name: str, dia: str, hora: str):
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
def update_activity_price(
    activity_id: int,
    price: float,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    print("➡️ Precio recibido:", price)

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    print("➡️ Actividad encontrada:", activity.name)

    if price < 1:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor o igual que 1")

    activity.price = price
    templates = db.query(ShiftTemplate).filter(ShiftTemplate.activity_id == activity_id).all()
    for t in templates:
        t.price = price
    db.commit()
    print("➡️ Precio actualizado en actividad y templates")

    print("➡️ Tipo de business_today:", type(business_today()))
    print("➡️ Valor de business_today:", business_today())

    filtro_fecha = business_today().date() if isinstance(business_today(), datetime) else business_today()

    inscriptos = (
    db.query(User)
    .join(Booking, Booking.user_id == User.id_user)
    .join(ShiftInstance, ShiftInstance.id == Booking.instance_id)
    .join(ShiftTemplate, ShiftTemplate.id == ShiftInstance.template_id)
    .join(Activity, Activity.id == ShiftTemplate.activity_id)
    .filter(
        Activity.id == activity.id,
        Activity.is_active == True,              # actividad activa
        ShiftTemplate.is_active == True,         # turno activo
        Booking.status.in_(["Confirmed", "Pending"]),
        ShiftInstance.date >= filtro_fecha,      # fecha futura
        ShiftInstance.is_cancelled == False
    )
    .distinct(User.id_user)
    .all()
)


    for user in inscriptos:
        try:
            background_tasks.add_task(
                send_price_update,
                email=user.email,
                nombre=user.first_name,
                actividad=activity.name,
                nuevo_precio=activity.price
            )
            print("➡️ Mail agendado para:", user.email)
        except Exception as e:
            print("Error enviando mail a", user.email, ":", e)