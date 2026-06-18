from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.waiting_list_service import WaitingListService
from ..schemas.waiting_list_schema import WaitingListResponse
from ..auth_utils import get_user_id_from_token  

router = APIRouter(
    prefix="/waiting-lists",
    tags=["Waiting Lists"]
)

@router.post("/join", response_model=WaitingListResponse, status_code=status.HTTP_201_CREATED)
def join_class_waiting_list(
    instance_id: int, 
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token)  
):
    """
    Permite a un cliente autenticado anotarse en la lista de espera 
    de una clase cuyo cupo esté totalmente completo.
    """
    new_entry = WaitingListService.join_waiting_list(
        db=db, 
        user_id=user_id, 
        instance_id=instance_id
    )
    return new_entry