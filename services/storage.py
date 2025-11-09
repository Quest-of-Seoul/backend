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
