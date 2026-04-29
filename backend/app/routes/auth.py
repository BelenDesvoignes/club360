from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.member import Member  # Ajustá la ruta según tu init
from app.schemas.member import MemberCreate, MemberResponse
from app.auth_utils import get_password_hash

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/register", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def register_member(member_data: MemberCreate, db: Session = Depends(get_db)):
    try:
        # 1. Verificar si el socio ya existe (por Email o DNI)
        existing_member = db.query(Member).filter(
            (Member.email == member_data.email) | (Member.dni == member_data.dni)
        ).first()

        if existing_member:
            raise HTTPException(
                status_code=400,
                detail="El DNI o Email ya se encuentran registrados en CLUB360."
            )

        # 2. Encriptar la contraseña usando la utilidad que creaste
        hashed_pass = get_password_hash(member_data.password)

        # 3. Crear la instancia del modelo Member
        new_member = Member(
            first_name=member_data.first_name,
            last_name=member_data.last_name,
            dni=member_data.dni,
            email=member_data.email,
            hashed_password=hashed_pass,
            is_suspended=False,
        )

        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        return new_member
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database operation failed: {exc.__class__.__name__}: {str(exc)[:700]}",
        )