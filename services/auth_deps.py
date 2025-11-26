"""Authentication Dependencies for FastAPI"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
from services.auth import decode_access_token, get_user_id_from_token
from services.db import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    현재 인증된 사용자의 ID를 반환하는 의존성 함수
    - Authorization 헤더에서 Bearer 토큰을 추출
    - 토큰에서 user_id 추출
    - 토큰이 없거나 유효하지 않으면 401 에러
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 존재 확인
    db = get_db()
    result = db.table("users").select("id").eq("id", user_id).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_id


async def get_current_user_id_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    현재 인증된 사용자의 ID를 반환하는 의존성 함수 (선택적)
    - 토큰이 없으면 None 반환 (에러 없음)
    - 토큰이 있지만 유효하지 않으면 401 에러
    - 인증이 선택적인 엔드포인트에서 사용
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # 사용자 존재 확인
    db = get_db()
    result = db.table("users").select("id").eq("id", user_id).execute()
    
    if not result.data or len(result.data) == 0:
        return None
    
    return user_id
