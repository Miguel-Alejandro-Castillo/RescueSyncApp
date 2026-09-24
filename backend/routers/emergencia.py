from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from models.emergencia import Emergencia

router = APIRouter(
    prefix="/emergencias",
    tags=["emergencias"]
)
@router.get("/")
def read_emergencias():
    return {"message": "List of emergencias"}

@router.post("")
def create_emergencia(
    emergencia: Emergencia,
    session: Session = Depends(get_session)
):
    session.add(emergencia)
    session.commit()
    session.refresh(emergencia)
    return emergencia