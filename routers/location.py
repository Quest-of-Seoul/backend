"""Location Tracking Router"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
from services.db import get_db
from services.auth_deps import get_current_user_id
from services.location_tracking import log_periodic_location, get_user_location_history

logger = logging.getLogger(__name__)
router = APIRouter()


class LocationTrackRequest(BaseModel):
    """주기적 위치 추적 요청"""
    latitude: float
    longitude: float
    quest_id: Optional[int] = None
    place_id: Optional[str] = None


@router.post("/track")
async def track_location(
    request: LocationTrackRequest,
    user_id: str = Depends(get_current_user_id)
):
    try:
        if request.latitude is None or request.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude are required")
        
        if not (-90 <= request.latitude <= 90):
            raise HTTPException(status_code=400, detail="latitude must be between -90 and 90")
        if not (-180 <= request.longitude <= 180):
            raise HTTPException(status_code=400, detail="longitude must be between -180 and 180")
        
        success = log_periodic_location(
            user_id=user_id,
            user_latitude=request.latitude,
            user_longitude=request.longitude,
            quest_id=request.quest_id,
            place_id=request.place_id
        )
        
        if success:
            logger.info(f"Location tracked for user {user_id[:8]}... at ({request.latitude}, {request.longitude})")
            return {
                "success": True,
                "message": "Location tracked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track location")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking location: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error tracking location: {str(e)}")


@router.get("/track/history")
async def get_location_history(
    start_date: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    limit: int = Query(1000, description="Maximum number of locations to retrieve (default: 1000)"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        if start_date:
            try:
                datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_date must be in YYYY-MM-DD format")
        
        if end_date:
            try:
                datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="end_date must be in YYYY-MM-DD format")
        
        locations = get_user_location_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        formatted_locations = []
        for loc in locations:
            formatted_locations.append({
                "id": loc.get("id"),
                "latitude": float(loc.get("user_latitude")) if loc.get("user_latitude") else None,
                "longitude": float(loc.get("user_longitude")) if loc.get("user_longitude") else None,
                "quest_id": loc.get("quest_id"),
                "place_id": loc.get("place_id"),
                "district": loc.get("district"),
                "distance_from_quest_km": float(loc.get("distance_from_quest_km")) if loc.get("distance_from_quest_km") else None,
                "created_at": loc.get("created_at")
            })
        
        logger.info(f"Location history retrieved for user {user_id[:8]}...: {len(formatted_locations)} locations")
        
        return {
            "success": True,
            "count": len(formatted_locations),
            "locations": formatted_locations
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting location history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting location history: {str(e)}")
