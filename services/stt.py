"""Speech-to-Text Service"""

from google.cloud import speech
import os
import logging
from typing import Optional
import base64

logger = logging.getLogger(__name__)


def get_stt_client():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        return speech.SpeechClient()
    else:
        logger.warning("STT credentials not found")
        return None


def speech_to_text(
    audio_bytes: bytes,
    language_code: str = "en-US",
    sample_rate_hertz: int = 16000,
    encoding: Optional[speech.RecognitionConfig.AudioEncoding] = None
) -> Optional[str]:
    client = get_stt_client()
    if not client:
        return None
    
    try:
        config_dict = {
            "sample_rate_hertz": sample_rate_hertz,
            "language_code": language_code,
            "enable_automatic_punctuation": True,
        }
        
        if encoding is not None:
            config_dict["encoding"] = encoding
        
        config = speech.RecognitionConfig(**config_dict)
        
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        response = client.recognize(config=config, audio=audio)
        
        if not response.results:
            logger.warning("No transcription results")
            return None
        
        transcript = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        
        logger.info(f"STT transcribed: {len(transcript)} chars")
        return transcript.strip()
    
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        return None


def speech_to_text_from_base64(
    audio_base64: str,
    language_code: str = "en-US",
    sample_rate_hertz: int = 16000,
    encoding: Optional[speech.RecognitionConfig.AudioEncoding] = None
) -> Optional[str]:
    try:
        audio_bytes = base64.b64decode(audio_base64)
        return speech_to_text(audio_bytes, language_code, sample_rate_hertz, encoding)
    except Exception as e:
        logger.error(f"Base64 decode error: {e}", exc_info=True)
        return None
