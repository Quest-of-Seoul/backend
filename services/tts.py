"""Text-to-Speech Service"""

from google.cloud import texttospeech
import os
import logging
import base64
from typing import Optional, Tuple
from services.storage import upload_audio_to_storage

logger = logging.getLogger(__name__)


def get_tts_client():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        return texttospeech.TextToSpeechClient()
    else:
        logger.warning("TTS credentials not found")
        return None


def text_to_speech_bytes(
    text: str,
    language_code: str = "en-US",
    voice_name: Optional[str] = None,
    speaking_rate: float = 1.0,
    pitch: float = 0.0
) -> Optional[bytes]:
    """Convert text to speech"""
    client = get_tts_client()
    if not client:
        return None
    
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        if not voice_name:
            voice_name = {
                "ko-KR": "ko-KR-Wavenet-A",
                "en-US": "en-US-Wavenet-F",
            }.get(language_code, "en-US-Wavenet-F")
        
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


def text_to_speech(
    text: str,
    language_code: str = "en-US",
    voice_name: Optional[str] = None
) -> Optional[str]:
    """Convert text to speech (returns base64)"""
    audio_bytes = text_to_speech_bytes(text, language_code, voice_name)
    
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode('utf-8')
    return None


def text_to_speech_url(
    text: str,
    language_code: str = "en-US",
    voice_name: Optional[str] = None,
    upload_to_storage: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """Convert text to speech and upload to storage"""
    audio_bytes = text_to_speech_bytes(text, language_code, voice_name)
    
    if not audio_bytes:
        return None, None
    
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    
    audio_url = None
    if upload_to_storage:
        audio_url = upload_audio_to_storage(audio_bytes)
    
    return audio_url, base64_audio
