import os
# CRITICAL FIX: MUST BE THE FIRST LINE
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import math
import config
import database as db
import utils
import i18n
from services import session_manager as sm
from services.whisper_service import load_whisper_model
from components.uploader import render_uploader
from components.gallery import render_gallery
from components.labeler import render_labeler
from components.recorder import render_recorder
from components.downloader import render_downloader
from components.image_protection import inject_image_protection
from services.auth_service import require_auth, render_logout_button

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    page_icon=config.APP_ICON,
)
# ── AUTHENTICATION GATE ───────────────────────────────────────────────────────
if not require_auth():
    st.stop()

# ── IMAGE PROTECTION (prevent download / right-click save) ───────────────────
inject_image_protection()

# Set UI language from config
i18n.ACTIVE_LANGUAGE = config.UI_LANGUAGE
# ── SESSION INITIALIZATION ──────────────────────────────────────────────────
sm.init_session()

# Check inactivity timeout
if sm.check_session_timeout(config.SESSION_TIMEOUT_MINUTES):
    if sm.has_undownloaded_data():
        summary = sm.get_session_data_summary()
        st.warning(
            f"⏰ Sesión expirada por inactividad ({config.SESSION_TIMEOUT_MINUTES} min). "
            f"Se eliminaron **{summary['total']}** imágenes, "
            f"**{summary['labeled']}** etiquetadas, "
            f"**{summary['with_audio']}** con audio. "
            "Descargue sus datos antes de que expire la sesión la próxima vez."
        )
    else:
        st.info("⏰ Sesión expirada por inactividad. Se inició una nueva sesión.")
    sm.clear_session()
    sm.init_session()

# ── DATABASE (metadata only — never images or audio) ────────────────────────
utils.setup_env()
try:
    active_db_type = db.init_db()
