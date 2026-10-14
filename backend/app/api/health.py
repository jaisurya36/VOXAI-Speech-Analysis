from fastapi import APIRouter
from app.schemas.analysis import HealthResponse

router = APIRouter()


@router.get('/health', response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status='ok',
        application='Counterpointing Speech Analytics',
        version='1.0.0'
    )
