from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class ShiftTemplateBase(BaseModel):
    day_of_week: str  # Ejemplo: "Martes"
    start_time: str   # Ejemplo: "17:00"
    capacity: int

class ShiftTemplateCreate(ShiftTemplateBase):
    activity_id: int

class ShiftTemplateOut(ShiftTemplateBase):
    id: int
    activity_id: int

    class Config:
        from_attributes = True  

class ShiftInstanceBase(BaseModel):
    date: date        # Usamos el tipo 'date' de Python para validación real
    is_cancelled: bool = False

class ShiftInstanceOut(ShiftInstanceBase):
    id: int
    template_id: int

    class Config:
        from_attributes = True