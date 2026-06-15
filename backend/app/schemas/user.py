from pydantic import BaseModel, EmailStr
from ..models.user import UserRole
from typing import Optional

class UserRegister(BaseModel):
    first_name: str
    last_name: str
    dni: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.CLIENT

class UserResponse(BaseModel):
    id_user: int
    first_name: str
    last_name: str
    dni: str
    email: str
    role: UserRole

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr

class UserProfileResponse(BaseModel):
    id_user: int
    first_name: str
    last_name: str
    dni: str
    email: str
    role: UserRole

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

    class Config:
        from_attributes = True