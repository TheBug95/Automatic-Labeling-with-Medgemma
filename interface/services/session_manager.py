"""
OphthalmoCapture — Ephemeral Session Manager

All image data lives exclusively in st.session_state (RAM).
Nothing is written to disk. Data is only persisted when the user
explicitly downloads their labeling package.
"""

import streamlit as st
import uuid
import datetime
import gc


def init_session():
    """Initialize the ephemeral session data model."""
    if "session_initialized" not in st.session_state:
        st.session_state.session_initialized = True
        st.session_state.session_id = str(uuid.uuid4())  # unique per session
        st.session_state.images = {}            # {uuid_str: image_data_dict}
        st.session_state.image_order = []       # [uuid_str, ...] upload order
        st.session_state.current_image_id = None
        st.session_state.last_activity = datetime.datetime.now()
        st.session_state.doctor_name = ""
        st.session_state.confirm_end_session = False


def add_image(filename: str, image_bytes: bytes) -> str:
    """Add an uploaded image to the in-memory session store.

    Returns the generated UUID for the image.
    """
    img_id = str(uuid.uuid4())
    st.session_state.images[img_id] = {
        "filename": filename,
        "bytes": image_bytes,
        "label": None,                 # Set during labeling (Phase 3)
        "audio_bytes": None,           # WAV from recording (Phase 4)
        "transcription": "",           # Editable transcription text
        "transcription_original": "",  # Original Whisper output (read-only)
        "timestamp": datetime.datetime.now(),
        "labeled_by": st.session_state.get("doctor_name", ""),
    }
    st.session_state.image_order.append(img_id)
    update_activity()
    return img_id


def remove_image(img_id: str):
    """Remove a single image from the session, freeing memory."""
    if img_id in st.session_state.images:
        # Explicitly clear heavy byte fields before deletion
        st.session_state.images[img_id]["bytes"] = None
        st.session_state.images[img_id]["audio_bytes"] = None
        del st.session_state.images[img_id]

    if img_id in st.session_state.image_order:
        st.session_state.image_order.remove(img_id)

    # Update current selection if the deleted image was active
    if st.session_state.current_image_id == img_id:
        if st.session_state.image_order:
            st.session_state.current_image_id = st.session_state.image_order[0]
        else:
            st.session_state.current_image_id = None


def get_current_image():
    """Get the data dict for the currently selected image, or None."""
    img_id = st.session_state.get("current_image_id")
    if img_id and img_id in st.session_state.images:
        return st.session_state.images[img_id]
    return None


def get_current_image_id():
    """Get the UUID of the currently selected image."""
    return st.session_state.get("current_image_id")


def set_current_image(img_id: str):
    """Set the currently active image by UUID."""
    if img_id in st.session_state.images:
        st.session_state.current_image_id = img_id
        update_activity()


def get_image_count() -> int:
    """Total number of images in session."""
    return len(st.session_state.images)


def get_labeling_progress():
    """Return (labeled_count, total_count)."""
    total = len(st.session_state.images)
    labeled = sum(
        1 for img in st.session_state.images.values()
        if img["label"] is not None
    )
    return labeled, total


def has_undownloaded_data() -> bool:
    """Check if there is any data in the session."""
    return len(st.session_state.images) > 0


def update_activity():
    """Update the last activity timestamp."""
    st.session_state.last_activity = datetime.datetime.now()


def check_session_timeout(timeout_minutes: int = 30) -> bool:
    """Return True if the session has exceeded the inactivity timeout."""
    last = st.session_state.get("last_activity")
    if last:
        elapsed = (datetime.datetime.now() - last).total_seconds() / 60
        return elapsed > timeout_minutes
    return False


def clear_session():
    """Completely wipe all session data — images, audio, everything.

    Called on explicit cleanup or session timeout.
    """
    # Explicitly null out heavy byte fields to help garbage collection
    for img in st.session_state.get("images", {}).values():
        img["bytes"] = None
        img["audio_bytes"] = None
    st.session_state.clear()
    gc.collect()


def get_remaining_timeout_minutes(timeout_minutes: int = 30) -> float:
    """Return how many minutes remain before timeout, or 0 if already expired."""
    last = st.session_state.get("last_activity")
    if not last:
        return 0.0
    elapsed = (datetime.datetime.now() - last).total_seconds() / 60
    remaining = timeout_minutes - elapsed
    return max(0.0, remaining)


def get_session_data_summary() -> dict:
    """Return a summary of what data exists in the session (for warnings)."""
    images = st.session_state.get("images", {})
    total = len(images)
    labeled = sum(1 for img in images.values() if img["label"] is not None)
    with_audio = sum(1 for img in images.values() if img["audio_bytes"] is not None)
    with_text = sum(1 for img in images.values() if img["transcription"])
    return {
        "total": total,
        "labeled": labeled,
        "with_audio": with_audio,
        "with_transcription": with_text,
    }
