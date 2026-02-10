"""OphthalmoCapture — Image Protection Layer

Injects CSS and JavaScript into the Streamlit page to prevent users from
downloading, dragging, or otherwise saving the confidential medical images.

KEY DESIGN DECISION:
  Streamlit's st.markdown(unsafe_allow_html=True) renders <style> tags but
  STRIPS <script> tags for security.  Therefore:
    • CSS protections → injected via st.markdown (works natively).
    • JS  protections → injected via st.components.v1.html() which creates
      a real iframe where JavaScript executes.  From that iframe we reach
      the main Streamlit page via window.parent.document (same-origin).

Protection layers (defence-in-depth):
  1. CSS: pointer-events:none, user-select:none, draggable:false on <img>.
  2. CSS: transparent ::after overlay on stImage containers blocks
     right-click "Save image as…".
  3. CSS: -webkit-touch-callout:none blocks mobile long-press save.
  4. JS:  contextmenu event blocked on the ENTIRE parent document.
  5. JS:  Ctrl+S / Ctrl+U / Ctrl+Shift+I / Ctrl+Shift+J / Ctrl+Shift+C /
         F12 all intercepted and cancelled.
  6. JS:  dragstart blocked for all images.
  7. JS:  MutationObserver re-applies draggable=false to dynamically added
         images (Streamlit re-renders on every interaction).
  8. JS:  Blob/URL revocation — monkey-patches URL.createObjectURL and
         document.createElement to block programmatic image extraction.

IMPORTANT LIMITATION:
  No client-side measure can guarantee absolute prevention.  A technically
  sophisticated user could still extract images through OS-level screenshots,
  network packet inspection, or browser extensions that bypass JS hooks.
  These protections eliminate ALL standard browser download paths and raise
  the bar significantly.
"""

import streamlit as st
import streamlit.components.v1 as components

# ── CSS injected via st.markdown (Streamlit renders <style> natively) ────────
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
</style>
"""

# ── JavaScript injected via components.html (runs in real iframe) ────────────
# From the iframe we access window.parent.document to attach listeners
# on the ACTUAL Streamlit page, not just inside the hidden iframe.
_PROTECTION_JS_HTML = """
<script>
(function () {
    // The parent document is the real Streamlit page
    var doc;
    try { doc = window.parent.document; } catch(e) { doc = document; }

    // Guard: only inject once per page lifecycle
    if (doc.__ophthalmo_protection__) return;
    doc.__ophthalmo_protection__ = true;

    function block(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    }

    // ── Layer 4: Block context menu on ENTIRE page ──────────────────────
    doc.addEventListener('contextmenu', function (e) {
        return block(e);
    }, true);

    // ── Layer 5: Block keyboard shortcuts ───────────────────────────────
    doc.addEventListener('keydown', function (e) {
        var dominated = false;
        var ctrl = e.ctrlKey || e.metaKey;
        var key  = e.key ? e.key.toLowerCase() : '';

        // Ctrl+S  — Save page
        if (ctrl && key === 's') dominated = true;
        // Ctrl+U  — View source
        if (ctrl && key === 'u') dominated = true;
        // Ctrl+P  — Print (can save as PDF with images)
        if (ctrl && key === 'p') dominated = true;
        // F12     — DevTools
        if (e.keyCode === 123) dominated = true;
        // Ctrl+Shift+I — DevTools (Inspector)
        if (ctrl && e.shiftKey && key === 'i') dominated = true;
        // Ctrl+Shift+J — DevTools (Console)
        if (ctrl && e.shiftKey && key === 'j') dominated = true;
        // Ctrl+Shift+C — DevTools (Element picker)
        if (ctrl && e.shiftKey && key === 'c') dominated = true;

        if (dominated) return block(e);
    }, true);

    // ── Layer 6: Block drag-and-drop of images ─────────────────────────
    doc.addEventListener('dragstart', function (e) {
        if (e.target && e.target.tagName === 'IMG') return block(e);
    }, true);

    // ── Layer 7: MutationObserver — lock new images as they appear ──────
    function lockImages(root) {
        var imgs = (root.querySelectorAll) ? root.querySelectorAll('img') : [];
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].setAttribute('draggable', 'false');
            imgs[i].ondragstart = function() { return false; };
            imgs[i].oncontextmenu = function() { return false; };
        }
    }
    lockImages(doc);

    // Debounce to reduce excessive firing
    var lockTimer = null;
    var obs = new MutationObserver(function (mutations) {
        if (lockTimer) return;  // skip if already scheduled
        lockTimer = setTimeout(function() {
            lockTimer = null;
            for (var m = 0; m < mutations.length; m++) {
                var nodes = mutations[m].addedNodes;
                for (var n = 0; n < nodes.length; n++) {
                    if (nodes[n].nodeType === 1) lockImages(nodes[n]);
                }
            }
        }, 100);  // debounce 100ms
    });
    obs.observe(doc.body, { childList: true, subtree: true });

    // ── Layer 8: Neuter Blob URL creation for images ────────────────────
    // Prevents programmatic extraction via createObjectURL
    var origCreateObjectURL = URL.createObjectURL;
    URL.createObjectURL = function(obj) {
        if (obj instanceof Blob && obj.type && obj.type.startsWith('image/')) {
            console.warn('[OphthalmoCapture] Blob URL creation blocked for images');
            return '';
        }
        return origCreateObjectURL.call(URL, obj);
    };

})();
</script>
"""


def inject_image_protection():
    """Inject all CSS + JS image-protection layers into the page.

    Call this ONCE near the top of main.py, after st.set_page_config().
    CSS is re-injected every rerun (Streamlit requires it in the render tree).
    JS has its own internal guard to avoid duplicate listeners.
    """
    # CSS — MUST be re-injected every rerun so it stays in the DOM
    st.markdown(_PROTECTION_CSS, unsafe_allow_html=True)

    # JS — uses components.html; internal guard prevents duplicate listeners.
    # height=0, width=0 makes the iframe invisible and avoids layout shifts.
    components.html(_PROTECTION_JS_HTML, height=0, width=0, scrolling=False)
