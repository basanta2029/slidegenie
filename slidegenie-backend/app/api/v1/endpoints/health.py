"""
Health check endpoints.
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.core.health import check_health, check_liveness, check_readiness, get_metrics

router = APIRouter()


@router.get("/health")
async def health_check(
    force_refresh: bool = Query(False, description="Force refresh of all health checks")
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Args:
        force_refresh: Force refresh of all health checks, ignoring cache
    
    Returns:
        Comprehensive health status with component details
    """
    try:
        health_data = await check_health(force_refresh=force_refresh)
        return health_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes-style readiness check.
    
    Returns:
        Readiness status indicating if the service can handle requests
    """
    try:
        is_ready, health_data = await check_readiness()
        
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
        
        return {
            "status": "ready",
            "timestamp": health_data.get("timestamp"),
            "components": health_data.get("components", {}),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {str(e)}"
        )


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes-style liveness check.
    
    Returns:
        Basic liveness status indicating if the service is alive
    """
    try:
        is_alive, basic_info = await check_liveness()
        
        if not is_alive:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not alive"
            )
        
        return basic_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Liveness check failed: {str(e)}"
        )


@router.get("/metrics")
async def health_metrics() -> Dict[str, Any]:
    """
    Get detailed health and performance metrics.
    
    Returns:
        Detailed system metrics and performance data
    """
    try:
        metrics = await get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )