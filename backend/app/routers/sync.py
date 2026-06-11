from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.api_football_service import sync_match_results

router = APIRouter()


@router.get("/results", status_code=status.HTTP_200_OK)
def sync_results_endpoint(
    secret: str,
    db: Session = Depends(get_db),
) -> dict:
    """Secure endpoint for automated cron jobs to sync match results."""
    if secret != settings.SYNC_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return sync_match_results(db)
