"""Analytics Router"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta
import logging
from services.db import get_db
from services.auth_deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/location-stats/district")
async def get_district_stats(
    start_date: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        query = db.table("anonymous_location_logs").select("*")
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt("created_at", end_datetime.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "success": True,
                "stats": [],
                "total_districts": 0
            }
        
        district_stats = {}
        
        for log in result.data:
            district = log.get("district")
            if not district:
                continue
            
            if district not in district_stats:
                district_stats[district] = {
                    "district": district,
                    "visitor_count": set(),
                    "quest_count": 0,
                    "interest_count": 0,
                    "total_distance_km": 0.0,
                    "distance_count": 0
                }
            
            anonymous_user_id = log.get("anonymous_user_id")
            if anonymous_user_id:
                district_stats[district]["visitor_count"].add(anonymous_user_id)
            
            if log.get("quest_id"):
                district_stats[district]["quest_count"] += 1
            
            district_stats[district]["interest_count"] += 1
            
            distance = log.get("distance_from_quest_km")
            if distance is not None:
                district_stats[district]["total_distance_km"] += float(distance)
                district_stats[district]["distance_count"] += 1
        
        stats_list = []
        for district, stats in district_stats.items():
            avg_distance = (
                stats["total_distance_km"] / stats["distance_count"]
                if stats["distance_count"] > 0
                else 0.0
            )
            
            stats_list.append({
                "district": district,
                "visitor_count": len(stats["visitor_count"]),
                "quest_count": stats["quest_count"],
                "interest_count": stats["interest_count"],
                "avg_distance_km": round(avg_distance, 2)
            })
        
        stats_list.sort(key=lambda x: x["visitor_count"], reverse=True)
        
        logger.info(f"District stats: {len(stats_list)} districts")
        
        return {
            "success": True,
            "stats": stats_list,
            "total_districts": len(stats_list),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    except Exception as e:
        logger.error(f"District stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/location-stats/quest")
async def get_quest_stats(
    quest_id: Optional[int] = Query(None, description="Quest ID (Optional)"),
    start_date: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        query = db.table("anonymous_location_logs").select("*, quests(name, title)")
        
        if quest_id:
            query = query.eq("quest_id", quest_id)
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt("created_at", end_datetime.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "success": True,
                "stats": [],
                "total_quests": 0
            }
        
        quest_stats = {}
        
        for log in result.data:
            q_id = log.get("quest_id")
            if not q_id:
                continue
            
            if q_id not in quest_stats:
                quest_info = log.get("quests")
                quest_name = None
                if quest_info:
                    if isinstance(quest_info, list) and len(quest_info) > 0:
                        quest_info = quest_info[0]
                    if isinstance(quest_info, dict):
                        quest_name = quest_info.get("name") or quest_info.get("title")
                
                quest_stats[q_id] = {
                    "quest_id": q_id,
                    "quest_name": quest_name,
                    "visitor_count": set(),
                    "visit_count": 0,
                    "district": log.get("district"),
                    "total_distance_km": 0.0,
                    "distance_count": 0
                }
            
            anonymous_user_id = log.get("anonymous_user_id")
            if anonymous_user_id:
                quest_stats[q_id]["visitor_count"].add(anonymous_user_id)
            
            quest_stats[q_id]["visit_count"] += 1
            
            distance = log.get("distance_from_quest_km")
            if distance is not None:
                quest_stats[q_id]["total_distance_km"] += float(distance)
                quest_stats[q_id]["distance_count"] += 1
        
        stats_list = []
        for q_id, stats in quest_stats.items():
            avg_distance = (
                stats["total_distance_km"] / stats["distance_count"]
                if stats["distance_count"] > 0
                else 0.0
            )
            
            stats_list.append({
                "quest_id": q_id,
                "quest_name": stats["quest_name"],
                "visitor_count": len(stats["visitor_count"]),
                "visit_count": stats["visit_count"],
                "district": stats["district"],
                "avg_distance_km": round(avg_distance, 2)
            })
        
        stats_list.sort(key=lambda x: x["visit_count"], reverse=True)
        
        logger.info(f"Quest stats: {len(stats_list)} quests")
        
        return {
            "success": True,
            "stats": stats_list,
            "total_quests": len(stats_list),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    except Exception as e:
        logger.error(f"Quest stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/location-stats/time")
async def get_time_stats(
    start_date: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    group_by: str = Query("hour", description="Group by: hour, day, week"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        query = db.table("anonymous_location_logs").select("*")
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt("created_at", end_datetime.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "success": True,
                "stats": [],
                "total_periods": 0
            }
        
        time_stats = {}
        
        for log in result.data:
            created_at = log.get("created_at")
            if not created_at:
                continue
            
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            if group_by == "hour":
                time_key = dt.strftime("%Y-%m-%d %H:00")
            elif group_by == "day":
                time_key = dt.strftime("%Y-%m-%d")
            elif group_by == "week":
                year, week, _ = dt.isocalendar()
                time_key = f"{year}-W{week:02d}"
            else:
                time_key = dt.strftime("%Y-%m-%d %H:00")
            
            if time_key not in time_stats:
                time_stats[time_key] = {
                    "time_period": time_key,
                    "visitor_count": set(),
                    "visit_count": 0
                }
            
            anonymous_user_id = log.get("anonymous_user_id")
            if anonymous_user_id:
                time_stats[time_key]["visitor_count"].add(anonymous_user_id)
            
            time_stats[time_key]["visit_count"] += 1
        
        stats_list = []
        for time_key, stats in time_stats.items():
            stats_list.append({
                "time_period": time_key,
                "visitor_count": len(stats["visitor_count"]),
                "visit_count": stats["visit_count"]
            })
        
        stats_list.sort(key=lambda x: x["time_period"])
        
        logger.info(f"Time stats: {len(stats_list)} periods (group_by={group_by})")
        
        return {
            "success": True,
            "stats": stats_list,
            "total_periods": len(stats_list),
            "group_by": group_by,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    except Exception as e:
        logger.error(f"Time stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/location-stats/summary")
async def get_summary_stats(
    start_date: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        query = db.table("anonymous_location_logs").select("*")
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt("created_at", end_datetime.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "success": True,
                "summary": {
                    "total_visitors": 0,
                    "total_visits": 0,
                    "total_quests": 0,
                    "total_districts": 0,
                    "avg_distance_km": 0.0
                }
            }
        
        visitors = set()
        quests = set()
        districts = set()
        total_distance = 0.0
        distance_count = 0
        
        for log in result.data:
            anonymous_user_id = log.get("anonymous_user_id")
            if anonymous_user_id:
                visitors.add(anonymous_user_id)
            
            quest_id = log.get("quest_id")
            if quest_id:
                quests.add(quest_id)
            
            district = log.get("district")
            if district:
                districts.add(district)
            
            distance = log.get("distance_from_quest_km")
            if distance is not None:
                total_distance += float(distance)
                distance_count += 1
        
        avg_distance = (
            total_distance / distance_count
            if distance_count > 0
            else 0.0
        )
        
        logger.info(f"Summary stats: {len(visitors)} visitors, {len(quests)} quests")
        
        return {
            "success": True,
            "summary": {
                "total_visitors": len(visitors),
                "total_visits": len(result.data),
                "total_quests": len(quests),
                "total_districts": len(districts),
                "avg_distance_km": round(avg_distance, 2)
            },
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    except Exception as e:
        logger.error(f"Summary stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
