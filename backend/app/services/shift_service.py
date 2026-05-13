from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models.shift_instance import ShiftInstance
from app.models.shift_template import ShiftTemplate
from app.models.activity import Activity

def create_instances_for_month(db: Session, template: ShiftTemplate):
    days_map = {
        "Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, 
        "Viernes": 4, "Sábado": 5, "Domingo": 6
    }
    target_day = days_map.get(template.day_of_week)
    if target_day is None: 
        return []

    today = date.today()
    new_instances = []
    
    for i in range(35):
        check_date = today + timedelta(days=i)
        
        if check_date.weekday() == target_day:
            
            existing = db.query(ShiftInstance).filter(
                ShiftInstance.template_id == template.id,
                ShiftInstance.date == check_date
            ).first()
            
            if not existing:
                db_instance = ShiftInstance(
                    template_id=template.id,
                    date=check_date,
                    is_cancelled=False,
                    capacity=template.capacity 
                )
                db.add(db_instance)
                new_instances.append(db_instance)
            
            # Limitar a 4 o 5 clases (un mes aproximado)
            if len(new_instances) >= 5: 
                break
                
    db.commit()
    return new_instances

def delete_template_and_instances(db: Session, template_id: int):
    db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).delete()
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if template:
        db.delete(template)
    db.commit()

def update_template_and_recreate_instances(db: Session, template_id: int, new_data):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template: return None

    template.day_of_week = new_data.day_of_week
    template.start_time = new_data.start_time
    template.capacity = new_data.capacity
    db.commit()

    db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id, ShiftInstance.date >= date.today()).delete()
    create_instances_for_month(db, template)
    
    return template

def get_shift_instance_detail(db: Session, instance_id: int):
    return db.query(
        ShiftInstance.id,
        Activity.name.label("activity_name"),
        Activity.court,  # <--- Ahora lo pedimos desde Activity
        ShiftInstance.date,
        ShiftTemplate.start_time,
        ShiftTemplate.capacity,
        ShiftInstance.is_cancelled
    ).join(
        ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id
    ).join(
        Activity, ShiftTemplate.activity_id == Activity.id
    ).filter(
        ShiftInstance.id == instance_id
    ).first()


def validate_unique_shift(db, activity_id, day_of_week, start_time, exclude_id=None):
    duplicate = db.query(ShiftTemplate).filter(
        ShiftTemplate.activity_id == activity_id,
        ShiftTemplate.day_of_week == day_of_week,
        ShiftTemplate.start_time == start_time,
        ShiftTemplate.id != exclude_id
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un turno el {day_of_week} a las {start_time}."
        )
