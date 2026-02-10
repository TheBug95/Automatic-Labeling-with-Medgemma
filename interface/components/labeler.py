"""OphthalmoCapture — Labeling Component

Provides:
  1. Categorical radio selector: Normal / Cataract / Bad quality / Needs dilation
  2. LOCS III dropdowns (only when "Cataract" is selected):
     - Nuclear Opalescence (NO) 0-6
     - Nuclear Color (NC)       0-6
     - Cortical Opacity (C)     0-5
  3. Auto-saves (upsert) to audit DB on every change.

Numeric values are stored for ML; only text labels are shown in the UI.
"""

import streamlit as st
import config
import database as db
from services import session_manager as sm


def _save_to_db(img: dict, image_id: str):
    """Persist current label + LOCS data to audit DB (non-blocking)."""
    try:
        db.save_or_update_annotation(
            image_filename=img["filename"],
            label=img["label"],
            transcription=img.get("transcription", ""),
            doctor_name=st.session_state.get("doctor_name", ""),
            session_id=st.session_state.get("session_id", ""),
            locs_data=img.get("locs_data", {}),
        )
    except Exception:
        pass


def _render_locs_dropdown(field: dict, image_id: str, current_locs: dict) -> int | None:
    """Render a single LOCS dropdown and return the selected numeric value."""
    field_id = field["field_id"]
    options = field["options"]
    display_labels = [opt["display"] for opt in options]

    # Determine current index from stored data
    stored_value = current_locs.get(field_id)
    if stored_value is not None:
        current_index = next(
            (i for i, opt in enumerate(options) if opt["value"] == stored_value),
            None,
        )
    else:
        current_index = None

    # Use index=None so nothing is pre-selected until doctor chooses
    selected_display = st.selectbox(
        field["label"],
        display_labels,
        index=current_index,
        key=f"locs_{field_id}_{image_id}",
        placeholder="Seleccionar…",
    )

    if selected_display is not None and selected_display in display_labels:
        idx = display_labels.index(selected_display)
        return options[idx]["value"]
    return None


def render_labeler(image_id: str):
    """Render the full labeling panel for the given image."""
    img = st.session_state.images.get(image_id)
    if img is None:
        return

    st.subheader("🏷️ Etiquetado")

    # ── 1. Categorical classification ────────────────────────────────────
    display_options = [opt["display"] for opt in config.LABEL_OPTIONS]
    current_label = img.get("label")

    if current_label is not None and current_label in display_options:
        current_index = display_options.index(current_label)
    else:
        current_index = None

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

    new_label = selected if selected in display_options else None

    # Detect categorical change
    label_changed = new_label is not None and new_label != current_label
    if label_changed:
        img["label"] = new_label
        img["labeled_by"] = st.session_state.get("doctor_name", "")
        # If switching away from Cataract, clear LOCS data
        if new_label != "Cataract":
            img["locs_data"] = {}
        sm.update_activity()
        _save_to_db(img, image_id)

    # ── 2. LOCS III Classification (only for "Cataract") ─────────────────
    effective_label = new_label or current_label
    if effective_label == "Cataract":
        st.markdown("---")
        st.markdown("**LOCS III Classification**")

        current_locs = img.get("locs_data", {})
        locs_changed = False

        with st.container(border=True):
            for field_def in config.LOCS_FIELDS:
                value = _render_locs_dropdown(field_def, image_id, current_locs)
                field_id = field_def["field_id"]
                if value is not None and value != current_locs.get(field_id):
                    current_locs[field_id] = value
                    locs_changed = True

        img["locs_data"] = current_locs

        if locs_changed:
            sm.update_activity()
            _save_to_db(img, image_id)

        # LOCS summary
        filled = sum(1 for f in config.LOCS_FIELDS if f["field_id"] in current_locs)
        total_fields = len(config.LOCS_FIELDS)
        if filled < total_fields:
            st.info(f"📋 LOCS: {filled}/{total_fields} campos completados")
        else:
            st.success(f"✅ LOCS: {filled}/{total_fields} campos completados")

    # ── 3. Visual feedback ───────────────────────────────────────────────
    if effective_label is None:
        st.warning("🔴 Sin etiquetar")
    else:
        st.success(f"🟢 Etiqueta: **{effective_label}**")
