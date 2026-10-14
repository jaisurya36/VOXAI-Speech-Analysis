import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.demo import DemoListResponse, DemoLoadResponse
from app.services.demo_service import get_demo_samples_list, load_demo_sample

router = APIRouter(prefix="/demo", tags=["demo"])
logger = logging.getLogger(__name__)


@router.get(
    "/samples",
    response_model=DemoListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available contrastive demo speeches with archetypes and benchmark scores",
)
async def list_demo_samples():
    """Retrieve catalog of pre-computed contrastive showcase speeches."""
    try:
        return get_demo_samples_list()
    except Exception as exc:
        logger.error(f"Failed to retrieve demo samples: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve demo samples: {str(exc)}",
        )


@router.post(
    "/load/{sample_id}",
    response_model=DemoLoadResponse,
    status_code=status.HTTP_200_OK,
    summary="Instantly load or seed a showcase demo speech for immediate dashboard viewing",
)
async def load_demo_sample_endpoint(
    sample_id: str,
    db: Session = Depends(get_db),
):
    """Seed or retrieve a precomputed demo speech and return its analysis_id."""
    try:
        result = load_demo_sample(db=db, sample_id=sample_id)
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Failed to load demo sample {sample_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load demo sample: {str(exc)}",
        )
