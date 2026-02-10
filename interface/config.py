"""OphthalmoCapture — Configuration Constants."""

# ── Categorical Label Options ────────────────────────────────────────────────
# Primary classification (radio buttons).
LABEL_OPTIONS = [
    {"key": "normal",          "display": "Normal",          "code": 0},
    {"key": "cataract",        "display": "Cataract",        "code": 1},
    {"key": "bad_quality",     "display": "Bad quality",     "code": 2},
    {"key": "needs_dilation",  "display": "Needs dilation",  "code": 3},
]

# ── LOCS III Classification (shown only when label == "Cataract") ────────────
# Values are integer bins mapped from LOCS III continuous scales:
#   NO/NC (0.1–6.9) → 0–6
#   C     (0.1–5.9) → 0–5
# We store the numeric value for ML and display only the text label.

LOCS_NUCLEAR_OPALESCENCE = {
    "field_id": "nuclear_opalescence",
    "label": "Nuclear Cataract – Opalescence (NO)",
    "options": [
        {"value": 0, "display": "None / Clear"},
        {"value": 1, "display": "Very mild"},
        {"value": 2, "display": "Mild"},
        {"value": 3, "display": "Mild–moderate"},
        {"value": 4, "display": "Moderate"},
        {"value": 5, "display": "Moderate–severe"},
        {"value": 6, "display": "Severe"},
    ],
}

LOCS_NUCLEAR_COLOR = {
    "field_id": "nuclear_color",
    "label": "Nuclear Cataract – Color (NC)",
    "options": [
        {"value": 0, "display": "None / Clear"},
        {"value": 1, "display": "Very mild yellowing"},
        {"value": 2, "display": "Mild yellowing"},
        {"value": 3, "display": "Moderate yellow"},
        {"value": 4, "display": "Yellow–brown"},
        {"value": 5, "display": "Brown"},
        {"value": 6, "display": "Dark brown"},
    ],
}

LOCS_CORTICAL = {
    "field_id": "cortical_opacity",
    "label": "Cortical Cataract (C)",
    "options": [
        {"value": 0, "display": "None"},
        {"value": 1, "display": "Peripheral spokes only"},
        {"value": 2, "display": "Mild peripheral involvement"},
        {"value": 3, "display": "Moderate spokes approaching center"},
        {"value": 4, "display": "Central involvement"},
        {"value": 5, "display": "Severe / dense central spokes"},
    ],
}

# Convenience list of all LOCS dropdowns
LOCS_FIELDS = [LOCS_NUCLEAR_OPALESCENCE, LOCS_NUCLEAR_COLOR, LOCS_CORTICAL]

# ── Session Settings ─────────────────────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = 30

# ── Upload Settings ──────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "tif"]
MAX_UPLOAD_SIZE_MB = 50

# ── Whisper Settings ─────────────────────────────────────────────────────────
WHISPER_MODEL_OPTIONS = [
    "tiny", "tiny.en", "base", "base.en",
    "small", "small.en", "medium", "medium.en",
    "large", "turbo",
]
DEFAULT_WHISPER_MODEL_INDEX = 1

WHISPER_LANGUAGE_OPTIONS = {
    "es": "Español",
    "en": "English",
}
DEFAULT_WHISPER_LANGUAGE = "es"

# ── App Metadata ─────────────────────────────────────────────────────────────
APP_TITLE = "OphthalmoCapture"
APP_ICON = "👁️"
APP_SUBTITLE = "Sistema de Etiquetado Médico Oftalmológico"

# ── UI Language ──────────────────────────────────────────────────────────────
# Language is now managed via st.session_state["ui_language"] and i18n module.
# Supported: "es" (Español), "en" (English).
