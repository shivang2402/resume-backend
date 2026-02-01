from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_sections():
    return {"message": "Not implemented yet"}