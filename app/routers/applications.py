from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_applications():
    return {"message": "Not implemented yet"}