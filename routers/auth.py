"""Authentication Router"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
from services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    get_user_id_from_token
)
from services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    nickname: Optional[str] = None


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    try:
        db = get_db()
        
        existing = db.table("users").select("id, email").eq("email", request.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        password_hash = get_password_hash(request.password)
        
        user_data = {
            "email": request.email,
            "password_hash": password_hash,
            "nickname": request.nickname or request.email.split("@")[0]
        }
        
        result = db.table("users").insert(user_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        user = result.data[0]
        user_id = user["id"]
        
        access_token = create_access_token(data={"sub": user_id})
        
        logger.info(f"User signed up: {request.email} (id: {user_id})")
        
        return TokenResponse(
            access_token=access_token,
            user_id=user_id,
            email=user["email"],
            nickname=user.get("nickname")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    try:
        db = get_db()
        
        result = db.table("users").select("id, email, password_hash, nickname").eq("email", request.email).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = result.data[0]
        
        if not user.get("password_hash"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user_id = user["id"]
        
        access_token = create_access_token(data={"sub": user_id})
        
        logger.info(f"User logged in: {request.email} (id: {user_id})")
        
        return TokenResponse(
            access_token=access_token,
            user_id=user_id,
            email=user["email"],
            nickname=user.get("nickname")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        db = get_db()
        result = db.table("users").select("id, email, nickname, joined_at").eq("id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        
        return {
            "user_id": user["id"],
            "email": user["email"],
            "nickname": user.get("nickname"),
            "joined_at": user.get("joined_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        db = get_db()
        result = db.table("users").select("id, email, nickname").eq("id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        
        new_token = create_access_token(data={"sub": user_id})
        
        return TokenResponse(
            access_token=new_token,
            user_id=user_id,
            email=user["email"],
            nickname=user.get("nickname")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )
