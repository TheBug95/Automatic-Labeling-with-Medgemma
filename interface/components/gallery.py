"""OphthalmoCapture — Image Gallery Component

Renders a thumbnail strip of all uploaded images with labeling-status
badges and click-to-select behaviour.
"""

import streamlit as st
from i18n import t
from services import session_manager as sm


def _label_badge(label):
    """Return a coloured status indicator for the label value."""
    if label is None:
        return "🔴"   # unlabeled
    return "🟢"       # labeled (any value)


def render_gallery():
    """Draw the horizontal thumbnail gallery with status badges.

    Returns True if the user clicked on a thumbnail (triggers rerun).
    """
    images = st.session_state.images
    order = st.session_state.image_order
    current_id = st.session_state.current_image_id

    if not order:
        return False

    # ── Progress bar ─────────────────────────────────────────────────────
    labeled, total = sm.get_labeling_progress()
    progress_text = f"{t('progress')}: **{labeled}** / **{total}** {t('labeled_suffix')}"
    st.markdown(progress_text)
    st.progress(labeled / total if total > 0 else 0)

    # ── Thumbnail strip ──────────────────────────────────────────────────
    # Show up to 8 thumbnails per row; wrap if there are more.
    COLS_PER_ROW = 8
    num_images = len(order)

    # Paginate the gallery if many images
    if "gallery_page" not in st.session_state:
        st.session_state.gallery_page = 0

    total_pages = max(1, -(-num_images // COLS_PER_ROW))  # ceil division
    page = st.session_state.gallery_page
    start = page * COLS_PER_ROW
    end = min(start + COLS_PER_ROW, num_images)
    visible_ids = order[start:end]

    cols = st.columns(max(len(visible_ids), 1))

    clicked = False
    for i, img_id in enumerate(visible_ids):
        img = images[img_id]
        badge = _label_badge(img["label"])
        is_selected = (img_id == current_id)

        with cols[i]:
            # Visual border to highlight the selected thumbnail
            if is_selected:
                st.markdown(
                    "<div style='border:3px solid #4CAF50; border-radius:8px; "
                    "padding:2px;'>",
                    unsafe_allow_html=True,
                )

            st.image(img["bytes"], use_container_width=True)

            if is_selected:
                st.markdown("</div>", unsafe_allow_html=True)

            # Label + filename
            short_name = img["filename"]
            if len(short_name) > 18:
                short_name = short_name[:15] + "…"

            if st.button(
                f"{badge} {short_name}",
                key=f"thumb_{img_id}",
                use_container_width=True,
            ):
                sm.set_current_image(img_id)
                clicked = True

    # ── Gallery pagination ───────────────────────────────────────────────
    if total_pages > 1:
        gc1, gc2, gc3 = st.columns([1, 3, 1])
        with gc1:
            if page > 0:
                if st.button(t("gallery_prev"), key="gal_prev"):
                    st.session_state.gallery_page -= 1
                    clicked = True
        with gc2:
            st.markdown(
                f"<div style='text-align:center; padding-top:6px;'>"
                f"{t('page')} {page + 1} / {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with gc3:
            if page < total_pages - 1:
                if st.button(t("gallery_next"), key="gal_next"):
                    st.session_state.gallery_page += 1
                    clicked = True

    return clicked
