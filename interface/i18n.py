"""OphthalmoCapture — Internationalization (i18n)

Centralized UI strings with session-state-based language selection.
All components call t(key) to get translated strings.
"""

import streamlit as st

SUPPORTED_LANGUAGES = {"es": "Español", "en": "English"}
DEFAULT_LANGUAGE = "es"


def _get_lang() -> str:
    """Return the active UI language code from session state."""
    return st.session_state.get("ui_language", DEFAULT_LANGUAGE)


_STRINGS = {
    "es": {
        # App
        "app_subtitle": "Sistema de Etiquetado Médico Oftalmológico",
        # Sidebar
        "settings": "⚙️ Configuración",
        "doctor_name": "👨‍⚕️ Nombre del Doctor",
        "whisper_model": "Modelo Whisper",
        "dictation_language": "Idioma de dictado",
        "current_session": "📊 Sesión Actual",
        "db_type": "Base de datos",
        "images_loaded": "Imágenes cargadas",
        "labeled_count": "Etiquetadas",
        "no_images": "No hay imágenes en la sesión.",
        "history": "🗄️ Historial",
        "search_image": "🔍 Buscar por imagen",
        "no_records": "Sin registros.",
        "label_header": "Etiqueta",
        "doctor_header": "Doctor",
        "no_transcription": "Sin transcripción",
        "end_session": "� Cerrar sesión",
        "undownloaded_warning": "⚠️ Datos no descargados",
        "timeout_in": "⏱️ Timeout en",
        "confirm_delete": "¿Está seguro? **Se cerrará la sesión y todos los datos se eliminarán permanentemente.**",
        "yes_delete": "✅ Sí, cerrar sesión",
        "cancel": "❌ Cancelar",
        "logout": "🚪 Cerrar sesión",
        # Upload
        "upload_images": "📤 Subir imágenes médicas",
        "upload_help_formats": "Formatos aceptados",
        "upload_help_max": "Máx.",
        "invalid_files": "archivo(s) no son imágenes válidas y fueron ignorados.",
        "duplicate_files": "archivo(s) duplicados fueron omitidos.",
        "upload_prompt": "📤 Suba imágenes médicas para comenzar el etiquetado.",
        # Gallery
        "progress": "Progreso",
        "labeled_suffix": "etiquetadas",
        "page": "Página",
        # Labeler
        "labeling": "🏷️ Etiquetado",
        "select_label": "— Seleccione una etiqueta —",
        "classification": "Clasificación de la imagen",
        "unlabeled": "🔴 Sin etiquetar",
        "label_set": "🟢 Etiqueta",
        "code": "código",
        "save_label": "💾 Guardar etiqueta en historial",
        "select_before_save": "Seleccione una etiqueta antes de guardar.",
        "label_saved": "✅ Etiqueta guardada en la base de datos.",
        "save_error": "Error al guardar",
        # Recorder
        "dictation": "🎙️ Dictado y Transcripción",
        "record_audio": "Grabar audio",
        "transcribing": "Transcribiendo audio…",
        "transcription_editable": "Transcripción (editable)",
        "transcription_placeholder": "Grabe un audio o escriba la transcripción manualmente…",
        "segments_timestamps": "🕐 Segmentos con timestamps",
        "restore_original": "🔄 Restaurar original",
        "clear_text": "🗑️ Limpiar texto",
        "words": "palabras",
        "manually_modified": "✏️ _modificada manualmente_",
        "no_transcription_yet": "Sin transcripción aún.",
        # Downloader
        "download": "📥 Descarga",
        "current_image": "Imagen actual",
        "label_to_enable": "Etiquete la imagen para habilitar la descarga individual.",
        "download_label": "⬇️ Descargar etiquetado",
        "full_session": "Toda la sesión",
        "images_metric": "Imágenes",
        "with_audio": "Con audio",
        "labeled_metric": "Etiquetadas",
        "with_transcription": "Con transcripción",
        "unlabeled_warning": "imagen(es) sin etiquetar. Se incluirán en la descarga pero sin etiqueta.",
        "no_images_download": "No hay imágenes para descargar.",
        "download_all": "⬇️ Descargar todo el etiquetado (ZIP)",
        "ml_formats": "Formatos para ML",
        "hf_csv": "📊 CSV (HuggingFace)",
        "jsonl_finetune": "📄 JSONL (Fine-tuning)",
        # Nav
        "previous": "⬅️ Anterior",
        "next": "Siguiente ➡️",
        "delete_image": "🗑️ Eliminar esta imagen",
        # Timeout
        "session_expired_data": "⏰ Sesión expirada por inactividad",
        "session_expired_clean": "⏰ Sesión expirada por inactividad. Se inició una nueva sesión.",
        "download_before_expire": "Descargue sus datos antes de que expire la sesión la próxima vez.",
        # Auth
        "login_prompt": "👨‍⚕️ Inicie sesión para acceder al sistema de etiquetado.",
        "login_error": "❌ Usuario o contraseña incorrectos.",
        # i18n
        "ui_language": "🌐 Idioma / Language",
        "loading_whisper": "Cargando modelo Whisper '{model}'...",
        # Session expiry with placeholders
        "session_expired": "⏰ Sesión expirada por inactividad ({minutes} min). Se eliminaron **{total}** imágenes, **{labeled}** etiquetadas, **{with_audio}** con audio. Descargue sus datos antes de que expire la sesión la próxima vez.",
        "db_error": "Error crítico de base de datos: {error}",
        "history_error": "Error al obtener historial: {error}",
        # Labeler
        "select_label_hint": "⬇️ Seleccione una etiqueta para esta imagen",
        "locs_title": "**Clasificación LOCS III**",
        "locs_placeholder": "Seleccionar…",
        "locs_progress": "📋 LOCS: {filled}/{total} campos completados",
        "locs_complete": "✅ LOCS: {filled}/{total} campos completados",
        # Recorder
        "re_record": "🎤 Volver a grabar",
        "word_count": "{count} palabras",
        # Downloader
        "single_download": "📥 Descarga individual",
        "session_info": "📊 Información de sesión",
        "bulk_download": "📦 Descargar todo el etiquetado",
        "download_all_zip": "⬇️ Descargar todo el etiquetado (ZIP)",
        "download_file": "⬇️ Descargar — {filename}",
        "incomplete_fields_msg": "La imagen **{filename}** tiene campos sin completar:",
        "missing_categorical": "Etiqueta categórica",
        "missing_locs": "LOCS III – {field}",
        "missing_voice": "Etiquetado por voz",
        "download_anyway": "⬇️ Descargar igualmente",
        "go_back_finish": "🔙 Regresar y terminar",
        "bulk_incomplete_msg": "**{count} imagen(es)** tienen etiquetado incompleto:",
        "col_image": "Imagen",
        "col_categorical": "Categórica",
        "col_locs": "LOCS III",
        "col_voice": "Voz",
        "locs_not_required": "No Necesario",
        "image_counter": "{current} de {total}",
        # Gallery
        "gallery_prev": "◀ Ant.",
        "gallery_next": "Sig. ▶",
        # Uploader
        "relabel_dialog_msg": "**{count} imagen(es)** ya fueron etiquetadas anteriormente. Seleccione cuáles desea volver a etiquetar.",
        "relabel_new_info": "ℹ️ Las otras **{count}** imagen(es) nuevas se subirán automáticamente.",
        "accept_upload": "✅ Aceptar y subir",
        "cancel_labeled": "❌ Cancelar etiquetadas",
        "duplicates_dialog_msg": "Las siguientes imágenes **ya se encuentran en la sesión actual** y no se volverán a subir:",
        "accept": "Aceptar",
        # Dialog titles
        "dlg_single_incomplete": "⚠️ Etiquetado incompleto",
        "dlg_bulk_incomplete": "⚠️ Imágenes con etiquetado incompleto",
        "dlg_relabel": "⚠️ Imágenes ya etiquetadas",
        "dlg_duplicates": "ℹ️ Imágenes duplicadas en sesión",
        # Uploader badge
        "times_badge": "{n} vez",
        "times_badge_plural": "{n} veces",
    },
    "en": {
        "app_subtitle": "Ophthalmological Medical Labeling System",
        "settings": "⚙️ Settings",
        "doctor_name": "👨‍⚕️ Doctor Name",
        "whisper_model": "Whisper Model",
        "dictation_language": "Dictation Language",
        "current_session": "📊 Current Session",
        "db_type": "Database",
        "images_loaded": "Images loaded",
        "labeled_count": "Labeled",
        "no_images": "No images in session.",
        "history": "🗄️ History",
        "search_image": "🔍 Search by image",
        "no_records": "No records.",
        "label_header": "Label",
        "doctor_header": "Doctor",
        "no_transcription": "No transcription",
        "end_session": "� Log out",
        "undownloaded_warning": "⚠️ Undownloaded data",
        "timeout_in": "⏱️ Timeout in",
        "confirm_delete": "Are you sure? **The session will be closed and all data permanently deleted.**",
        "yes_delete": "✅ Yes, log out",
        "cancel": "❌ Cancel",
        "logout": "🚪 Log out",
        "upload_images": "📤 Upload medical images",
        "upload_help_formats": "Accepted formats",
        "upload_help_max": "Max.",
        "invalid_files": "file(s) are not valid images and were ignored.",
        "duplicate_files": "duplicate file(s) were skipped.",
        "upload_prompt": "📤 Upload medical images to start labeling.",
        "progress": "Progress",
        "labeled_suffix": "labeled",
        "page": "Page",
        "labeling": "🏷️ Labeling",
        "select_label": "— Select a label —",
        "classification": "Image classification",
        "unlabeled": "🔴 Unlabeled",
        "label_set": "🟢 Label",
        "code": "code",
        "save_label": "💾 Save label to history",
        "select_before_save": "Select a label before saving.",
        "label_saved": "✅ Label saved to database.",
        "save_error": "Save error",
        "dictation": "🎙️ Dictation & Transcription",
        "record_audio": "Record audio",
        "transcribing": "Transcribing audio…",
        "transcription_editable": "Transcription (editable)",
        "transcription_placeholder": "Record audio or type the transcription manually…",
        "segments_timestamps": "🕐 Segments with timestamps",
        "restore_original": "🔄 Restore original",
        "clear_text": "🗑️ Clear text",
        "words": "words",
        "manually_modified": "✏️ _manually modified_",
        "no_transcription_yet": "No transcription yet.",
        "download": "📥 Download",
        "current_image": "Current image",
        "label_to_enable": "Label the image to enable individual download.",
        "download_label": "⬇️ Download labeling",
        "full_session": "Full session",
        "images_metric": "Images",
        "with_audio": "With audio",
        "labeled_metric": "Labeled",
        "with_transcription": "With transcription",
        "unlabeled_warning": "unlabeled image(s). They will be included in the download without a label.",
        "no_images_download": "No images to download.",
        "download_all": "⬇️ Download all labeling (ZIP)",
        "ml_formats": "ML Formats",
        "hf_csv": "📊 CSV (HuggingFace)",
        "jsonl_finetune": "📄 JSONL (Fine-tuning)",
        "previous": "⬅️ Previous",
        "next": "Next ➡️",
        "delete_image": "🗑️ Delete this image",
        "session_expired_data": "⏰ Session expired due to inactivity",
        "session_expired_clean": "⏰ Session expired. A new session has started.",
        "download_before_expire": "Download your data before the session expires next time.",
        "login_prompt": "👨‍⚕️ Log in to access the labeling system.",
        "login_error": "❌ Wrong username or password.",
        "ui_language": "🌐 Language / Idioma",
        "loading_whisper": "Loading Whisper model '{model}'...",
        "session_expired": "⏰ Session expired due to inactivity ({minutes} min). Removed **{total}** images, **{labeled}** labeled, **{with_audio}** with audio. Download your data before the session expires next time.",
        "db_error": "Critical database error: {error}",
        "history_error": "Error fetching history: {error}",
        "select_label_hint": "⬇️ Select a label for this image",
        "locs_title": "**LOCS III Classification**",
        "locs_placeholder": "Select…",
        "locs_progress": "📋 LOCS: {filled}/{total} fields completed",
        "locs_complete": "✅ LOCS: {filled}/{total} fields completed",
        "re_record": "🎤 Re-record",
        "word_count": "{count} words",
        "single_download": "📥 Individual Download",
        "session_info": "📊 Session Information",
        "bulk_download": "📦 Download All Labeling",
        "download_all_zip": "⬇️ Download all labeling (ZIP)",
        "download_file": "⬇️ Download — {filename}",
        "incomplete_fields_msg": "Image **{filename}** has incomplete fields:",
        "missing_categorical": "Categorical label",
        "missing_locs": "LOCS III – {field}",
        "missing_voice": "Voice labeling",
        "download_anyway": "⬇️ Download anyway",
        "go_back_finish": "🔙 Go back and finish",
        "bulk_incomplete_msg": "**{count} image(s)** have incomplete labeling:",
        "col_image": "Image",
        "col_categorical": "Categorical",
        "col_locs": "LOCS III",
        "col_voice": "Voice",
        "locs_not_required": "Not Required",
        "image_counter": "{current} of {total}",
        "gallery_prev": "◀ Prev",
        "gallery_next": "Next ▶",
        "relabel_dialog_msg": "**{count} image(s)** were previously labeled. Select which ones to re-label.",
        "relabel_new_info": "ℹ️ The other **{count}** new image(s) will be uploaded automatically.",
        "accept_upload": "✅ Accept and upload",
        "cancel_labeled": "❌ Cancel labeled",
        "duplicates_dialog_msg": "The following images **are already in the current session** and will not be re-uploaded:",
        "accept": "Accept",
        "dlg_single_incomplete": "⚠️ Incomplete labeling",
        "dlg_bulk_incomplete": "⚠️ Images with incomplete labeling",
        "dlg_relabel": "⚠️ Previously labeled images",
        "dlg_duplicates": "ℹ️ Duplicate images in session",
        "times_badge": "{n} time",
        "times_badge_plural": "{n} times",
    },
}


