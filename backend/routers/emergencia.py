from fastapi import APIRouter

router = APIRouter(
    prefix="/emergencias",
    tags=["emergencias"]
)
@router.get("/")
def read_emergencias():
    return {"message": "List of emergencias"}

@router.post("/")
def create_emergencia():
    return {"message": "Create a new emergencia"}