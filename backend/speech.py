import os
import tempfile
import logging
from pathlib import Path

import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB cap

# MIME/extension -> pydub format mapping for common browser-recorded formats
FORMAT_BY_EXTENSION = {
    ".wav": "wav",
    ".webm": "webm",
    ".mp4": "mp4",
    ".m4a": "mp4",
    ".ogg": "ogg",
    ".aac": "aac",
    ".flac": "flac",
}


def _ensure_ffmpeg() -> None:
    """Verify FFmpeg is available to pydub; raise a clear error if not."""
    try:
        AudioSegment.converter  # pydub checks this lazily at runtime
    except Exception as exc:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. "
            "Install ffmpeg (apt-get install ffmpeg on Linux, "
            "winget install ffmpeg on Windows) to process audio."
        ) from exc


def _detect_format(audio_path: str) -> str:
    """Return the pydub format for the given file extension."""
    ext = Path(audio_path).suffix.lower()
    if ext not in FORMAT_BY_EXTENSION:
        raise ValueError(f"Unsupported audio format: {ext or '(no extension)'}")
    return FORMAT_BY_EXTENSION[ext]


def _convert_to_pcm_wav(audio_path: str) -> str:
    """
    Convert any supported browser-recorded audio file into a mono,
    16 kHz, 16-bit PCM WAV file. Returns the path to the converted WAV.
    """
    _ensure_ffmpeg()

    file_size = os.path.getsize(audio_path)
    if file_size == 0:
        raise ValueError("Audio file is empty.")
    if file_size > MAX_AUDIO_BYTES:
        raise ValueError(
            f"Audio file too large ({file_size / (1024 * 1024):.1f} MB). "
            f"Maximum is {MAX_AUDIO_BYTES / (1024 * 1024):.0f} MB."
        )

    fmt = _detect_format(audio_path)

    try:
        audio = AudioSegment.from_file(audio_path, format=fmt)
    except Exception as exc:
        raise ValueError(f"Could not read audio file ({exc}). "
                         f"The file may be corrupted or in an unsupported format.") from exc

    # Normalize: mono, 16 kHz, 16-bit PCM
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        audio.export(wav_path, format="wav", codec="pcm_s16le")
    except Exception as exc:
        try:
            os.remove(wav_path)
        except OSError:
            pass
        raise ValueError(f"Audio conversion failed: {exc}") from exc

    # Verify the converted WAV is readable
    try:
        with sr.AudioFile(wav_path) as _source:
            pass
    except Exception as exc:
        try:
            os.remove(wav_path)
        except OSError:
            pass
        raise ValueError(f"Converted WAV verification failed: {exc}") from exc

    return wav_path


def speech_to_text(audio_path: str) -> str:
    """
    Convert an audio file to Telugu text using Google Speech Recognition.

    Returns the recognized text, or a descriptive error string for known
    failure modes so callers can respond without exposing internals.
    """
    recognizer = sr.Recognizer()

    # 1. Verify the source file exists and is non-empty
    if not audio_path or not os.path.exists(audio_path):
        logger.error("Audio file not found: %s", audio_path)
        return "Audio file not found."

    if os.path.getsize(audio_path) == 0:
        logger.error("Audio file is empty: %s", audio_path)
        return "Audio file is empty."

    wav_path = audio_path
    converted = False

    # 2. Convert non-WAV audio to verified PCM WAV
    if Path(audio_path).suffix.lower() != ".wav":
        try:
            wav_path = _convert_to_pcm_wav(audio_path)
            converted = True
        except (ValueError, RuntimeError) as exc:
            logger.error("Audio conversion failed for %s: %s", audio_path, exc)
            return f"Audio processing failed: {exc}"

    # 3. Run speech recognition on the verified WAV
    try:
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data, language="te-IN")
    except sr.UnknownValueError:
        text = "Speech could not be understood"
    except sr.RequestError as exc:
        logger.error("Google Speech Recognition request error: %s", exc)
        text = f"Speech recognition service error: {exc}"
    except Exception as exc:
        logger.error("Speech recognition error: %s", exc)
        text = f"Speech recognition error: {exc}"
    finally:
        # 4. Always clean up temporary converted WAV files
        if converted and wav_path != audio_path:
            try:
                os.remove(wav_path)
            except (OSError, PermissionError):
                pass

    return text
