"""OphthalmoCapture — Audio Recorder & Transcription Component

Records audio via st.audio_input, transcribes with Whisper, stores the
audio bytes and transcription in the ephemeral session, and lets the
doctor edit the transcription or restore the original.

Includes timestamped segments from Whisper for reference.
"""

import hashlib
import streamlit as st
import database as db
from services import session_manager as sm
from services.whisper_service import transcribe_audio_with_timestamps, format_timestamp


def _audio_fingerprint(audio_bytes: bytes) -> str:
    """Return a short hash of the audio content for change detection."""
    return hashlib.md5(audio_bytes).hexdigest()


def render_recorder(image_id: str, model, language: str):
    """Render the audio recording + transcription panel.

    Parameters
    ----------
    image_id : str
        UUID of the currently selected image.
    model :
        Loaded Whisper model instance.
    language : str
        ISO language code for transcription (e.g. "es").
    """
    img = st.session_state.images.get(image_id)
    if img is None:
        return

    st.subheader("🎙️ Dictado y Transcripción")

    # ── Audio recording ──────────────────────────────────────────────────
    audio_wav = st.audio_input(
        "Grabar audio",
        key=f"audio_input_{image_id}",
    )

    # Track which audio blob we already processed so we don't re-transcribe
    processed_key = f"_last_audio_{image_id}"
    segments_key = f"_segments_{image_id}"

    if audio_wav is not None:
        audio_bytes = audio_wav.getvalue()
        fingerprint = _audio_fingerprint(audio_bytes)

        # Only transcribe if this is a *new* recording (content changed)
        if st.session_state.get(processed_key) != fingerprint:
            with st.spinner("Transcribiendo audio…"):
                text, segments = transcribe_audio_with_timestamps(
                    model, audio_bytes, language
                )

            # Store in session
            img["audio_bytes"] = audio_bytes

            # Append (don't overwrite) if there was previous text
            if img["transcription"]:
                img["transcription"] += " " + text
            else:
                img["transcription"] = text

            # Keep a copy of the raw Whisper output
            if img["transcription_original"]:
                img["transcription_original"] += " " + text
            else:
                img["transcription_original"] = text

            # Store timestamped segments
            existing_segments = st.session_state.get(segments_key, [])
            st.session_state[segments_key] = existing_segments + segments

            # Mark this audio as processed using content hash (stable across reruns)
            st.session_state[processed_key] = fingerprint
            # Update the text_area widget state so it reflects the new text
            st.session_state[f"transcription_area_{image_id}"] = img["transcription"]

            # Re-save to audit DB if the image is already labeled (upsert)
            if img.get("label"):
                try:
                    db.save_or_update_annotation(
                        image_filename=img["filename"],
                        label=img["label"],
                        transcription=img["transcription"],
                        doctor_name=st.session_state.get("doctor_name", ""),
                        session_id=st.session_state.get("session_id", ""),
                        locs_data=img.get("locs_data", {}),
                    )
                except Exception:
                    pass

            sm.update_activity()
            st.rerun()

    # ── Editable transcription ───────────────────────────────────────────
    edited_text = st.text_area(
        "Transcripción (editable)",
        value=img["transcription"],
        height=180,
        key=f"transcription_area_{image_id}",
        placeholder="Grabe un audio o escriba la transcripción manualmente…",
    )

    # Sync edits back to session
    if edited_text != img["transcription"]:
        img["transcription"] = edited_text
        sm.update_activity()

    # ── Timestamped segments (Idea C) ────────────────────────────────────
    segments = st.session_state.get(segments_key, [])
    if segments:
        with st.expander("🕐 Segmentos con timestamps", expanded=False):
            for seg in segments:
                ts_start = format_timestamp(seg["start"])
                ts_end = format_timestamp(seg["end"])
                st.markdown(
                    f"`{ts_start} → {ts_end}` &nbsp; {seg['text']}"
                )

    # ── Helper buttons ───────────────────────────────────────────────────
    btn_cols = st.columns(3)

    with btn_cols[0]:
        # Re-record: clear audio and transcription so a new recording can be made
        has_audio = img["audio_bytes"] is not None
        if st.button(
            "🎤 Volver a grabar",
            key=f"rerecord_{image_id}",
            disabled=not has_audio,
            use_container_width=True,
        ):
            img["audio_bytes"] = None
            img["transcription"] = ""
            img["transcription_original"] = ""
            st.session_state.pop(segments_key, None)
            st.session_state.pop(processed_key, None)
            # Clear both text_area and audio_input widget states
            st.session_state[f"transcription_area_{image_id}"] = ""
            st.session_state.pop(f"audio_input_{image_id}", None)
            sm.update_activity()
            st.rerun()

    with btn_cols[1]:
        # Restore original Whisper transcription
        has_original = bool(img["transcription_original"])
        is_different = img["transcription"] != img["transcription_original"]
        if st.button(
            "🔄 Restaurar original",
            key=f"restore_{image_id}",
            disabled=not (has_original and is_different),
            use_container_width=True,
        ):
            img["transcription"] = img["transcription_original"]
            st.session_state[f"transcription_area_{image_id}"] = img["transcription_original"]
            sm.update_activity()
            st.rerun()

    with btn_cols[2]:
        # Clear transcription entirely
        if st.button(
            "🗑️ Limpiar texto",
            key=f"clear_text_{image_id}",
            disabled=not img["transcription"],
            use_container_width=True,
        ):
            img["transcription"] = ""
            st.session_state[f"transcription_area_{image_id}"] = ""
            sm.update_activity()
            st.rerun()

    # ── Status line ──────────────────────────────────────────────────────
    if img["transcription"]:
        modified_tag = ""
        if (
            img["transcription_original"]
            and img["transcription"] != img["transcription_original"]
        ):
            modified_tag = "  ✏️ _modificada manualmente_"
        word_count = len(img["transcription"].split())
        st.caption(f"{word_count} palabras{modified_tag}")
    else:
        st.caption("Sin transcripción aún.")