def t(key: str, **kwargs) -> str:
    """Return the translated string for *key*, with optional format kwargs."""
    lang = _get_lang()
    text = _STRINGS.get(lang, _STRINGS["es"]).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


# ── Label display translations ───────────────────────────────────────────────
# Labels are stored in English (config.LABEL_OPTIONS["display"]).
# These mappings translate for UI display only.

_LABEL_DISPLAY = {
    "es": {
        "Normal": "Normal",
        "Cataract": "Catarata",
        "Bad quality": "Mala calidad",
        "Needs dilation": "Necesita dilatación",
    },
    "en": {
        "Normal": "Normal",
        "Cataract": "Cataract",
        "Bad quality": "Bad quality",
        "Needs dilation": "Needs dilation",
    },
}


def label_display(english_name: str) -> str:
    """Translate a label's English display name to the active UI language."""
    lang = _get_lang()
    return _LABEL_DISPLAY.get(lang, _LABEL_DISPLAY["en"]).get(english_name, english_name)


def label_from_display(translated_name: str) -> str | None:
    """Reverse-map a translated label back to its English storage name."""
    lang = _get_lang()
    mapping = _LABEL_DISPLAY.get(lang, _LABEL_DISPLAY["en"])
    reverse = {v: k for k, v in mapping.items()}
    return reverse.get(translated_name)


