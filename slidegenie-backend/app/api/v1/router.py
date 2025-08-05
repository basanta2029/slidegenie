"""
API v1 router configuration.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    academic,
    # admin,  # TODO: Fix decorator issues
    # analytics,  # TODO: Fix decorator issues
    auth,
    document_upload,
    export,
    generation,
    health,
    oauth,
    presentations,
    realtime,
    # slides,  # TODO: Fix layout engine initialization
    templates,
    users,
    websocket,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(academic.router, prefix="/academic", tags=["academic"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(presentations.router, prefix="/presentations", tags=["presentations"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
# api_router.include_router(slides.router, prefix="/slides", tags=["slides"])  # TODO: Fix layout engine initialization
api_router.include_router(document_upload.router, prefix="/documents/upload", tags=["document-upload"])
api_router.include_router(export.router, tags=["export"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
# api_router.include_router(analytics.router, tags=["analytics"])  # TODO: Fix decorator issues
# api_router.include_router(admin.router, tags=["admin"])  # TODO: Fix decorator issues