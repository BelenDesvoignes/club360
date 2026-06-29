from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import (
    UserRegister,
    UserResponse,
    UserLogin,
    Token,
    UserProfileResponse,
    UserProfileUpdate,
)
from ..auth_utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Any, cast
import random
from ..mail import send_reset_code
from ..models.password_reset import PasswordResetCode

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.dni == user_in.dni).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese DNI.",
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese correo electrónico.",
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CLIENT,
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
            detail=f"Error al crear el usuario: {str(e)}",
        ) from e


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo electrónico no está registrado.",
        )

    user_record = cast(Any, user)

    if not verify_password(user_in.password, user_record.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta."
        )

    role_value = user_record.role.value
    access_token = create_access_token(
        data={"sub": user_record.email, "id": user_record.id_user, "role": role_value}
    )

    return {"access_token": access_token, "token_type": "bearer", "role": role_value}


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
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="El correo ingresado no se encuentra registrado."
        )

    db.query(PasswordResetCode).filter(
        PasswordResetCode.email == data.email, PasswordResetCode.used.is_(False)
    ).update({"used": True})

    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    reset = PasswordResetCode(email=data.email, code=code, expires_at=expires)
    db.add(reset)
    db.commit()

    await send_reset_code(data.email, code)
    return {"message": "Si el email existe, recibirás un código."}


@router.post("/verify-reset-code")
def verify_code(data: VerifyCodeRequest, db: Session = Depends(get_db)):
    record = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.email == data.email,
            PasswordResetCode.code == data.code,
            PasswordResetCode.used.is_(False),
            PasswordResetCode.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=400, detail="Código inválido o expirado.")

    return {"valid": True}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    record = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.email == data.email,
            PasswordResetCode.code == data.code,
            PasswordResetCode.used.is_(False),
            PasswordResetCode.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=400, detail="Código inválido o expirado.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user_record = cast(Any, user)
    reset_record = cast(Any, record)
    user_record.hashed_password = get_password_hash(data.new_password)
    reset_record.used = True
    db.commit()

    return {"message": "Contraseña actualizada correctamente."}


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="No autorizado. Inicie sesión nuevamente."
        )

    token = authorization.split(" ")[1]
    user_email = None

    try:
        from jose import jwt

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        user_email = payload.get("sub")
    except Exception:
        user_id = None
        user_email = None

    if not user_id and not user_email:
        raise HTTPException(
            status_code=401, detail="Sesión inválida. Inicie sesión nuevamente."
        )

    if user_id:
        user = db.query(User).filter(User.id_user == user_id).first()
    else:
        user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/me", response_model=UserProfileResponse)
def update_me(
    payload: UserProfileUpdate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sesión expirada.")

    token = authorization.split(" ")[1]
    try:
        from jose import jwt

        payload_data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload_data.get("id")
        user_email = payload_data.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Sesión inválida.") from None

    # Buscamos al usuario autenticado
    if user_id:
        user = db.query(User).filter(User.id_user == user_id).first()
    else:
        user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # --- AQUÍ ESTÁ LA MAGIA ---
    # Solo validamos duplicados si el correo del formulario es DISTINTO al que el usuario tiene ahora
    user_record = cast(Any, user)

    if payload.email != user_record.email:
        existing_user = db.query(User).filter(User.email == payload.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Ese correo electrónico ya está registrado por otro usuario.",
            )

    # Actualizamos los datos
    user_record.first_name = payload.first_name
    user_record.last_name = payload.last_name
    user_record.email = payload.email

    db.commit()
    db.refresh(user)
    return user
