"""OphthalmoCapture — Whisper Transcription Service

Encapsulates all Whisper-related logic: model loading, transcription,
and segment-level timestamps.  Temporary files are ALWAYS cleaned up.
"""

import os
import shutil
import tempfile
import streamlit as st
import whisper

# ── Ensure ffmpeg is available ───────────────────────────────────────────────
# If system ffmpeg is not in PATH, use the bundled one from imageio-ffmpeg.
if shutil.which("ffmpeg") is None:
    try:
        import imageio_ffmpeg
        _ffmpeg_real = imageio_ffmpeg.get_ffmpeg_exe()
        # The bundled binary has a long name; create an alias as ffmpeg.exe
        # next to it so that Whisper (which calls "ffmpeg") can find it.
        _ffmpeg_alias = os.path.join(os.path.dirname(_ffmpeg_real), "ffmpeg.exe")
        if not os.path.exists(_ffmpeg_alias):
            try:
                os.link(_ffmpeg_real, _ffmpeg_alias)   # hard link (no admin)
            except OSError:
                import shutil as _sh
                _sh.copy2(_ffmpeg_real, _ffmpeg_alias)  # fallback: copy
        os.environ["PATH"] = (
            os.path.dirname(_ffmpeg_alias) + os.pathsep + os.environ.get("PATH", "")
        )
    except ImportError:
        pass  # Will fail later with a clear Whisper error


@st.cache_resource
def load_whisper_model(model_size: str):
    """Load and cache a Whisper model."""
    print(f"Loading Whisper model: {model_size}...")
    return whisper.load_model(model_size)


def transcribe_audio(model, audio_bytes: bytes, language: str = "es") -> str:
    """Transcribe raw WAV bytes and return plain text.

    The temporary file is **always** deleted (try/finally).
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        result = model.transcribe(tmp_path, language=language)
        return result.get("text", "").strip()
    except Exception as e:
        st.error(f"Error de transcripción: {e}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def transcribe_audio_with_timestamps(
    model, audio_bytes: bytes, language: str = "es"
) -> tuple[str, list[dict]]:
    """Transcribe raw WAV bytes and return (plain_text, segments).

    Each segment dict contains:
        {"start": float, "end": float, "text": str}

    Useful for syncing transcript highlights with audio playback.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        result = model.transcribe(tmp_path, language=language)
        text = result.get("text", "").strip()

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })

        return text, segments
    except Exception as e:
        st.error(f"Error de transcripción: {e}")
        return "", []
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
