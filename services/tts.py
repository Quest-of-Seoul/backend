"""Text-to-Speech Service"""

from google.cloud import texttospeech
import os
import logging
import base64
import asyncio
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from services.storage import upload_audio_to_storage
from services.cache import get_tts_cache, cache_key_tts

logger = logging.getLogger(__name__)

_tts_client = None
_executor = ThreadPoolExecutor(max_workers=3)


def get_tts_client():
    """Get or create TTS client (singleton)"""
    global _tts_client
    if _tts_client is None:
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            _tts_client = texttospeech.TextToSpeechClient()
            logger.info("TTS client initialized")
        else:
            logger.warning("TTS credentials not found")
    return _tts_client


def _text_to_speech_bytes_sync(
    text: str,
    language_code: str,
    voice_name: Optional[str],
    speaking_rate: float,
    pitch: float
) -> Optional[bytes]:
    """Synchronous TTS generation"""
    client = get_tts_client()
    if not client:
        return None
    
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        if not voice_name:
            voice_name = {
                "ko-KR": "ko-KR-Wavenet-A",
                "en-US": "en-US-Wavenet-F",
            }.get(language_code, "ko-KR-Wavenet-A")
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate_hertz=24000,
            effects_profile_id=["small-bluetooth-speaker-class-device"]
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        logger.info(f"TTS generated: {len(response.audio_content)} bytes")
        return response.audio_content
    
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        return None


async def text_to_speech_bytes(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None,
    speaking_rate: float = 1.0,
    pitch: float = 0.0
) -> Optional[bytes]:
    """Convert text to speech with caching"""
    cache = get_tts_cache()
    cache_key = cache_key_tts(text, language_code)
    
    if voice_name is None and speaking_rate == 1.0 and pitch == 0.0:
        cached_audio = cache.get(cache_key)
        if cached_audio is not None:
            logger.info(f"Using cached TTS: {len(cached_audio)} bytes")
            return cached_audio
    
    loop = asyncio.get_event_loop()
    audio_bytes = await loop.run_in_executor(
        _executor,
        _text_to_speech_bytes_sync,
        text, language_code, voice_name, speaking_rate, pitch
    )
    
    if audio_bytes and voice_name is None and speaking_rate == 1.0 and pitch == 0.0:
        cache.set(cache_key, audio_bytes, ttl=86400)  # 24 hours
    
    return audio_bytes


async def text_to_speech(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None
) -> Optional[str]:
    """Convert text to speech (returns base64)"""
    audio_bytes = await text_to_speech_bytes(text, language_code, voice_name)
    
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode('utf-8')
    return None


async def text_to_speech_url(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None,
    upload_to_storage: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """Convert text to speech and upload to storage"""
    audio_bytes = await text_to_speech_bytes(text, language_code, voice_name)
    
    if not audio_bytes:
        return None, None
    
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    
    audio_url = None
    if upload_to_storage:
        loop = asyncio.get_event_loop()
        audio_url = await loop.run_in_executor(_executor, upload_audio_to_storage, audio_bytes)
    
    return audio_url, base64_audio
