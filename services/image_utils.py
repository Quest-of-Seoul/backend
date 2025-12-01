"""Image Utilities"""

import logging
import requests
import hashlib
from typing import Optional, Tuple
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


def download_image(image_url: str, timeout: int = 10, max_size_mb: int = 10) -> Optional[bytes]:
    if not image_url:
        return None
    
    try:
        logger.info(f"Downloading image: {image_url[:80]}...")
        response = requests.get(image_url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            logger.warning(f"Not an image: {content_type}")
            return None
        
        content_length = response.headers.get('Content-Length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > max_size_mb:
                logger.warning(f"Image too large: {size_mb:.2f}MB > {max_size_mb}MB")
                return None
        
        image_bytes = response.content
        
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"Image too large: {size_mb:.2f}MB > {max_size_mb}MB")
            return None
        
        try:
            img = Image.open(BytesIO(image_bytes))
            img.verify()
            logger.info(f"Image downloaded successfully: {len(image_bytes)} bytes")
            return image_bytes
        except Exception as e:
            logger.warning(f"Invalid image: {e}")
            return None
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download image: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {e}", exc_info=True)
        return None


def hash_image(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()
