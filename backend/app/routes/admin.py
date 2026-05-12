from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserRegister, UserResponse
from ..auth_utils import get_password_hash
# Asumo que tienes una función para obtener el usuario actual desde el token
# from app.routes.auth import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/crear-equipo", response_model=UserResponse)
def crear_miembro_equipo(user_in: UserRegister, db: Session = Depends(get_db)):
    # NOTA: Aquí deberías agregar la lógica de seguridad para que solo un admin logueado pase.
    # Por ahora, hagamos la lógica de creación:

    # 1. Verificar si ya existe
    user_exists = db.query(User).filter(
        (User.email == user_in.email) | (User.dni == user_in.dni)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="El usuario con este Email o DNI ya existe."
        )

    # 2. Crear instancia (Aquí permitimos definir el ROL que venga del front)
    # Importante: En el frontend enviaremos 'admin' o 'employee'
    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role # Aquí usamos el rol que mandes desde el formulario
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")