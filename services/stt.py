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


def detect_audio_encoding(audio_bytes: bytes) -> Optional[speech.RecognitionConfig.AudioEncoding]:
    if len(audio_bytes) < 4:
        return None
    
    if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
        logger.info("Detected WebM format, using WEBM_OPUS encoding")
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    
    if audio_bytes[:4] == b'RIFF' and len(audio_bytes) > 8 and audio_bytes[8:12] == b'WAVE':
        logger.info("Detected WAV format, using LINEAR16 encoding")
        return speech.RecognitionConfig.AudioEncoding.LINEAR16
    
    if audio_bytes[:4] == b'fLaC':
        logger.info("Detected FLAC format")
        return speech.RecognitionConfig.AudioEncoding.FLAC
    
    if audio_bytes[:4] == b'OggS':
        logger.info("Detected Ogg format, using OGG_OPUS encoding")
        return speech.RecognitionConfig.AudioEncoding.OGG_OPUS
    
    if audio_bytes[:3] == b'ID3' or (len(audio_bytes) > 2 and audio_bytes[:2] == b'\xff\xfb'):
        logger.info("Detected MP3 format, will use ENCODING_UNSPECIFIED")
        return speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    
    return None


def speech_to_text(
    audio_bytes: bytes,
    language_code: str = "en-US",
    sample_rate_hertz: Optional[int] = None,
    encoding: Optional[speech.RecognitionConfig.AudioEncoding] = None
) -> Optional[str]:
    client = get_stt_client()
    if not client:
        return None
    
    try:
        if encoding is None:
            detected_encoding = detect_audio_encoding(audio_bytes)
            if detected_encoding:
                encoding = detected_encoding
                logger.info(f"Auto-detected encoding: {encoding}")
            else:
                encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
                logger.info(f"Using default encoding: WEBM_OPUS")
        
        config_dict = {
            "language_code": language_code,
            "enable_automatic_punctuation": True,
            "encoding": encoding,
        }
        
        if sample_rate_hertz is None:
            if encoding in [
                speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            ]:
                sample_rate_hertz = 48000
            elif encoding == speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED:
                sample_rate_hertz = 16000
            else:
                sample_rate_hertz = 16000
        
        config_dict["sample_rate_hertz"] = sample_rate_hertz
        
        config = speech.RecognitionConfig(**config_dict)
        
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        response = client.recognize(config=config, audio=audio)
        
        if not response.results:
            logger.warning(f"No transcription results from Google STT API (audio length: {len(audio_bytes)} bytes, encoding: {encoding}, language: {language_code})")
            return None
        
        transcript = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        
        transcript = transcript.strip()
        
        if not transcript:
            logger.warning(f"STT transcription resulted in empty string after stripping (audio length: {len(audio_bytes)} bytes, encoding: {encoding}, language: {language_code})")
            return None
        
        logger.info(f"STT transcribed: '{transcript}' ({len(transcript)} chars)")
        return transcript
    
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        return None


def speech_to_text_from_base64(
    audio_base64: str,
    language_code: str = "en-US",
    sample_rate_hertz: Optional[int] = None,
    encoding: Optional[speech.RecognitionConfig.AudioEncoding] = None
) -> Optional[str]:
    try:
        audio_bytes = base64.b64decode(audio_base64)
        
        if len(audio_bytes) < 100:
            logger.warning(f"Audio too short for STT: {len(audio_bytes)} bytes")
            return None
        
        return speech_to_text(audio_bytes, language_code, sample_rate_hertz, encoding)
    except Exception as e:
        logger.error(f"Base64 decode error: {e}", exc_info=True)
        return None
