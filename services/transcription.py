"""FieldOps AI — Transcription Service using Groq Whisper API."""

import logging
import tempfile
import os

from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

# Known Whisper hallucinations on silence/quiet audio
HALLUCINATIONS = {
    "thank you", "thanks for watching", "thanks for listening",
    "bye", "goodbye", "see you", "you", "thanks", "the end",
    "subtitles by", "thank you for watching",
}


async def transcribe_audio(audio_file) -> str:
    """
    Transcribe an audio file using Groq's Whisper Large v3 API.

    Args:
        audio_file: File-like object (from FastAPI UploadFile)

    Returns:
        Transcript text string
    """
    logger.info("Starting audio transcription via Groq Whisper...")

    try:
        content = await audio_file.read()
        logger.info(f"Received audio file, size: {len(content)} bytes")

        if len(content) < 1000:
            raise Exception("Audio file too small — please record a longer clip.")

        # Write to temp file (Groq API needs a file object)
        suffix = ".webm"
        if audio_file.content_type and "wav" in audio_file.content_type:
            suffix = ".wav"
        elif audio_file.content_type and "mp3" in audio_file.content_type:
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY,
            )

            with open(tmp_path, "rb") as audio:
                response = client.audio.transcriptions.create(
                    model=settings.GROQ_WHISPER_MODEL,
                    file=audio,
                    language="en",
                )

            transcript = response.text.strip()
            logger.info(f"Raw transcript: {transcript}")

            # Detect hallucinations
            if transcript.lower().strip(". !") in HALLUCINATIONS:
                logger.warning(f"Detected hallucination: '{transcript}'")
                raise Exception(
                    f"Could not transcribe — got '{transcript}'. "
                    "Speak louder and closer to the mic, record for at least 3 seconds."
                )

            if len(transcript) < 5:
                raise Exception("Transcript too short. Please speak clearly for at least 3 seconds.")

            logger.info(f"Final transcript: {transcript}")
            return transcript

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise
