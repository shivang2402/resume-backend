from fastapi import APIRouter

router = APIRouter()


@router.post("")
def generate_resume():
    return {"message": "Not implemented yet"}