from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.activity import Activity
from ..models.shift_template import ShiftTemplate

router = APIRouter(prefix="/activities", tags=["activities"])

# 1. Obtener todas las actividades (READ)
@router.get("/")
def get_activities(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    # Usamos .templates porque así lo definiste en el modelo
    return db.query(Activity).options(joinedload(Activity.templates)).filter(Activity.is_active == True).all()

# 2. Crear (Ya lo tenías, pero asegúrate de que use esquemas si prefieres)
@router.post("/")
def create_activity(data: dict, db: Session = Depends(get_db)):
    try:
        new_activity = Activity(name=data['name'], court=data.get('court', ''))
        db.add(new_activity)
        db.flush()
        for s in data['shifts']:
            db.add(ShiftTemplate(activity_id=new_activity.id, day_of_week=s['day_of_week'],
                                 start_time=s['start_time'], capacity=s['capacity']))
        db.commit()
        return {"message": "Creada"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# 3. Editar (UPDATE)
@router.put("/{activity_id}")
def update_activity(activity_id: int, data: dict, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    activity.name = data['name']
    activity.court = data['court']

    # Para los turnos es más fácil borrar los viejos y crear los nuevos (soft reset de templates)
    db.query(ShiftTemplate).filter(ShiftTemplate.activity_id == activity_id).delete()
    for s in data['shifts']:
        db.add(ShiftTemplate(activity_id=activity_id, day_of_week=s['day_of_week'],
                             start_time=s['start_time'], capacity=s['capacity']))

    db.commit()
    return {"message": "Actualizada"}

# 4. Borrar (DELETE - Soft Delete)
@router.delete("/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="No encontrada")

    activity.is_active = False # Usamos borrado lógico
    db.commit()
    return {"message": "Borrada"}