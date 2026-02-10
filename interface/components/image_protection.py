"""OphthalmoCapture — Image Protection Layer

Injects CSS and JavaScript into the Streamlit page to prevent users from
downloading, dragging, or otherwise saving the confidential medical images.

APPROACH (HF Spaces compatible):
  1. CSS via st.markdown(unsafe_allow_html=True) — Streamlit renders <style>
     natively.  Handles pointer-events, overlays, drag prevention.
  2. JS via st.html() — Streamlit >= 1.33 renders raw HTML (including
     <script>) inside a tiny srcdoc iframe.  From there we reach the real
     Streamlit DOM via window.parent.document (same-origin).
  3. Additional CSS hides the st.html wrapper divs ([data-testid="stHtml"])
     so the iframe has ZERO visual footprint — no layout shifts.

Protection layers (defence-in-depth):
  1. CSS: pointer-events:none, user-select:none on <img>.
  2. CSS: transparent ::after overlay on stImage containers.
  3. CSS: -webkit-touch-callout:none for mobile.
  4. JS:  contextmenu blocked on entire parent document.
  5. JS:  Ctrl+S / Ctrl+U / Ctrl+P / F12 / DevTools shortcuts blocked.
  6. JS:  dragstart blocked for images.
  7. JS:  MutationObserver re-applies draggable=false to new images.
"""

import streamlit as st

# ── CSS via st.markdown ──────────────────────────────────────────────────────
_PROTECTION_CSS = """
<style>
/* Layer 1: Disable ALL interaction on <img> tags */
img {
    pointer-events: none       !important;
    user-select: none          !important;
    -webkit-user-select: none  !important;
    -moz-user-select: none     !important;
    -ms-user-select: none      !important;
    -webkit-user-drag: none    !important;
    -webkit-touch-callout: none !important;
}

/* Layer 2: Transparent overlay on every Streamlit image container */
[data-testid="stImage"] {
    position: relative !important;
}
[data-testid="stImage"]::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 10;
    background: transparent;
    pointer-events: auto !important;
    cursor: default;
}

/* Layer 3: Extra drag prevention */
[data-testid="stImage"] img {
    -webkit-user-drag: none !important;
    user-drag: none         !important;
}

/* ── Hide st.html() wrappers to prevent ANY layout shift ──────────────── */
[data-testid="stHtml"] {
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 0 !important;
    font-size: 0 !important;
    border: none !important;
}
[data-testid="stHtml"] iframe {
    height: 0 !important;
    min-height: 0 !important;
    border: none !important;
    display: block !important;
}
</style>
"""

# ── JS via st.html() — runs inside srcdoc iframe, reaches parent DOM ─────────
_PROTECTION_JS = """
<script>
(function () {
    var doc;
    try { doc = window.parent.document; } catch(e) { doc = document; }

    // Guard: only attach once per page lifecycle
    if (doc.__ophthalmo_protection__) return;
    doc.__ophthalmo_protection__ = true;

    function block(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    }

    // ── Block context menu (right-click) on ENTIRE page ─────────────────
    doc.addEventListener('contextmenu', function (e) {
        return block(e);
    }, true);

    // ── Block keyboard shortcuts ────────────────────────────────────────
    doc.addEventListener('keydown', function (e) {
        var dominated = false;
        var ctrl = e.ctrlKey || e.metaKey;
        var key  = e.key ? e.key.toLowerCase() : '';

        if (ctrl && key === 's') dominated = true;   // Save page
        if (ctrl && key === 'u') dominated = true;   // View source
        if (ctrl && key === 'p') dominated = true;   // Print
        if (e.keyCode === 123)   dominated = true;   // F12
        if (ctrl && e.shiftKey && key === 'i') dominated = true;  // Inspector
        if (ctrl && e.shiftKey && key === 'j') dominated = true;  // Console
        if (ctrl && e.shiftKey && key === 'c') dominated = true;  // Picker

        if (dominated) return block(e);
    }, true);

    // ── Block drag-and-drop of images ───────────────────────────────────
    doc.addEventListener('dragstart', function (e) {
        if (e.target && e.target.tagName === 'IMG') return block(e);
    }, true);

    // ── MutationObserver — lock new images as they appear ───────────────
    function lockImgs(root) {
        var imgs = root.querySelectorAll ? root.querySelectorAll('img') : [];
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].setAttribute('draggable', 'false');
            imgs[i].ondragstart = function () { return false; };
            imgs[i].oncontextmenu = function () { return false; };
        }
    }
    lockImgs(doc);

    var timer = null;
    new MutationObserver(function () {
        if (timer) return;
        timer = setTimeout(function () {
            timer = null;
            lockImgs(doc);
        }, 250);
    }).observe(doc.body, { childList: true, subtree: true });

})();
</script>
"""


def inject_image_protection():
    """Inject CSS + JS image-protection layers into the page.

    - CSS via st.markdown  (always re-injected per rerun, as Streamlit requires).
    - JS via st.html       (rendered with <script> support; internal guard
      prevents duplicate listeners across reruns).
    - The CSS also hides st.html wrappers to prevent layout shifts.
    """
    # 1) CSS protection + hide st.html wrappers
    st.markdown(_PROTECTION_CSS, unsafe_allow_html=True)

    # 2) JS protection (right-click, keyboard shortcuts, drag, observer)
    st.html(_PROTECTION_JS)
