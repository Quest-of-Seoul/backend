"""Reward Router"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.db import get_db
from services.auth_deps import get_current_user_id
from datetime import datetime
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ClaimRewardRequest(BaseModel):
    reward_id: int


class AddPointsRequest(BaseModel):
    points: int
    reason: str = "Quest completion"


@router.get("/points")
async def get_user_points(user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"Getting points for user: {user_id}")

        db = get_db()

        result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        total_points = result.data if result.data else 0

        transactions = db.table("points") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()

        logger.info(f"Total points: {total_points}, transactions: {len(transactions.data)}")

        return {
            "total_points": total_points,
            "transactions": transactions.data
        }

    except Exception as e:
        logger.error(f"Error getting points: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching points: {str(e)}")


@router.post("/points/add")
async def add_points(request: AddPointsRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"Adding {request.points} points to user: {user_id}")

        if request.points <= 0:
            raise HTTPException(status_code=400, detail="Points must be greater than 0")

        db = get_db()

        current_points_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        current_points = current_points_result.data if current_points_result.data else 0

        db.table("points").insert({
            "user_id": user_id,
            "value": request.points,
            "reason": request.reason
        }).execute()

        new_balance = current_points + request.points
        logger.info(f"Points added successfully. New balance: {new_balance}")

        return {
            "status": "success",
            "message": f"Successfully added {request.points} points",
            "points_added": request.points,
            "previous_balance": current_points,
            "new_balance": new_balance,
            "reason": request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding points: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error adding points: {str(e)}")


@router.get("/list")
async def get_available_rewards(
    type: str | None = None,
    search: str | None = None
):
    try:
        db = get_db()
        query = db.table("rewards").select("*").eq("is_active", True)
        
        if type:
            query = query.eq("type", type)
        
        if search:
            query = query.ilike("name", f"%{search}%")
        
        result = query.order("point_cost").execute()

        logger.info(f"Fetched {len(result.data)} rewards (type={type}, search={search})")

        return {
            "rewards": result.data
        }

    except Exception as e:
        logger.error(f"Error fetching rewards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching rewards: {str(e)}")


@router.post("/claim")
async def claim_reward(request: ClaimRewardRequest, user_id: str = Depends(get_current_user_id)):
    try:
        db = get_db()

        reward = db.table("rewards") \
            .select("*") \
            .eq("id", request.reward_id) \
            .eq("is_active", True) \
            .execute()

        if not reward.data:
            raise HTTPException(status_code=404, detail="Reward not found or inactive")

        reward_data = reward.data[0]

        user_points_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        user_points = user_points_result.data if user_points_result.data else 0

        if user_points < reward_data['point_cost']:
            return {
                "status": "fail",
                "message": "Not enough points",
                "required": reward_data['point_cost'],
                "current": user_points,
                "shortage": reward_data['point_cost'] - user_points
            }

        db.table("points").insert({
            "user_id": user_id,
            "value": -reward_data['point_cost'],
            "reason": f"Redeemed: {reward_data['name']}"
        }).execute()

        qr_token = secrets.token_urlsafe(16)

        db.table("user_rewards").insert({
            "user_id": user_id,
            "reward_id": request.reward_id,
            "qr_code": qr_token
        }).execute()

        return {
            "status": "success",
            "message": "Reward claimed successfully!",
            "reward": {
                "id": reward_data['id'],
                "name": reward_data['name'],
                "type": reward_data.get('type'),
                "point_cost": reward_data['point_cost'],
                "description": reward_data.get('description'),
                "image_url": reward_data.get('image_url'),
                "expire_date": reward_data.get('expire_date')
            },
            "qr_code": qr_token,
            "remaining_points": user_points - reward_data['point_cost']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error claiming reward: {str(e)}")


@router.get("/claimed")
async def get_claimed_rewards(user_id: str = Depends(get_current_user_id)):
    try:
        db = get_db()

        result = db.table("user_rewards") \
            .select("*, rewards(*)") \
            .eq("user_id", user_id) \
            .order("claimed_at", desc=True) \
            .execute()

        return {
            "claimed_rewards": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching claimed rewards: {str(e)}")


@router.post("/use/{reward_id}")
async def use_reward(reward_id: int, user_id: str = Depends(get_current_user_id)):
    try:
        db = get_db()

        user_reward = db.table("user_rewards") \
            .select("*") \
            .eq("id", reward_id) \
            .eq("user_id", user_id) \
            .execute()

        if not user_reward.data:
            raise HTTPException(status_code=404, detail="Reward not found")

        if user_reward.data[0].get("used_at"):
            raise HTTPException(status_code=400, detail="Reward already used")

        db.table("user_rewards") \
            .update({"used_at": datetime.now().isoformat()}) \
            .eq("id", reward_id) \
            .execute()

        return {
            "status": "success",
            "message": "Reward marked as used"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error using reward: {str(e)}")
