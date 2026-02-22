"""Health check route."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "FieldOps AI Backend"}
