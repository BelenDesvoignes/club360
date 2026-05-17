from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.activity import Activity
from app.models.shift_template import ShiftTemplate
from app.models.shift_instance import ShiftInstance
from app.models.booking import Booking
from app.services import shift_service

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
            capacity=s['capacity']
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

    instances = db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).all()
    inst_ids = [i.id for i in instances]

    if inst_ids:
        confirmed_bookings = db.query(Booking).filter(
            Booking.instance_id.in_(inst_ids),
            Booking.status == "Confirmed"
        ).all()

        if confirmed_bookings and not cancel_bookings:
            # Soft delete: desactivar sin tocar reservas
            template.is_active = False
            db.commit()
            return {"message": "Horario desactivado correctamente"}

        # Borrar en orden: bookings → instancias → template
        db.query(Booking).filter(
            Booking.instance_id.in_(inst_ids)
        ).delete(synchronize_session=False)
        db.flush()

        db.query(ShiftInstance).filter(
            ShiftInstance.id.in_(inst_ids)
        ).delete(synchronize_session=False)
        db.flush()

    db.delete(template)
    db.commit()
    return {"message": "Horario eliminado correctamente"}

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
    return {"message": "Actualización exitosa"}

@router.post("/")
def create_activity(data: dict, db: Session = Depends(get_db)):
    print("NAME recibido:", repr(data.get('name')))  # ← acá

    shifts_incoming = data.get('shifts', [])
    seen = set()
    ...