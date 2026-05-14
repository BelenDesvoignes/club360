from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.activity import Activity
from app.models.shift_template import ShiftTemplate
from app.models.shift_instance import ShiftInstance
from app.models.booking import Booking
from app.services import shift_service  # Tu servicio con la lógica de negocio

router = APIRouter(prefix="/activities", tags=["activities"])

# 1. Obtener todas las actividades (READ)
@router.get("/")
def get_activities(db: Session = Depends(get_db)):
    return db.query(Activity).options(joinedload(Activity.templates)).filter(Activity.is_active == True).all()

# 2. Crear (POST)
@router.post("/")
def create_activity(data: dict, db: Session = Depends(get_db)):
    shifts_incoming = data.get('shifts', [])

    seen = set()
    for s in shifts_incoming:
        key = (s['day_of_week'], s['start_time'])
        if key in seen:
            raise HTTPException(status_code=400, detail=f"Turno repetido en el formulario: {key[0]} {key[1]}")
        seen.add(key)

    new_activity = Activity(name=data['name'], court=data.get('court', ''))
    db.add(new_activity)
    db.flush()

    for s in shifts_incoming:
        shift_service.validate_unique_shift(db, new_activity.id, s['day_of_week'], s['start_time'])

        new_template = ShiftTemplate(
            activity_id=new_activity.id,
            day_of_week=s['day_of_week'],
            start_time=s['start_time'],
            capacity=s['capacity']
        )
        db.add(new_template)
        db.flush()
        shift_service.create_instances_for_month(db, new_template)

    db.commit()
    return {"message": "Actividad creada con éxito"}

# 3. Editar (UPDATE )
# 3. Editar (UPDATE) - Versión compatible con formulario de un solo turno
@router.put("/{activity_id}")
def update_activity(activity_id: int, data: dict, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    # 1. Actualizamos datos básicos de la actividad
    activity.name = data['name']
    activity.court = data.get('court', activity.court)

    shifts_incoming = data.get('shifts', [])

    # 2. Procesamos los turnos que vienen en el payload
    for s_data in shifts_incoming:
        shift_id = s_data.get('id') # Intentamos obtener el ID del template

        # Validamos que no choque con otro turno existente de la misma actividad
        shift_service.validate_unique_shift(db, activity_id, s_data['day_of_week'], s_data['start_time'], shift_id)

        if shift_id:
            # Si tiene ID, actualizamos el registro existente
            template = db.query(ShiftTemplate).filter(ShiftTemplate.id == shift_id).first()
            if template:
                template.day_of_week = s_data['day_of_week']
                template.start_time = s_data['start_time']
                template.capacity = s_data['capacity']
        else:
            # Si no tiene ID (es un turno nuevo agregado a la actividad), lo creamos
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

# 4. Borrar (DELETE )
# Nuevo endpoint para eliminar un horario específico
@router.delete("/templates/{template_id}")
def delete_shift_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # 1. Buscar si hay instancias de este turno
    instances = db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).all()
    inst_ids = [i.id for i in instances]

    if inst_ids:
        # 2. Verificar si alguna instancia tiene reservas
        has_bookings = db.query(Booking).filter(Booking.instance_id.in_(inst_ids)).first()
        if has_bookings:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el turno porque ya tiene reservas asociadas."
            )

        # 3. Borrar instancias si están limpias
        db.query(ShiftInstance).filter(ShiftInstance.id.in_(inst_ids)).delete(synchronize_session=False)

    # 4. Borrar el template
    db.delete(template)
    db.commit()
    return {"message": "Horario eliminado correctamente"}