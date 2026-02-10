"""OphthalmoCapture — Image Upload Component

Handles file upload, validation, and ingestion into the ephemeral session.
Uses @st.dialog modals to warn about:
  - Previously labeled images (from DB) — doctor chooses which to re-label.
  - Session duplicates — informational notice.
"""

import streamlit as st
import config
import database as db
from services import session_manager as sm
from utils import validate_image_bytes


def _reset_uploader():
    """Increment the uploader key counter to clear the file_uploader widget."""
    st.session_state._uploader_counter = st.session_state.get("_uploader_counter", 0) + 1


# ── Modal: previously labeled images ─────────────────────────────────────────
@st.dialog("⚠️ Imágenes ya etiquetadas", width="large", dismissible=False)
def _show_relabel_dialog():
    """Modal dialog asking the doctor which previously-labeled images to re-upload."""
    pending = st.session_state.get("_pending_upload_review")
    if not pending:
        st.rerun()
        return

    prev = pending["previously_labeled"]
    non_labeled_count = len(pending["files"]) - len(prev)

    st.markdown(
        f"**{len(prev)} imagen(es)** ya fueron etiquetadas anteriormente. "
        "Seleccione cuáles desea volver a etiquetar."
    )
    if non_labeled_count > 0:
        st.info(
            f"ℹ️ Las otras **{non_labeled_count}** imagen(es) nuevas se subirán automáticamente."
        )

    relabel_choices = {}
    for fname, records in prev.items():
        latest = records[0]
        label_info = latest.get("label", "—")
        doctor_info = latest.get("doctorName", "—")
        ts_info = str(latest.get("createdAt", ""))[:16]
        n_times = len(records)
        badge = f"({n_times} vez{'es' if n_times > 1 else ''})"

        relabel_choices[fname] = st.checkbox(
            f"**{fname}** — _{label_info}_ | {doctor_info} | {ts_info} {badge}",
            value=True,
            key=f"_dlg_relabel_{fname}",
        )

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Aceptar y subir", type="primary", use_container_width=True):
            _process_pending(relabel_choices)
    with col_b:
        if st.button("❌ Cancelar etiquetadas", use_container_width=True):
            _cancel_pending()


def _process_pending(relabel_choices: dict[str, bool]):
    """Ingest accepted files from the pending review."""
    pending = st.session_state.pop("_pending_upload_review", None)
    if not pending:
        st.rerun()
        return

    prev = pending["previously_labeled"]
    files_dict = pending["files"]
    existing_filenames = {
        img["filename"] for img in st.session_state.images.values()
    }

    if "_processed_uploads" not in st.session_state:
        st.session_state._processed_uploads = set()

    added = 0
    for fname, raw_bytes in files_dict.items():
        # If it was previously labeled and doctor unchecked it → skip
        if fname in prev and not relabel_choices.get(fname, True):
            continue
        if fname not in existing_filenames:
            sm.add_image(fname, raw_bytes)
            st.session_state._processed_uploads.add(fname)
            st.session_state.session_downloaded = False
            added += 1

    _reset_uploader()
    if added > 0 and st.session_state.current_image_id is None:
        st.session_state.current_image_id = st.session_state.image_order[0]
    st.rerun()


def _cancel_pending():
    """Cancel previously-labeled images but still ingest new (non-labeled) ones."""
    pending = st.session_state.pop("_pending_upload_review", None)
    if pending:
        prev = pending["previously_labeled"]
        files_dict = pending["files"]
        existing_filenames = {
            img["filename"] for img in st.session_state.images.values()
        }
        if "_processed_uploads" not in st.session_state:
            st.session_state._processed_uploads = set()

        added = 0
        for fname, raw_bytes in files_dict.items():
            # Skip previously labeled — doctor chose to cancel them
            if fname in prev:
                continue
            if fname not in existing_filenames:
                sm.add_image(fname, raw_bytes)
                st.session_state._processed_uploads.add(fname)
                st.session_state.session_downloaded = False
                added += 1

        if added > 0 and st.session_state.current_image_id is None:
            st.session_state.current_image_id = st.session_state.image_order[0]

    _reset_uploader()
    st.rerun()


