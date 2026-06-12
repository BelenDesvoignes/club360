from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserRegister, UserResponse, UserLogin, Token, UserProfileResponse, UserProfileUpdate
from ..auth_utils import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import random
from ..mail import send_reset_code
from ..models.password_reset import PasswordResetCode

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.dni == user_in.dni).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese DNI."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese correo electrónico."
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CLIENT
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
            detail=f"Error al crear el usuario: {str(e)}"
        )

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo electrónico no está registrado."
        )

    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta."
        )

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
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="El correo ingresado no se encuentra registrado.")

    db.query(PasswordResetCode).filter(
        PasswordResetCode.email == data.email,
        PasswordResetCode.used == False
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


# COMPATIBILIDAD TOTAL: Eliminamos librerías externas que rompen producción.
# Si tu frontend envía el Header con el correo o token, lo procesamos directamente con FastAPI.
@router.get("/me", response_model=UserProfileResponse)
def get_me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado. Inicie sesión nuevamente.")
    
    token = authorization.split(" ")[1]
    
    try:
        import jwt
        SECRET_KEY = "key"
        ALGORITHM = "HS256"
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="El token no contiene un usuario válido.")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada. Vuelva a ingresar.")

    # BUSCADOR EXACTO: Filtra por el email real del token (ej: admin@gmail.com)
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
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = db.query(User).filter(User.id_user == User.id_user).first()

    if payload.email != user.email:
        existing_user = db.query(User).filter(User.email == payload.email, User.id_user != user.id_user).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo electrónico.")

    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.email = payload.email

    db.commit()
    db.refresh(user)

    return user