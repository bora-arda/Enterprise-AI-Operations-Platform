"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}
