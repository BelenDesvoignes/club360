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
    """Get all upcoming shift instances with booking counts and activity names."""
    from sqlalchemy import func
    
    # Single query with LEFT JOIN and GROUP BY for efficiency
    result = (
        db.query(
            ShiftInstance.id,
            ShiftInstance.date,
            ShiftInstance.is_cancelled,
            ShiftTemplate.id.label('template_id'),
            ShiftTemplate.activity_id,
            ShiftTemplate.day_of_week,
            ShiftTemplate.start_time,
            ShiftTemplate.capacity,
            ShiftTemplate.price,
            Activity.name.label('activity_name'),
            func.count(Booking.id).label('booked_count')
        )
        .outerjoin(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .outerjoin(Activity, ShiftTemplate.activity_id == Activity.id)
        .outerjoin(
            Booking,
            and_(
                Booking.instance_id == ShiftInstance.id,
                Booking.status != "Cancelled"
            )
        )
        .filter(ShiftInstance.is_cancelled == False)
        .group_by(ShiftInstance.id, ShiftTemplate.id, Activity.id)
        .all()
    )
    
    # Format response
    instances_dict = {}
    for row in result:
        instance_id = row.id
        if instance_id not in instances_dict:
            instances_dict[instance_id] = {
                "id": row.id,
                "date": str(row.date),
                "is_cancelled": row.is_cancelled,
                "booked_count": row.booked_count if row.booked_count else 0,
                "activity_name": row.activity_name or f"Actividad {row.activity_id}",
                "template": {
                    "id": row.template_id,
                    "activity_id": row.activity_id,
                    "day_of_week": row.day_of_week,
                    "start_time": row.start_time,
                    "capacity": row.capacity,
                    "price": float(row.price) if row.price else 100.0
                }
            }
    
    return list(instances_dict.values())
@router.get("/instances/{instance_id}", response_model=ShiftDetailResponse)
def get_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    detail = shift_service.get_shift_instance_detail(db, instance_id)
    if not detail:
        raise HTTPException(status_code=404, detail="El detalle del turno no existe")
    return detail