# ── Modal: session duplicates (informational) ────────────────────────────────
@st.dialog("ℹ️ Imágenes duplicadas en sesión", dismissible=False)
def _show_duplicates_dialog():
    """Informational modal listing images already present in the current session."""
    dup_names = st.session_state.get("_session_duplicates", [])
    if not dup_names:
        st.rerun()
        return

    st.markdown(
        "Las siguientes imágenes **ya se encuentran en la sesión actual** "
        "y no se volverán a subir:"
    )
    for fname in dup_names:
        st.markdown(f"- `{fname}`")

    if st.button("Aceptar", use_container_width=True):
        st.session_state.pop("_session_duplicates", None)
        st.rerun()


# ── Main uploader ────────────────────────────────────────────────────────────
def render_uploader():
    """Render the file uploader and process new uploads.

    Returns the number of newly added images (0 if none).
    """
    counter = st.session_state.get("_uploader_counter", 0)

    uploaded_files = st.file_uploader(
        "📤 Subir imágenes médicas",
        type=config.ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
        help=f"Formatos aceptados: {', '.join(config.ALLOWED_EXTENSIONS)}. "
             f"Máx. {config.MAX_UPLOAD_SIZE_MB} MB por archivo.",
        key=f"uploader_{counter}",
    )

    # ── Show pending dialogs (survive reruns) ────────────────────────────
    if "_pending_upload_review" in st.session_state:
        _show_relabel_dialog()
        return 0

    if "_session_duplicates" in st.session_state:
        _show_duplicates_dialog()
        return 0

    if not uploaded_files:
        return 0

    if "_processed_uploads" not in st.session_state:
        st.session_state._processed_uploads = set()

    existing_filenames = {
        img["filename"] for img in st.session_state.images.values()
    }

    # ── Classify files ───────────────────────────────────────────────────
    new_files = []
    skipped_invalid = 0
    session_duplicates = []

    for uf in uploaded_files:
        # Already in the current session
        if uf.name in existing_filenames:
            if uf.name not in st.session_state._processed_uploads:
                session_duplicates.append(uf.name)
                st.session_state._processed_uploads.add(uf.name)
            continue

        # Already ingested via this uploader cycle
        if uf.name in st.session_state._processed_uploads:
            continue

        raw_bytes = uf.getvalue()
        if not validate_image_bytes(raw_bytes):
            skipped_invalid += 1
            continue

        new_files.append((uf.name, raw_bytes))

    # ── Check DB for previously labeled images ───────────────────────────
    if new_files:
        new_filenames = [name for name, _ in new_files]
        previously_labeled = db.get_previously_labeled_filenames(new_filenames)

        if previously_labeled:
            # Store all files (new + previously labeled) for review
            st.session_state["_pending_upload_review"] = {
                "files": {name: raw for name, raw in new_files},
                "previously_labeled": previously_labeled,
            }
            # Also show session duplicate dialog afterward if needed
            if session_duplicates:
                st.session_state["_session_duplicates"] = session_duplicates
            st.rerun()
            return 0

    # ── Ingest files that need no review ─────────────────────────────────
    new_count = 0
    for name, raw_bytes in new_files:
        if name in existing_filenames:
            continue
        if name in st.session_state._processed_uploads:
            continue

        sm.add_image(name, raw_bytes)
        existing_filenames.add(name)
        st.session_state._processed_uploads.add(name)
        st.session_state.session_downloaded = False
        new_count += 1

    if skipped_invalid > 0:
        st.warning(
            f"⚠️ {skipped_invalid} archivo(s) no son imágenes válidas y fueron ignorados."
        )

    if new_count > 0:
        _reset_uploader()
        if st.session_state.current_image_id is None:
            st.session_state.current_image_id = st.session_state.image_order[0]

    # ── Show session duplicate info dialog if any ────────────────────────
    if session_duplicates:
        st.session_state["_session_duplicates"] = session_duplicates
        st.rerun()

    return new_count
