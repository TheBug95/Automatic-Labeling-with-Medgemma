"""OphthalmoCapture — Basic Authentication Service

Provides a simple login gate using streamlit-authenticator.
Doctors must authenticate before accessing the labeling interface.
Their name is automatically set in the session for audit trails.

If streamlit-authenticator is not installed, authentication is skipped
and the app works in "anonymous" mode.
"""

import streamlit as st

try:
    import streamlit_authenticator as stauth
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


# ── Default credentials ──────────────────────────────────────────────────────
# In production, load these from a secure YAML/env.  For now, hardcoded demo.
DEFAULT_CREDENTIALS = {
    "usernames": {
        "admin": {
            "name": "Administrador",
            "password": "$2b$12$dcvvIg0q/2hZ1pO9gBKqY./LfujFHvoJUvPDLx1qhLS0LtD2kzJoq",
            # plain: "admin123"  — generate new hashes with stauth.Hasher
        },
        "doctor1": {
            "name": "Dr. García",
            "password": "$2b$12$dcvvIg0q/2hZ1pO9gBKqY./LfujFHvoJUvPDLx1qhLS0LtD2kzJoq",
            # plain: "admin123"
        },
        "doctor2": {
            "name": "Dra. López",
            "password": "$2b$12$dcvvIg0q/2hZ1pO9gBKqY./LfujFHvoJUvPDLx1qhLS0LtD2kzJoq",
            # plain: "admin123"
        },
    }
}

COOKIE_NAME = "ophthalmocapture_auth"
COOKIE_KEY = "ophthalmocapture_secret_key"
COOKIE_EXPIRY_DAYS = 1


def _get_authenticator():
    """Return a single shared Authenticate instance per session."""
    if "authenticator" not in st.session_state:
        st.session_state["authenticator"] = stauth.Authenticate(
            credentials=DEFAULT_CREDENTIALS,
            cookie_name=COOKIE_NAME,
            cookie_key=COOKIE_KEY,
            cookie_expiry_days=COOKIE_EXPIRY_DAYS,
        )
    return st.session_state["authenticator"]


def require_auth() -> bool:
    """Show login form and return True if the user is authenticated.

    If streamlit-authenticator is not installed, returns True immediately
    (anonymous mode) and sets doctor_name to empty string.
    """
    if not AUTH_AVAILABLE:
        # Graceful degradation: no auth library → anonymous mode
        return True

    authenticator = _get_authenticator()

    try:
        authenticator.login(location="main")
    except Exception:
        pass

    if st.session_state.get("authentication_status"):
        # Set doctor name from authenticated user
        username = st.session_state.get("username", "")
        user_info = DEFAULT_CREDENTIALS["usernames"].get(username, {})
        st.session_state.doctor_name = user_info.get("name", username)
        return True

    elif st.session_state.get("authentication_status") is False:
        st.error("❌ Usuario o contraseña incorrectos.")
        return False

    else:
        st.info("👨‍⚕️ Inicie sesión para acceder al sistema de etiquetado.")
        return False


def render_logout_button():
    """Show a logout button in the sidebar (only if auth is active)."""
    if not AUTH_AVAILABLE:
        return

    if st.session_state.get("authentication_status"):
        authenticator = _get_authenticator()
        authenticator.logout("🚪 Cerrar sesión", location="sidebar")
