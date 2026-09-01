"""Health-check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
