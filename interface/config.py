"""OphthalmoCapture — Configuration Constants."""

# ── Label Options ────────────────────────────────────────────────────────────
# Designed as a configurable list for easy extension (e.g. glaucoma, DR, AMD).
LABEL_OPTIONS = [
    {"key": "catarata",    "display": "Catarata",    "code": 1},
    {"key": "no_catarata", "display": "No Catarata", "code": 0},
]

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
# "es" = Español, "en" = English
UI_LANGUAGE = "es"