# ── LOCS display translations ────────────────────────────────────────────────

_LOCS_DISPLAY = {
    "es": {
        "Nuclear Cataract \u2013 Opalescence (NO)": "Catarata Nuclear \u2013 Opalescencia (NO)",
        "Nuclear Cataract \u2013 Color (NC)": "Catarata Nuclear \u2013 Color (NC)",
        "Cortical Cataract (C)": "Catarata Cortical (C)",
        "None / Clear": "Ninguna / Transparente",
        "Very mild": "Muy leve",
        "Mild": "Leve",
        "Mild\u2013moderate": "Leve\u2013moderada",
        "Moderate": "Moderada",
        "Moderate\u2013severe": "Moderada\u2013severa",
        "Severe": "Severa",
        "Very mild yellowing": "Amarillamiento muy leve",
        "Mild yellowing": "Amarillamiento leve",
        "Moderate yellow": "Amarillo moderado",
        "Yellow\u2013brown": "Amarillo\u2013marrón",
        "Brown": "Marrón",
        "Dark brown": "Marrón oscuro",
        "None": "Ninguna",
        "Peripheral spokes only": "Solo radios periféricos",
        "Mild peripheral involvement": "Compromiso periférico leve",
        "Moderate spokes approaching center": "Radios moderados acercándose al centro",
        "Central involvement": "Compromiso central",
        "Severe / dense central spokes": "Severa / radios centrales densos",
    },
    "en": {},
}


def locs_display(english_text: str) -> str:
    """Translate a LOCS field label or option to the active UI language."""
    lang = _get_lang()
    if lang == "en":
        return english_text
    return _LOCS_DISPLAY.get(lang, {}).get(english_text, english_text)
