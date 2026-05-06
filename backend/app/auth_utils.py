import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional
import os
from dotenv import load_dotenv

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
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt