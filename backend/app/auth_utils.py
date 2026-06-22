import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status, Header

load_dotenv() # Esto lee un archivo .env en tu carpeta local

# Busca la variable, si no la encuentra usa un valor por defecto (solo para desarrollo)
SECRET_KEY = os.getenv("SECRET_KEY", "una_clave_temporal_muy_debil")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  * 365 # 1ano

def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera el token JWT con los datos del usuario (id, email, rol)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_id_from_token(authorization: str | None = Header(default=None)) -> Optional[int]:
    """Decodifica el JWT del header Authorization y devuelve el campo 'id' si existe.

    Diseñada para usarse como dependencia: Depends(get_user_id_from_token)
    """
    if not authorization:
        return None

    # Si la string viene como 'Bearer <token>' extraer token
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    else:
        # Si se llamó pasando el token crudo (caso habitual en rutas que llaman la función directamente)
        token = authorization.strip()

    # Protección básica: el token JWT suele tener 2 puntos '.'
    if token.count('.') < 2:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get('id')
        return int(user_id) if user_id is not None else None
    except Exception:
        return None


def get_current_user_role(authorization: str | None = Header(default=None)) -> str:
    """
    Extrae el rol del usuario desde el header Authorization Bearer <token>.
    Diseñada para usarse como dependencia en FastAPI: Depends(get_current_user_role)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        return role if role is not None else "client"
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")