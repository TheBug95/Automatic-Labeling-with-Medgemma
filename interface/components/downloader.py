"""OphthalmoCapture — Download Component

Provides individual and bulk download buttons for the labeling package.
Uses @st.dialog modals to warn about incomplete labeling before download.
"""

import streamlit as st
import pandas as pd
import config
from i18n import t
from services.export_service import (
    export_single_image,
    export_full_session,
    get_session_summary,
    export_huggingface_csv,
    export_jsonl,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_image_missing_info(img: dict) -> list[str]:
    """Return a list of human-readable items that are missing for one image."""
    missing = []
    if img.get("label") is None:
        missing.append(t("missing_categorical"))
    elif img["label"] == "Cataract":
        locs = img.get("locs_data", {})
        for field in config.LOCS_FIELDS:
            fid = field["field_id"]
            if fid not in locs:
                missing.append(t("missing_locs", field=field["label"]))
    if not img.get("transcription"):
        missing.append(t("missing_voice"))
    return missing


# ── Dialog: individual download with incomplete labeling ─────────────────────

def _show_single_incomplete_dialog(image_id: str):
    """Warn about missing labeling for one image before individual download."""

    @st.dialog(t("dlg_single_incomplete"), dismissible=False)
    def _dlg():
        img = st.session_state.images.get(image_id)
        if img is None:
            st.rerun()
            return

        missing = _get_image_missing_info(img)
        if not missing:
            st.session_state.pop("_pending_single_dl", None)
            st.rerun()
            return

        st.markdown(
            t("incomplete_fields_msg", filename=img['filename'])
        )
        for item in missing:
            st.markdown(f"- {item}")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            zip_bytes, zip_name = export_single_image(image_id)
            if st.download_button(
                label=t("download_anyway"),
                data=zip_bytes,
                file_name=zip_name,
                mime="application/zip",
                key="_dlg_dl_single_anyway",
                use_container_width=True,
            ):
                st.session_state.pop("_pending_single_dl", None)
                st.rerun()
        with c2:
            if st.button(
                t("go_back_finish"),
                use_container_width=True,
                type="primary",
            ):
                st.session_state.pop("_pending_single_dl", None)
                st.rerun()

    _dlg()


# ── Dialog: bulk download with incomplete images ─────────────────────────────

def _show_bulk_incomplete_dialog():
    """Table showing per-image what labeling is missing before bulk download."""

    @st.dialog(t("dlg_bulk_incomplete"), width="large", dismissible=False)
    def _dlg():
        images = st.session_state.images
        order = st.session_state.image_order

        # Build table data
        rows = []
        for img_id in order:
            img = images[img_id]
            has_categorical = img.get("label") is not None
            needs_locs = img.get("label") == "Cataract"
            locs = img.get("locs_data", {})

            if needs_locs:
                locs_filled = all(
                    f["field_id"] in locs for f in config.LOCS_FIELDS
                )
            else:
                locs_filled = True  # Not applicable

            has_voice = bool(img.get("transcription"))

            # Determine LOCS III column value:
            #   - Cataract selected, all filled → ✅
            #   - Cataract selected, missing fields → ❌
            #   - No label selected → ❌
            #   - Non-cataract label selected → "Not Required"
            if needs_locs:
                locs_cell = "✅" if locs_filled else "❌"
            elif has_categorical:
                locs_cell = t("locs_not_required")
            else:
                locs_cell = "❌"

            # Only show images that have something missing
            if not (has_categorical and locs_filled and has_voice):
                rows.append({
                    t("col_image"): img["filename"],
                    t("col_categorical"): "✅" if has_categorical else "❌",
                    t("col_locs"): locs_cell,
                    t("col_voice"): "✅" if has_voice else "❌",
                })

        if not rows:
            st.session_state.pop("_pending_bulk_dl", None)
            st.rerun()
            return

        st.markdown(
            t("bulk_incomplete_msg", count=len(rows))
        )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            zip_bytes, zip_name = export_full_session()
            if st.download_button(
                label=t("download_anyway"),
                data=zip_bytes,
                file_name=zip_name,
                mime="application/zip",
                key="_dlg_dl_bulk_anyway",
                use_container_width=True,
            ):
                st.session_state.session_downloaded = True
                st.session_state.pop("_pending_bulk_dl", None)
                st.rerun()
        with c2:
            if st.button(
                t("go_back_finish"),
                use_container_width=True,
                type="primary",
            ):
                st.session_state.pop("_pending_bulk_dl", None)
                st.rerun()

    _dlg()


# ── Main downloader ──────────────────────────────────────────────────────────

def render_downloader(image_id: str):
    """Render the download panel for the current image + bulk download."""
    img = st.session_state.images.get(image_id)
    if img is None:
        return

    # ── Show pending dialogs (survive reruns) ────────────────────────────
    if "_pending_single_dl" in st.session_state:
        _show_single_incomplete_dialog(st.session_state["_pending_single_dl"])
        return

    if "_pending_bulk_dl" in st.session_state:
        _show_bulk_incomplete_dialog()
        return

    # ── Two columns: Individual download (left) | Session info (right) ───
    col_dl, col_info = st.columns(2)

    with col_dl:
        st.subheader(t("single_download"))

        # Check completeness for individual download
        missing = _get_image_missing_info(img)
        if missing:
            # Show button that triggers the warning dialog
            if st.button(
                t("download_file", filename=img['filename']),
                key=f"dl_single_check_{image_id}",
                use_container_width=True,
            ):
                st.session_state["_pending_single_dl"] = image_id
                st.rerun()
        else:
            zip_bytes, zip_name = export_single_image(image_id)
            st.download_button(
                label=t("download_file", filename=img['filename']),
                data=zip_bytes,
                file_name=zip_name,
                mime="application/zip",
                key=f"dl_single_{image_id}",
                use_container_width=True,
            )

    with col_info:
        st.subheader(t("session_info"))
        summary = get_session_summary()
        sc1, sc2 = st.columns(2)
        with sc1:
            st.metric(t("images_metric"), summary["total"])
            st.metric(t("with_audio"), summary["with_audio"])
        with sc2:
            st.metric(t("labeled_metric"), f"{summary['labeled']} / {summary['total']}")
            st.metric(t("with_transcription"), summary["with_transcription"])

    st.divider()

    # ── Full-width: Bulk download ────────────────────────────────────────
    st.subheader(t("bulk_download"))

    summary = get_session_summary()

    if summary["total"] == 0:
        st.info(t("no_images_download"))
    else:
        # Check if any image has incomplete labeling
        has_incomplete = any(
            _get_image_missing_info(st.session_state.images[iid])
            for iid in st.session_state.image_order
        )

        if has_incomplete:
            if st.button(
                t("download_all_zip"),
                key="dl_bulk_check",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["_pending_bulk_dl"] = True
                st.rerun()
        else:
            zip_bytes, zip_name = export_full_session()
            if st.download_button(
                label=t("download_all_zip"),
                data=zip_bytes,
                file_name=zip_name,
                mime="application/zip",
                key="dl_bulk",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.session_downloaded = True

    # ── ML-ready formats (Idea F) ────────────────────────────────────────
    if summary["labeled"] > 0:
        st.markdown(t("ml_formats"))
        ml1, ml2 = st.columns(2)
        with ml1:
            csv_bytes, csv_name = export_huggingface_csv()
            if st.download_button(
                label=t("hf_csv"),
                data=csv_bytes,
                file_name=csv_name,
                mime="text/csv",
                key="dl_hf_csv",
                use_container_width=True,
            ):
                st.session_state.session_downloaded = True
        with ml2:
            jsonl_bytes, jsonl_name = export_jsonl()
            if st.download_button(
                label=t("jsonl_finetune"),
                data=jsonl_bytes,
                file_name=jsonl_name,
                mime="application/jsonl",
                key="dl_jsonl",
                use_container_width=True,
            ):
                st.session_state.session_downloaded = True
