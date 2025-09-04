import logging

from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter()
logger = logging.getLogger("app.router.health")


@router.get("/health", response_model=HealthResponse)
def health_check():
    logger.info("Health check endpoint was called.")
    return HealthResponse(status="healthy", message="API is running")
