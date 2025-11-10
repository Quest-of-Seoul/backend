"""
Supabase Storage service - File upload and management
"""

from supabase import Client
from services.db import get_db
import uuid
import os
from typing import Optional


def upload_audio_to_storage(audio_bytes: bytes, filename: Optional[str] = None) -> Optional[str]:
    """
    Upload audio file to Supabase Storage and return public URL

    Args:
        audio_bytes: Audio file content as bytes
        filename: Optional custom filename (auto-generated if not provided)

    Returns:
        Public URL of uploaded file, or None if upload fails
    """
    try:
        supabase: Client = get_db()

        # Generate unique filename if not provided
        if not filename:
            filename = f"tts_{uuid.uuid4()}.mp3"
        elif not filename.endswith('.mp3'):
            filename = f"{filename}.mp3"

        # Upload to Supabase Storage 'tts' bucket
        response = supabase.storage.from_("tts").upload(
            path=filename,
            file=audio_bytes,
            file_options={
                "content-type": "audio/mpeg",
                "cache-control": "3600",  # Cache for 1 hour
                "upsert": "true"  # Overwrite if exists
            }
        )

        print(f"[Storage] Upload response: {response}")

        # Get public URL
        public_url = supabase.storage.from_("tts").get_public_url(filename)

        # Remove trailing '?' if present
        if public_url and public_url.endswith('?'):
            public_url = public_url[:-1]

        print(f"[Storage] ✅ Audio uploaded: {public_url}")
        return public_url

    except Exception as e:
        print(f"[Storage] ❌ Upload failed: {e}")
        return None


def delete_audio_from_storage(filename: str) -> bool:
    """
    Delete audio file from Supabase Storage

    Args:
        filename: Name of file to delete

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        supabase: Client = get_db()

        response = supabase.storage.from_("tts").remove([filename])

        print(f"[Storage] ✅ Deleted: {filename}")
        return True

    except Exception as e:
        print(f"[Storage] ❌ Delete failed: {e}")
        return False


def list_audio_files(limit: int = 100) -> list:
    """
    List audio files in Supabase Storage

    Args:
        limit: Maximum number of files to return

    Returns:
        List of file objects
    """
    try:
        supabase: Client = get_db()

        response = supabase.storage.from_("tts").list(
            options={"limit": limit, "sortBy": {"column": "created_at", "order": "desc"}}
        )

        return response

    except Exception as e:
        print(f"[Storage] ❌ List failed: {e}")
        return []


def cleanup_old_files(hours: int = 24) -> int:
    """
    Clean up audio files older than specified hours

    Args:
        hours: Delete files older than this many hours

    Returns:
        Number of files deleted
    """
    try:
        from datetime import datetime, timedelta

        supabase: Client = get_db()

        # Get all files
        files = supabase.storage.from_("tts").list()

        # Calculate cutoff time
        cutoff = datetime.now() - timedelta(hours=hours)

        # Filter old files
        old_files = []
        for file in files:
            created_at = datetime.fromisoformat(file.get("created_at", "").replace("Z", "+00:00"))
            if created_at < cutoff:
                old_files.append(file["name"])

        # Delete old files
        if old_files:
            supabase.storage.from_("tts").remove(old_files)
            print(f"[Storage] 🗑️  Cleaned up {len(old_files)} old files")
            return len(old_files)

        print(f"[Storage] No files to clean up")
        return 0

    except Exception as e:
        print(f"[Storage] ❌ Cleanup failed: {e}")
        return 0


# ============================================================
# Image Upload Functions (for VLM images)
# ============================================================

def upload_image_to_storage(
    image_bytes: bytes, 
    filename: Optional[str] = None,
    bucket: str = "images"
) -> Optional[str]:
    """
    이미지를 Supabase Storage에 업로드
    
    Args:
        image_bytes: 이미지 바이트 데이터
        filename: 파일명 (없으면 UUID 생성)
        bucket: 스토리지 버킷명
    
    Returns:
        Public URL 또는 None
    """
    try:
        from PIL import Image
        from io import BytesIO
        import hashlib
        
        supabase: Client = get_db()
        
        # 이미지 형식 감지
        img = Image.open(BytesIO(image_bytes))
        img_format = img.format.lower() if img.format else 'jpeg'
        
        # 파일명 생성
        if not filename:
            # 이미지 해시 사용 (중복 방지)
            img_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
            filename = f"place_{img_hash}.{img_format}"
        
        # Content-Type 설정
        content_type_map = {
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'gif': 'image/gif'
        }
        content_type = content_type_map.get(img_format, 'image/jpeg')
        
        # Supabase Storage 업로드
        response = supabase.storage.from_(bucket).upload(
            path=filename,
            file=image_bytes,
            file_options={
                "content-type": content_type,
                "cache-control": "31536000",  # 1년 캐싱
                "upsert": "true"
            }
        )
        
        print(f"[Storage] Upload response: {response}")
        
        # Public URL 생성
        public_url = supabase.storage.from_(bucket).get_public_url(filename)
        
        # Trailing '?' 제거
        if public_url and public_url.endswith('?'):
            public_url = public_url[:-1]
        
        print(f"[Storage] ✅ Image uploaded: {public_url}")
        return public_url
    
    except Exception as e:
        print(f"[Storage] ❌ Image upload failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compress_and_upload_image(
    image_bytes: bytes,
    max_size: int = 1920,
    quality: int = 85,
    bucket: str = "images"
) -> Optional[str]:
    """
    이미지를 압축한 후 업로드 (용량 절약)
    
    Args:
        image_bytes: 원본 이미지
        max_size: 최대 가로/세로 픽셀
        quality: JPEG 품질 (1-100)
        bucket: 스토리지 버킷명
    
    Returns:
        Public URL 또는 None
    """
    try:
        from PIL import Image, ImageOps
        from io import BytesIO
        
        # 이미지 로드
        img = Image.open(BytesIO(image_bytes))
        
        # EXIF 회전 정보 적용
        try:
            img = ImageOps.exif_transpose(img)
        except:
            pass
        
        # RGB 변환
        if img.mode in ('RGBA', 'P', 'LA'):
            # 투명 배경 → 흰색
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 리사이징 (비율 유지)
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            print(f"[Storage] Resized to: {img.size}")
        
        # JPEG 압축
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_bytes = output.getvalue()
        
        original_size = len(image_bytes) / 1024  # KB
        compressed_size = len(compressed_bytes) / 1024  # KB
        print(f"[Storage] Compressed: {original_size:.1f}KB → {compressed_size:.1f}KB")
        
        # 업로드
        return upload_image_to_storage(compressed_bytes, bucket=bucket)
    
    except Exception as e:
        print(f"[Storage] ❌ Compression failed: {e}")
        # 실패 시 원본 업로드 시도
        return upload_image_to_storage(image_bytes, bucket=bucket)


def delete_image_from_storage(filename: str, bucket: str = "images") -> bool:
    """
    이미지 삭제
    
    Args:
        filename: 파일명
        bucket: 버킷명
    
    Returns:
        성공 여부
    """
    try:
        supabase: Client = get_db()
        response = supabase.storage.from_(bucket).remove([filename])
        print(f"[Storage] ✅ Image deleted: {filename}")
        return True
    
    except Exception as e:
        print(f"[Storage] ❌ Image delete failed: {e}")
        return False