except Exception as e:
    st.error(f"Error crítico de base de datos: {e}")
    st.stop()

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")

    # Logout button (only visible if auth is active)
    render_logout_button()

    # Doctor name
    doctor = st.text_input(
        "👨‍⚕️ Nombre del Doctor",
        value=st.session_state.get("doctor_name", ""),
    )
    if doctor != st.session_state.get("doctor_name", ""):
        st.session_state.doctor_name = doctor

    st.divider()

    # Whisper language (select FIRST so models can be filtered)
    lang_keys = list(config.WHISPER_LANGUAGE_OPTIONS.keys())
    lang_labels = list(config.WHISPER_LANGUAGE_OPTIONS.values())
    selected_lang_display = st.selectbox("Idioma de dictado", lang_labels, index=0)
    selected_language = lang_keys[lang_labels.index(selected_lang_display)]

    # Whisper model — filtered by selected language
    # Models ending in ".en" → English only.  Others → multilingual.
    # "large" and "turbo" are multilingual and work for all languages.
    if selected_language == "en":
        available_models = [
            m for m in config.WHISPER_MODEL_OPTIONS
            if m.endswith(".en") or m in ("large", "turbo")
        ]
    else:
        available_models = [
            m for m in config.WHISPER_MODEL_OPTIONS if not m.endswith(".en")
        ]
    selected_model = st.selectbox(
        "Modelo Whisper",
        available_models,
        index=0,
    )

    st.divider()

    # ── Session progress ─────────────────────────────────────────────────────
    labeled, total = sm.get_labeling_progress()
    st.subheader("📊 Sesión Actual")
    st.caption(f"Base de datos: **{active_db_type}**")
    if total > 0:
        st.write(f"Imágenes cargadas: **{total}**")
        st.write(f"Etiquetadas: **{labeled}** / {total}")
        st.progress(labeled / total if total > 0 else 0)
    else:
        st.info("No hay imágenes en la sesión.")

    st.divider()

    # ── Annotation History (from DB) — Grouped by image ────────────────────────
    st.subheader("🗄️ Historial")
    search_input = st.text_input(
        "🔍 Buscar por imagen",
        value=st.session_state.get("history_search", ""),
    )
    if search_input != st.session_state.get("history_search", ""):
        st.session_state.history_search = search_input
        st.session_state.history_page = 1
        st.rerun()

    if "history_page" not in st.session_state:
        st.session_state.history_page = 1

    ITEMS_PER_PAGE = 5
    try:
        history_groups, total_items = db.get_history_grouped(
            st.session_state.get("history_search", ""),
            st.session_state.history_page,
            ITEMS_PER_PAGE,
        )
    except Exception as e:
        st.error(f"Error al obtener historial: {e}")
        history_groups, total_items = [], 0

    if not history_groups:
        st.caption("Sin registros.")
    else:
        for group in history_groups:
            fname = group["imageFilename"]
            annotations = group["annotations"]
            n_annotations = len(annotations)
            latest = annotations[0]
            latest_label = latest.get("label") or "—"

            # Badge showing number of labelings
            badge = f" ({n_annotations}x)" if n_annotations > 1 else ""

            with st.expander(f"📄 {fname}{badge} — {latest_label}"):
                for i, ann in enumerate(annotations):
                    ts = str(ann.get("createdAt", ""))[:16]
                    label = ann.get("label") or "—"
                    doctor = ann.get("doctorName") or "—"
                    text = ann.get("transcription", "") or ""
                    preview = (text[:60] + "…") if len(text) > 60 else text

                    if n_annotations > 1:
                        st.markdown(
                            f"**#{i + 1}** — `{ts}`"
                        )
                    st.write(f"**Etiqueta:** {label}")
                    st.write(f"**Doctor:** {doctor}")
                    if preview:
                        st.caption(f"📝 {preview}")
                    else:
                        st.caption("_Sin transcripción_")

                    if i < n_annotations - 1:
                        st.divider()

    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    if total_pages > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.session_state.history_page > 1:
                if st.button("◀️"):
                    st.session_state.history_page -= 1
                    st.rerun()
        with c2:
            st.markdown(
                f"<div style='text-align:center'>"
                f"{st.session_state.history_page} / {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with c3:
            if st.session_state.history_page < total_pages:
                if st.button("▶️"):
                    st.session_state.history_page += 1
                    st.rerun()

    st.divider()

    # ── End session ──────────────────────────────────────────────────────────
    if sm.has_undownloaded_data() and not st.session_state.get("session_downloaded", False):
        summary = sm.get_session_data_summary()
        remaining = sm.get_remaining_timeout_minutes(config.SESSION_TIMEOUT_MINUTES)
        st.warning(
            f"⚠️ Datos no descargados: **{summary['total']}** imágenes, "
            f"**{summary['labeled']}** etiquetadas, "
            f"**{summary['with_audio']}** con audio."
        )
        st.caption(f"⏱️ Timeout en ~{remaining:.0f} min")

    # Two-step confirmation to prevent accidental data loss
    if not st.session_state.get("confirm_end_session", False):
        if st.button(
            "🗑️ Finalizar Sesión",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.confirm_end_session = True
            st.rerun()
    else:
        st.error(
            "¿Está seguro? **Todos los datos se eliminarán permanentemente.**"
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✅ Sí, eliminar", type="primary", use_container_width=True):
                sm.clear_session()
                st.rerun()
        with cc2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirm_end_session = False
                st.rerun()

# ── LOAD WHISPER MODEL ───────────────────────────────────────────────────────
with st.spinner(f"Cargando modelo Whisper '{selected_model}'..."):
    model = load_whisper_model(selected_model)
# ── BROWSER CLOSE GUARD (beforeunload) ───────────────────────────────────
# Warn the user when they try to close/reload the tab with data in session.
if sm.has_undownloaded_data() and not st.session_state.get("session_downloaded", False):
    st.components.v1.html(
        """
        <script>
        window.addEventListener('beforeunload', function (e) {
            e.preventDefault();
            e.returnValue = '';
        });
        </script>
        """,
        height=0,
    )
# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.title(f"{config.APP_ICON} {config.APP_TITLE}")
st.caption(config.APP_SUBTITLE)

# ── IMAGE UPLOAD ─────────────────────────────────────────────────────────────
new_count = render_uploader()
if new_count > 0:
    st.rerun()

# ── WORKSPACE (requires at least one image) ──────────────────────────────────
if not st.session_state.image_order:
    st.info("📤 Suba imágenes médicas para comenzar el etiquetado.")
    st.stop()

# ── IMAGE GALLERY ────────────────────────────────────────────────────────────
st.divider()
gallery_clicked = render_gallery()
if gallery_clicked:
    st.rerun()
st.divider()

# Ensure a valid current image is selected
current_id = st.session_state.current_image_id
if current_id is None or current_id not in st.session_state.images:
    st.session_state.current_image_id = st.session_state.image_order[0]
    current_id = st.session_state.current_image_id

current_img = sm.get_current_image()
order = st.session_state.image_order
current_idx = order.index(current_id)

# ── Single-column layout ─────────────────────────────────────────────────────

# 1️⃣ LABELER — radio buttons at full width
render_labeler(current_id)

st.divider()

# 2️⃣ IMAGE — with navigation and delete
st.image(
    current_img["bytes"],
    caption=current_img["filename"],
    use_container_width=True,
)

c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    if st.button("⬅️ Anterior", disabled=(len(order) <= 1)):
        new_idx = (current_idx - 1) % len(order)
        st.session_state.current_image_id = order[new_idx]
        sm.update_activity()
        st.rerun()
with c2:
    st.markdown(
        f"<div style='text-align:center'><b>{current_img['filename']}</b>"
        f"<br>({current_idx + 1} de {len(order)})</div>",
        unsafe_allow_html=True,
    )
with c3:
    if st.button("Siguiente ➡️", disabled=(len(order) <= 1)):
        new_idx = (current_idx + 1) % len(order)
        st.session_state.current_image_id = order[new_idx]
        sm.update_activity()
        st.rerun()

if st.button("🗑️ Eliminar esta imagen", key="delete_img"):
    sm.remove_image(current_id)
    sm.update_activity()
    st.rerun()

st.divider()

# 3️⃣ RECORDER — dictation and transcription
render_recorder(current_id, model, selected_language)

st.divider()

# 4️⃣ DOWNLOAD (individual) + SESSION INFO — two columns
render_downloader(current_id)
