from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.activity import Activity
from sqlalchemy import and_
from app.database import get_db
from app.schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut, ShiftDetailResponse
from app.models.shift_template import ShiftTemplate
from app.services import shift_service

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
    
    result = (
        db.query(
            ShiftInstance.id,
            ShiftInstance.date,
            ShiftInstance.is_cancelled,
            ShiftInstance.capacity.label('instance_capacity'), # <--- Capacidad real de la clase
            ShiftTemplate.id.label('template_id'),
            ShiftTemplate.activity_id,
            ShiftTemplate.start_time,
            ShiftTemplate.capacity.label('template_capacity'), # <--- Capacidad del molde (opcional)
            Activity.name.label('activity_name'),
            func.count(Booking.id).label('booked_count')
        )
        .outerjoin(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .outerjoin(Activity, ShiftTemplate.activity_id == Activity.id)
        .outerjoin(Booking, and_(Booking.instance_id == ShiftInstance.id, Booking.status != "Cancelled"))
        .filter(ShiftInstance.is_cancelled == False)
        .group_by(ShiftInstance.id, ShiftTemplate.id, Activity.id)
        .all()
    )
    
    instances_list = []
    for row in result:
        instances_list.append({
            "id": row.id,
            "date": str(row.date),
            "is_cancelled": row.is_cancelled,
            "booked_count": row.booked_count or 0,
            "activity_name": row.activity_name,
            "capacity": row.instance_capacity,  
            "template": {
                "id": row.template_id,
                "start_time": row.start_time,
                "base_capacity": row.template_capacity 
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
    # Buscamos la instancia
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="La clase no existe")
    
    # Cambiamos el estado a cancelado
    instance.is_cancelled = True
    db.commit()
    
    return {"message": "Clase cancelada exitosamente", "id": instance_id}