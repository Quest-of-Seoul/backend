"""
Reward router - Points and rewards management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.db import get_db
from datetime import datetime
import secrets

router = APIRouter()


class ClaimRewardRequest(BaseModel):
    user_id: str
    reward_id: int


class AddPointsRequest(BaseModel):
    user_id: str
    points: int
    reason: str = "Quest completion"


@router.get("/points/{user_id}")
async def get_user_points(user_id: str):
    """
    Get user's total points balance
    """
    try:
        print(f"📡 Getting points for user_id: {user_id}")  # 디버그

        db = get_db()

        # Get total points using the database function
        result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        total_points = result.data if result.data else 0

        print(f"✅ Total points: {total_points}")  # 디버그

        # Get recent transactions
        transactions = db.table("points") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()

        print(f"✅ Transactions count: {len(transactions.data)}")  # 디버그

        return {
            "total_points": total_points,
            "transactions": transactions.data
        }

    except Exception as e:
        print(f"❌ Error in get_user_points: {str(e)}")  # 디버그
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching points: {str(e)}")


@router.post("/points/add")
async def add_points(request: AddPointsRequest):
    """
    Add points to user's account
    """
    try:
        print(f"📡 Adding {request.points} points to user_id: {request.user_id}")  # 디버그

        if request.points <= 0:
            raise HTTPException(status_code=400, detail="Points must be greater than 0")

        db = get_db()

        # Ensure user exists in users table (create if not exists)
        user_check = db.table("users").select("id").eq("id", request.user_id).execute()
        if not user_check.data:
            # Create user if doesn't exist
            print(f"📝 Creating user {request.user_id} in users table")
            db.table("users").insert({
                "id": request.user_id,
                "email": f"{request.user_id}@temp.com",  # Temporary email
                "nickname": "Guest User"
            }).execute()

        # Get current points balance
        current_points_result = db.rpc("get_user_points", {"user_uuid": request.user_id}).execute()
        current_points = current_points_result.data if current_points_result.data else 0

        # Add points to the points table
        db.table("points").insert({
            "user_id": request.user_id,
            "value": request.points,
            "reason": request.reason
        }).execute()

        # Calculate new balance
        new_balance = current_points + request.points

        print(f"✅ Points added successfully. New balance: {new_balance}")  # 디버그

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
        print(f"❌ Error in add_points: {str(e)}")  # 디버그
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error adding points: {str(e)}")


@router.get("/list")
async def get_available_rewards():
    """
    Get all available rewards
    """
    try:
        db = get_db()
        result = db.table("rewards") \
            .select("*") \
            .eq("is_active", True) \
            .order("point_cost") \
            .execute()

        return {
            "rewards": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rewards: {str(e)}")


@router.post("/claim")
async def claim_reward(request: ClaimRewardRequest):
    """
    Claim a reward using points
    """
    try:
        db = get_db()

        # Get reward details
        reward = db.table("rewards") \
            .select("*") \
            .eq("id", request.reward_id) \
            .eq("is_active", True) \
            .execute()

        if not reward.data:
            raise HTTPException(status_code=404, detail="Reward not found or inactive")

        reward_data = reward.data[0]

        # Get user's total points
        user_points_result = db.rpc("get_user_points", {"user_uuid": request.user_id}).execute()
        user_points = user_points_result.data if user_points_result.data else 0

        # Check if user has enough points
        if user_points < reward_data['point_cost']:
            return {
                "status": "fail",
                "message": "Not enough points",
                "required": reward_data['point_cost'],
                "current": user_points,
                "shortage": reward_data['point_cost'] - user_points
            }

        # Deduct points
        db.table("points").insert({
            "user_id": request.user_id,
            "value": -reward_data['point_cost'],
            "reason": f"Redeemed: {reward_data['name']}"
        }).execute()

        # Generate QR code (simple token for now)
        qr_token = secrets.token_urlsafe(16)

        # Add reward to user's claimed rewards
        db.table("user_rewards").insert({
            "user_id": request.user_id,
            "reward_id": request.reward_id,
            "qr_code": qr_token
        }).execute()

        return {
            "status": "success",
            "message": "Reward claimed successfully!",
            "reward": reward_data['name'],
            "qr_code": qr_token,
            "remaining_points": user_points - reward_data['point_cost']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error claiming reward: {str(e)}")


@router.get("/claimed/{user_id}")
async def get_claimed_rewards(user_id: str):
    """
    Get user's claimed rewards
    """
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
async def use_reward(reward_id: int, user_id: str):
    """
    Mark a reward as used
    """
    try:
        db = get_db()

        # Find the user's reward
        user_reward = db.table("user_rewards") \
            .select("*") \
            .eq("id", reward_id) \
            .eq("user_id", user_id) \
            .execute()

        if not user_reward.data:
            raise HTTPException(status_code=404, detail="Reward not found")

        if user_reward.data[0].get("used_at"):
            raise HTTPException(status_code=400, detail="Reward already used")

        # Mark as used
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
