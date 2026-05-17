from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User,UserRole
from ..schemas.user import UserRegister, UserResponse, UserLogin, Token
from ..auth_utils import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import random
from ..mail import send_reset_code
from ..models.password_reset import PasswordResetCode


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # 1. Verificar si ya existe el usuario
    user_exists = db.query(User).filter(
        (User.email == user_in.email) | (User.dni == user_in.dni)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or DNI already exists."
        )

    # 2. Crear instancia del nuevo usuario
    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CLIENT # Por defecto es cliente
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    # 1. Buscar usuario
    user = db.query(User).filter(User.email == user_in.email).first()

    # 2. Validar existencia y contraseña
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # 3. Generar Token incluyendo el ROL
    access_token = create_access_token(
        data={"sub": user.email, "id": user.id_user, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value
    }

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(data: EmailRequest, db: Session = Depends(get_db)):
    # No revelar si el email existe o no (seguridad)
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "Si el email existe, recibirás un código."}

    # Invalidar códigos anteriores del mismo email
    db.query(PasswordResetCode).filter(
        PasswordResetCode.email == data.email,
        PasswordResetCode.used == False
    ).update({"used": True})

    # Generar código
    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    reset = PasswordResetCode(email=data.email, code=code, expires_at=expires)
    db.add(reset)
    db.commit()

    await send_reset_code(data.email, code)
    return {"message": "Si el email existe, recibirás un código."}


@router.post("/verify-reset-code")
def verify_code(data: VerifyCodeRequest, db: Session = Depends(get_db)):
    record = db.query(PasswordResetCode).filter(
        PasswordResetCode.email == data.email,
        PasswordResetCode.code == data.code,
        PasswordResetCode.used == False,
        PasswordResetCode.expires_at > datetime.utcnow()
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Código inválido o expirado.")

    return {"valid": True}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    record = db.query(PasswordResetCode).filter(
        PasswordResetCode.email == data.email,
        PasswordResetCode.code == data.code,
        PasswordResetCode.used == False,
        PasswordResetCode.expires_at > datetime.utcnow()
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Código inválido o expirado.")

    user = db.query(User).filter(User.email == data.email).first()
    user.hashed_password = get_password_hash(data.new_password)

    record.used = True
    db.commit()

    return {"message": "Contraseña actualizada correctamente."}