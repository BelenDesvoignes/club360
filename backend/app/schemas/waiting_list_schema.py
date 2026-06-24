from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class UserSimple(BaseModel):
    id_user: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True

class WaitingListCreate(BaseModel):
    instance_id: int = Field(..., description="ID de la clase/instancia de turno")

class WaitingListResponse(BaseModel):
    id: int
    user_id: int
    instance_id: int
    position: int
    status: str
    entry_type: str
    subscription_id: Optional[int] = None
    created_at: datetime
    promoted_at: Optional[datetime] = None
    promotion_expires_at: Optional[datetime] = None
    user: Optional[UserSimple] = None

    class Config:
        from_attributes = True  