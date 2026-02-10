"""OphthalmoCapture — Image Protection Layer

Injects CSS and JavaScript into the Streamlit page to prevent users from
downloading, dragging, or otherwise saving the confidential medical images.

APPROACH:
  Streamlit's st.markdown(unsafe_allow_html=True) renders <style> tags but
  STRIPS <script> tags.  To run JS without components.html (which creates
  iframes that cause layout shifts on HF Spaces), we use the classic
  <img src=x onerror="…"> trick — the onerror handler executes inline JS
  directly in the main Streamlit DOM, with no iframe.

Protection layers (defence-in-depth):
  1. CSS: pointer-events:none, user-select:none on <img>.
  2. CSS: transparent ::after overlay on stImage containers.
  3. CSS: -webkit-touch-callout:none for mobile.
  4. JS:  contextmenu blocked on entire document.
  5. JS:  Ctrl+S / Ctrl+U / Ctrl+P / F12 / DevTools shortcuts blocked.
  6. JS:  dragstart blocked for images.
  7. JS:  MutationObserver re-applies draggable=false to new images.
"""

import streamlit as st

# ── CSS + JS injected via st.markdown ────────────────────────────────────────
_PROTECTION_HTML = """
<style>
/* Layer 1: Disable ALL interaction on <img> tags */
img:not([data-protection-trigger]) {
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

/* Hide the trigger pixel completely */
img[data-protection-trigger] {
    display: none !important;
}
</style>

<!-- JS via onerror trick — runs directly in Streamlit DOM, no iframe -->
<img data-protection-trigger src="x" onerror="
(function(doc){
    if(doc.__ophthalmo_protection__) return;
    doc.__ophthalmo_protection__=true;

    function block(e){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();return false;}

    doc.addEventListener('contextmenu',function(e){return block(e);},true);

    doc.addEventListener('keydown',function(e){
        var dominated=false;
        var ctrl=e.ctrlKey||e.metaKey;
        var key=e.key?e.key.toLowerCase():'';
        if(ctrl&&key==='s')dominated=true;
        if(ctrl&&key==='u')dominated=true;
        if(ctrl&&key==='p')dominated=true;
        if(e.keyCode===123)dominated=true;
        if(ctrl&&e.shiftKey&&key==='i')dominated=true;
        if(ctrl&&e.shiftKey&&key==='j')dominated=true;
        if(ctrl&&e.shiftKey&&key==='c')dominated=true;
        if(dominated)return block(e);
    },true);

    doc.addEventListener('dragstart',function(e){
        if(e.target&&e.target.tagName==='IMG')return block(e);
    },true);

    function lockImgs(root){
        var imgs=root.querySelectorAll?root.querySelectorAll('img:not([data-protection-trigger])'):[];
        for(var i=0;i<imgs.length;i++){
            imgs[i].setAttribute('draggable','false');
            imgs[i].ondragstart=function(){return false;};
            imgs[i].oncontextmenu=function(){return false;};
        }
    }
    lockImgs(doc);

    var t=null;
    new MutationObserver(function(muts){
        if(t)return;
        t=setTimeout(function(){
            t=null;
            lockImgs(doc);
        },200);
    }).observe(doc.body,{childList:true,subtree:true});

})(document);
" />
"""


def inject_image_protection():
    """Inject CSS + JS image-protection layers into the page.

    Uses st.markdown only — NO components.html iframes — so there are
    zero layout shifts.  The JS guard (doc.__ophthalmo_protection__)
    ensures listeners are attached only once per page lifecycle even
    though st.markdown re-renders on every Streamlit rerun.
    """
    st.markdown(_PROTECTION_HTML, unsafe_allow_html=True)
