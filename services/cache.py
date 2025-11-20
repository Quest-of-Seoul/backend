"""Cache Service - Simple in-memory cache with TTL"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
import hashlib
import json

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple TTL-based cache"""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry['expires_at']
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


_image_embedding_cache = TTLCache(default_ttl=86400)  # 24 hours
_place_cache = TTLCache(default_ttl=3600)  # 1 hour
_tts_cache = TTLCache(default_ttl=86400)  # 24 hours


def get_image_embedding_cache() -> TTLCache:
    """Get image embedding cache"""
    return _image_embedding_cache


def get_place_cache() -> TTLCache:
    """Get place cache"""
    return _place_cache


def get_tts_cache() -> TTLCache:
    """Get TTS cache"""
    return _tts_cache


def cache_key_image(image_bytes: bytes) -> str:
    """Generate cache key for image"""
    return f"img:{hashlib.sha256(image_bytes).hexdigest()}"


def cache_key_place(place_id: str) -> str:
    """Generate cache key for place"""
    return f"place:{place_id}"


def cache_key_tts(text: str, language_code: str) -> str:
    """Generate cache key for TTS"""
    key_str = f"{text}:{language_code}"
    return f"tts:{hashlib.md5(key_str.encode()).hexdigest()}"


def cached(ttl: Optional[int] = None):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key_parts = [func.__name__]
            cache_key_parts.extend(str(arg) for arg in args)
            cache_key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(cache_key_parts).encode()).hexdigest()
            
            cache = get_tts_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator
