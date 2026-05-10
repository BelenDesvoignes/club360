from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
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
@router.put("/{activity_id}")
def update_activity(activity_id: int, data: dict, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    activity.name = data['name']
    activity.court = data['court']

    shifts_incoming = data.get('shifts', [])
    
    seen = set()
    for s in shifts_incoming:
        key = (s['day_of_week'], s['start_time'])
        if key in seen:
            raise HTTPException(status_code=400, detail=f"Turno duplicado en el formulario: {key[0]} {key[1]}")
        seen.add(key)

    current_templates = db.query(ShiftTemplate).filter(ShiftTemplate.activity_id == activity_id).all()
    current_templates_dict = {t.id: t for t in current_templates}
    incoming_ids = [s.get('id') for s in shifts_incoming if s.get('id')]

    for old_id, template in current_templates_dict.items():
        if old_id not in incoming_ids:
            instances = db.query(ShiftInstance).filter(ShiftInstance.template_id == old_id).all()
            inst_ids = [i.id for i in instances]
            
            if inst_ids:
                has_bookings = db.query(Booking).filter(Booking.instance_id.in_(inst_ids)).first()
                if has_bookings:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"No se puede borrar el turno {template.day_of_week} {template.start_time} (tiene reservas)."
                    )
                db.query(ShiftInstance).filter(ShiftInstance.id.in_(inst_ids)).delete(synchronize_session=False)
            
            db.delete(template)

    for s_data in shifts_incoming:
        shift_id = s_data.get('id')

        shift_service.validate_unique_shift(db, activity_id, s_data['day_of_week'], s_data['start_time'], shift_id)

        if shift_id and shift_id in current_templates_dict:
            template = current_templates_dict[shift_id]
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
    return {"message": "Sincronización completada"}

# 4. Borrar (DELETE )
@router.delete("/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    activity.is_active = False 
    db.commit()
    return {"message": "Borrada"}