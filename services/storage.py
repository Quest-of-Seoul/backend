"""Supabase Storage Service"""

from supabase import Client
from services.db import get_db
import uuid
import os
import logging
from typing import Optional
from PIL import Image, ImageOps
from io import BytesIO
import hashlib

logger = logging.getLogger(__name__)


def upload_audio_to_storage(audio_bytes: bytes, filename: Optional[str] = None) -> Optional[str]:
    """Upload audio file to Supabase Storage"""
    try:
        supabase: Client = get_db()

        if not filename:
            filename = f"tts_{uuid.uuid4()}.mp3"
        elif not filename.endswith('.mp3'):
            filename = f"{filename}.mp3"

        response = supabase.storage.from_("tts").upload(
            path=filename,
            file=audio_bytes,
            file_options={
                "content-type": "audio/mpeg",
                "cache-control": "3600",
                "upsert": "true"
            }
        )

        logger.debug(f"Upload response: {response}")

        public_url = supabase.storage.from_("tts").get_public_url(filename)

        if public_url and public_url.endswith('?'):
            public_url = public_url[:-1]

        logger.info(f"Audio uploaded: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return None


def compress_and_upload_image(
    image_bytes: bytes,
    max_size: int = 1920,
    quality: int = 85,
    bucket: str = "images"
) -> Optional[str]:
    """Compress and upload image to Supabase Storage"""
    try:
        supabase: Client = get_db()
        
        img = Image.open(BytesIO(image_bytes))
        
        try:
            img = ImageOps.exif_transpose(img)
        except:
            pass
        
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logger.info(f"Resized to: {img.size}")
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_bytes = output.getvalue()
        
        original_size = len(image_bytes) / 1024
        compressed_size = len(compressed_bytes) / 1024
        logger.info(f"Compressed: {original_size:.1f}KB → {compressed_size:.1f}KB")
        
        img_hash = hashlib.sha256(compressed_bytes).hexdigest()[:16]
        filename = f"place_{img_hash}.jpeg"
        
        content_type = 'image/jpeg'
        
        response = supabase.storage.from_(bucket).upload(
            path=filename,
            file=compressed_bytes,
            file_options={
                "content-type": content_type,
                "cache-control": "31536000",
                "upsert": "true"
            }
        )
        
        public_url = supabase.storage.from_(bucket).get_public_url(filename)
        
        if public_url and public_url.endswith('?'):
            public_url = public_url[:-1]
        
        logger.info(f"Image uploaded: {public_url}")
        return public_url
    
    except Exception as e:
        logger.error(f"Image upload failed: {e}", exc_info=True)
        return None
