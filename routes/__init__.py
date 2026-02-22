from routes.voice import router as voice_router
from routes.dashboard import router as dashboard_router
from routes.health import router as health_router

__all__ = ["voice_router", "dashboard_router", "health_router"]
