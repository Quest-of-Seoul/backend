"""
Text-to-Speech service - Google Cloud TTS
"""

from google.cloud import texttospeech
import os
import base64
from typing import Optional, Tuple
from services.storage import upload_audio_to_storage

# Initialize TTS client
def get_tts_client():
    """Initialize Google Cloud TTS client with service account"""
    # Set credentials from environment variable
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        return texttospeech.TextToSpeechClient()
    else:
        # If credentials file not set, return None
        # TTS will be disabled
        return None


def text_to_speech_bytes(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None,
    speaking_rate: float = 1.0,
    pitch: float = 0.0
) -> Optional[bytes]:
    """
    Convert text to speech audio (returns raw bytes)

    Args:
        text: Text to convert
        language_code: Language code (ko-KR, en-US, etc.)
        voice_name: Specific voice name (optional)
        speaking_rate: Speech speed (0.25 to 4.0, default 1.0)
        pitch: Voice pitch (-20.0 to 20.0, default 0.0)

    Returns:
        Audio bytes (MP3) or None if TTS unavailable
    """

    client = get_tts_client()
    if not client:
        print("[TTS] ⚠️  Warning: TTS client not initialized. Check GOOGLE_APPLICATION_CREDENTIALS.")
        return None

    try:
        # Set up synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Voice selection
        if not voice_name:
            # Default voices based on language
            voice_name = {
                "ko-KR": "ko-KR-Wavenet-A",  # Female Korean voice
                "en-US": "en-US-Wavenet-F",  # Female English voice
            }.get(language_code, "ko-KR-Wavenet-A")

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )

        # Audio config with quality settings
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate_hertz=24000,  # Higher quality
            effects_profile_id=["small-bluetooth-speaker-class-device"]  # Optimized for mobile
        )

        # Perform TTS request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        print(f"[TTS] ✅ Generated audio for text: {text[:50]}...")
        return response.audio_content

    except Exception as e:
        print(f"[TTS] ❌ Error in TTS: {e}")
        return None


def text_to_speech(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None
) -> Optional[str]:
    """
    Convert text to speech audio (returns base64)

    Args:
        text: Text to convert
        language_code: Language code (ko-KR, en-US, etc.)
        voice_name: Specific voice name (optional)

    Returns:
        Base64-encoded audio data (MP3) or None if TTS unavailable
    """

    audio_bytes = text_to_speech_bytes(text, language_code, voice_name)

    if audio_bytes:
        return base64.b64encode(audio_bytes).decode('utf-8')
    return None


def text_to_speech_url(
    text: str,
    language_code: str = "ko-KR",
    voice_name: Optional[str] = None,
    upload_to_storage: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert text to speech and upload to Supabase Storage

    Args:
        text: Text to convert
        language_code: Language code (ko-KR, en-US, etc.)
        voice_name: Specific voice name (optional)
        upload_to_storage: Whether to upload to Supabase Storage

    Returns:
        Tuple of (audio_url, base64_audio)
        - audio_url: Public URL from Supabase Storage (or None)
        - base64_audio: Base64-encoded audio as fallback
    """

    audio_bytes = text_to_speech_bytes(text, language_code, voice_name)

    if not audio_bytes:
        return None, None

    # Generate base64 as fallback
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')

    # Upload to Supabase Storage if requested
    audio_url = None
    if upload_to_storage:
        audio_url = upload_audio_to_storage(audio_bytes)

    return audio_url, base64_audio
