"""Text-to-Speech Service"""

from google.cloud import texttospeech
import os
import logging
from typing import Optional

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
    language_code: str = "ko-KR",
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


def text_to_speech(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None
) -> Optional[bytes]:
    """Convert text to speech"""
    return text_to_speech_bytes(text, language_code, voice_name)
