from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut
from app.models.shift_template import ShiftTemplate
from app.models.shift_instance import ShiftInstance
from app.models.booking import Booking
from app.models.activity import Activity
from app.services import shift_service
from sqlalchemy import and_

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
    instances = db.query(ShiftInstance).filter(ShiftInstance.is_cancelled == False).all()
    
    result = []
    for instance in instances:
        template = instance.template
        if not template:
            continue
        
        activity = template.activity
        activity_name = activity.name if activity else f"Actividad {template.activity_id}"
        
        # Count non-cancelled bookings
        booked_count = (
            db.query(Booking)
            .filter(
                and_(
                    Booking.instance_id == instance.id,
                    Booking.status != "Cancelled"
                )
            )
            .count()
        )
        
        result.append({
            "id": instance.id,
            "date": instance.date,
            "is_cancelled": instance.is_cancelled,
            "booked_count": booked_count,
            "activity_name": activity_name,
            "template": {
                "id": template.id,
                "activity_id": template.activity_id,
                "day_of_week": template.day_of_week,
                "start_time": template.start_time,
                "capacity": template.capacity,
                "price": template.price
            }
        })
    
    return result