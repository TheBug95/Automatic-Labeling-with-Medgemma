"""OphthalmoCapture — Labeling Component

Provides the radio-button selector for classifying images (e.g. catarata /
no catarata) and persists the choice in the ephemeral session.  The label
list is driven by config.LABEL_OPTIONS so it can be extended without touching
this component.
"""

import streamlit as st
import config
import database as db
from services import session_manager as sm


def render_labeler(image_id: str):
    """Render the labeling panel for the given image.

    Displays a radio selector, saves the label into session state and
    optionally persists metadata to the audit database.
    """
    img = st.session_state.images.get(image_id)
    if img is None:
        return

    st.subheader("🏷️ Etiquetado")

    display_options = [opt["display"] for opt in config.LABEL_OPTIONS]
    current_label = img.get("label")

    # Determine current index (None if unlabeled)
    if current_label is not None and current_label in display_options:
        current_index = display_options.index(current_label)
    else:
        current_index = None

    # Styled container with radio buttons
    with st.container(border=True):
        if current_index is None:
            st.caption("⬇️ Seleccione una etiqueta para esta imagen")

        selected = st.radio(
            "Clasificación",
            display_options,
            index=current_index,
            key=f"label_radio_{image_id}",
            horizontal=True,
            label_visibility="collapsed",
        )

    # Map selection
    new_label = selected if selected in display_options else None

    # Detect change, update session and auto-save to DB
    if new_label is not None and new_label != current_label:
        st.session_state.images[image_id]["label"] = new_label
        st.session_state.images[image_id]["labeled_by"] = st.session_state.get(
            "doctor_name", ""
        )
        sm.update_activity()

        # Auto-save to audit DB (upsert — one record per image per session)
        try:
            db.save_or_update_annotation(
                image_filename=img["filename"],
                label=new_label,
                transcription=img.get("transcription", ""),
                doctor_name=st.session_state.get("doctor_name", ""),
                session_id=st.session_state.get("session_id", ""),
            )
        except Exception:
            pass  # Non-blocking: audit DB failure should not break labeling

    # ── Visual feedback ──────────────────────────────────────────────────
    if new_label is None:
        st.warning("🔴 Sin etiquetar")
    else:
        code = "—"
        for opt in config.LABEL_OPTIONS:
            if opt["display"] == new_label:
                code = opt["code"]
                break
        st.success(f"🟢 Etiqueta: **{new_label}** (código: {code})")
