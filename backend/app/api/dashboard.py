import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.dashboard import DashboardDataResponse
from app.services.dashboard_service import get_dashboard_data

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/analysis/{analysis_id}/dashboard",
    response_model=DashboardDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve unified multi-track speech analytics data for interactive dashboards",
)
async def get_dashboard_endpoint(
    analysis_id: str,
    auto_complete: bool = Query(default=True, description="Automatically chain and compute missing pipeline stages if audio exists"),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    try:
        data = get_dashboard_data(db=db, analysis_id=analysis_id, auto_complete=auto_complete)
        return data
    except Exception as exc:
        logger.error(f"Failed to retrieve dashboard data for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(exc)}",
        )
