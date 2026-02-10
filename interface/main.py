import os
# CRITICAL FIX: MUST BE THE FIRST LINE
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import math
import config
import database as db
import utils
from i18n import t, label_display, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from services import session_manager as sm
from services.whisper_service import load_whisper_model
from components.uploader import render_uploader
from components.gallery import render_gallery
from components.labeler import render_labeler
from components.recorder import render_recorder
from components.downloader import render_downloader
from components.image_protection import inject_image_protection
from services.auth_service import require_auth, do_logout

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    page_icon=config.APP_ICON,
)

# ── FIX: Prevent horizontal layout shift from scrollbar appearing/disappearing
# HF Spaces renders Streamlit inside an iframe. The scroll container is NOT
# <html> but internal Streamlit elements. We target every possible scroll
# container and use scrollbar-gutter:stable (modern) + overflow-y:scroll (fallback).
st.markdown("""
<style>
    /* Modern solution: reserves space for scrollbar even when not needed */
    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main,
    section[data-testid="stMain"],
    [data-testid="stVerticalBlockBorderWrapper"],
    .stMainBlockContainer {
        scrollbar-gutter: stable !important;
    }

    /* Fallback: force scrollbar always visible on all potential containers */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main {
        overflow-y: scroll !important;
    }

    /* Prevent any horizontal overflow that could cause shifts */
    [data-testid="stMainBlockContainer"],
    [data-testid="stVerticalBlock"] {
        overflow-x: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# ── IMAGE PROTECTION (prevent download / right-click save) ───────────────────
inject_image_protection()

# ── AUTHENTICATION GATE ───────────────────────────────────────────────────────
if not require_auth():
    st.stop()

# ── UI LANGUAGE (initialize before anything renders) ─────────────────────────
if "ui_language" not in st.session_state:
    st.session_state.ui_language = DEFAULT_LANGUAGE

# ── SESSION INITIALIZATION ──────────────────────────────────────────────────
sm.init_session()

# Check inactivity timeout
if sm.check_session_timeout(config.SESSION_TIMEOUT_MINUTES):
    if sm.has_undownloaded_data():
        summary = sm.get_session_data_summary()
        st.warning(t("session_expired",
                     minutes=config.SESSION_TIMEOUT_MINUTES,
                     total=summary['total'],
                     labeled=summary['labeled'],
                     with_audio=summary['with_audio']))
    else:
        st.info(t("session_expired_clean"))
    sm.clear_session()
    sm.init_session()

# ── DATABASE (metadata only — never images or audio) ────────────────────────
utils.setup_env()
try:
    active_db_type = db.init_db()
except Exception as e:
    st.error(t("db_error", error=str(e)))
    st.stop()

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title(t("settings"))

    # Language selector
    lang_codes = list(SUPPORTED_LANGUAGES.keys())
    lang_names = list(SUPPORTED_LANGUAGES.values())
    current_lang_idx = lang_codes.index(st.session_state.ui_language) if st.session_state.ui_language in lang_codes else 0
    selected_ui_lang = st.selectbox(
        t("ui_language"),
        lang_names,
        index=current_lang_idx,
        key="_ui_language_selector",
    )
    new_lang_code = lang_codes[lang_names.index(selected_ui_lang)]
    if new_lang_code != st.session_state.ui_language:
        st.session_state.ui_language = new_lang_code
        st.rerun()

    st.divider()

    # Doctor name
    doctor = st.text_input(
        t("doctor_name"),
        value=st.session_state.get("doctor_name", ""),
    )
    if doctor != st.session_state.get("doctor_name", ""):
        st.session_state.doctor_name = doctor

    st.divider()

    # Whisper language (select FIRST so models can be filtered)
    lang_keys = list(config.WHISPER_LANGUAGE_OPTIONS.keys())
    lang_labels = list(config.WHISPER_LANGUAGE_OPTIONS.values())
    selected_lang_display = st.selectbox(t("dictation_language"), lang_labels, index=0)
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
        t("whisper_model"),
        available_models,
        index=0,
    )

    st.divider()

    # ── Session progress ─────────────────────────────────────────────────────
    labeled, total = sm.get_labeling_progress()
    st.subheader(t("current_session"))
    st.caption(f"{t('db_type')}: **{active_db_type}**")
    if total > 0:
        st.write(f"{t('images_loaded')}: **{total}**")
        st.write(f"{t('labeled_count')}: **{labeled}** / {total}")
        st.progress(labeled / total if total > 0 else 0)
    else:
        st.info(t("no_images"))

    st.divider()

    # ── Annotation History (from DB) — Grouped by image ────────────────────────
    st.subheader(t("history"))
    search_input = st.text_input(
        t("search_image"),
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
        st.error(t("history_error", error=str(e)))
        history_groups, total_items = [], 0

    if not history_groups:
        st.caption(t("no_records"))
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
                    st.write(f"**{t('label_header')}:** {label_display(label) if label != '—' else label}")
                    st.write(f"**{t('doctor_header')}:** {doctor}")
                    if preview:
                        st.caption(f"📝 {preview}")
                    else:
                        st.caption(f"_{t('no_transcription')}_")

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
            f"{t('undownloaded_warning')}: **{summary['total']}** {t('images_metric')}, "
            f"**{summary['labeled']}** {t('labeled_count')}, "
            f"**{summary['with_audio']}** {t('with_audio')}."
        )
        st.caption(f"{t('timeout_in')} ~{remaining:.0f} min")

    # Two-step confirmation to prevent accidental data loss
    if not st.session_state.get("confirm_end_session", False):
        if st.button(
            t("logout"),
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.confirm_end_session = True
            st.rerun()
    else:
        st.error(t("confirm_delete"))
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button(t("yes_delete"), type="primary", use_container_width=True):
                sm.clear_session()
                do_logout()
                st.rerun()
        with cc2:
            if st.button(t("cancel"), use_container_width=True):
                st.session_state.confirm_end_session = False
                st.rerun()

# ── LOAD WHISPER MODEL ───────────────────────────────────────────────────────
with st.spinner(t("loading_whisper", model=selected_model)):
    model = load_whisper_model(selected_model)

# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.title(f"{config.APP_ICON} {config.APP_TITLE}")
st.caption(t("app_subtitle"))

# ── IMAGE UPLOAD ─────────────────────────────────────────────────────────────
new_count = render_uploader()
if new_count > 0:
    st.rerun()

# ── WORKSPACE (requires at least one image) ──────────────────────────────────
if not st.session_state.image_order:
    st.info(t("upload_prompt"))
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

# 2️⃣ IMAGE — with navigation and delete (max 500px to fit on screen)
_img_col1, _img_col2, _img_col3 = st.columns([1, 3, 1])
with _img_col2:
    st.image(
        current_img["bytes"],
        caption=current_img["filename"],
        use_container_width=True,
    )

c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    if st.button(t("previous"), disabled=(len(order) <= 1)):
        new_idx = (current_idx - 1) % len(order)
        st.session_state.current_image_id = order[new_idx]
        sm.update_activity()
        st.rerun()
with c2:
    st.markdown(
        f"<div style='text-align:center'><b>{current_img['filename']}</b>"
        f"<br>({t('image_counter', current=current_idx + 1, total=len(order))})</div>",
        unsafe_allow_html=True,
    )
with c3:
    if st.button(t("next"), disabled=(len(order) <= 1)):
        new_idx = (current_idx + 1) % len(order)
        st.session_state.current_image_id = order[new_idx]
        sm.update_activity()
        st.rerun()

if st.button(t("delete_image"), key="delete_img"):
    sm.remove_image(current_id)
    sm.update_activity()
    st.rerun()

st.divider()

# 3️⃣ RECORDER — dictation and transcription
render_recorder(current_id, model, selected_language)

st.divider()

# 4️⃣ DOWNLOAD (individual) + SESSION INFO — two columns
render_downloader(current_id)
