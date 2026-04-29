from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserRegister(BaseModel):
    first_name: str
    last_name: str
    dni: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id_user: int
    email: str
    role: UserRole

    class Config:
        from_attributes = True