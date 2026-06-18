from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class WaitingListCreate(BaseModel):
    instance_id: int = Field(..., description="ID de la clase/instancia de turno")

class WaitingListResponse(BaseModel):
    id: int
    user_id: int
    instance_id: int
    position: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  