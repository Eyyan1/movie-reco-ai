from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, history, preferences, recommendations, watchlist

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    preferences.router, prefix="/preferences", tags=["preferences"]
)
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(
    recommendations.router, prefix="/recommendations", tags=["recommendations"]
)
