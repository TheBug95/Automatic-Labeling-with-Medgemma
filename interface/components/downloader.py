"""OphthalmoCapture — Download Component

Provides individual and bulk download buttons for the labeling package.
"""

import streamlit as st
from services.export_service import (
    export_single_image,
    export_full_session,
    get_session_summary,
    export_huggingface_csv,
    export_jsonl,
)


def render_downloader(image_id: str):
    """Render the download panel for the current image + bulk download."""
    img = st.session_state.images.get(image_id)
    if img is None:
        return

    st.subheader("📥 Descarga")

    # ── Individual download ──────────────────────────────────────────────
    st.markdown("**Imagen actual**")

    can_download = img["label"] is not None
    if not can_download:
        st.info("Etiquete la imagen para habilitar la descarga individual.")
    else:
        zip_bytes, zip_name = export_single_image(image_id)
        st.download_button(
            label=f"⬇️ Descargar etiquetado — {img['filename']}",
            data=zip_bytes,
            file_name=zip_name,
            mime="application/zip",
            key=f"dl_single_{image_id}",
            use_container_width=True,
        )

    st.divider()

    # ── Bulk download ────────────────────────────────────────────────────
    st.markdown("**Toda la sesión**")

    summary = get_session_summary()
    sc1, sc2 = st.columns(2)
    with sc1:
        st.metric("Imágenes", summary["total"])
        st.metric("Con audio", summary["with_audio"])
    with sc2:
        st.metric("Etiquetadas", f"{summary['labeled']} / {summary['total']}")
        st.metric("Con transcripción", summary["with_transcription"])

    if summary["unlabeled"] > 0:
        st.warning(
            f"⚠️ {summary['unlabeled']} imagen(es) sin etiquetar. "
            "Se incluirán en la descarga pero sin etiqueta."
        )

    if summary["total"] == 0:
        st.info("No hay imágenes para descargar.")
    else:
        zip_bytes, zip_name = export_full_session()
        if st.download_button(
            label="⬇️ Descargar todo el etiquetado (ZIP)",
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
        st.divider()
        st.markdown("**Formatos para ML**")
        ml1, ml2 = st.columns(2)
        with ml1:
            csv_bytes, csv_name = export_huggingface_csv()
            if st.download_button(
                label="📊 CSV (HuggingFace)",
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
                label="📄 JSONL (Fine-tuning)",
                data=jsonl_bytes,
                file_name=jsonl_name,
                mime="application/jsonl",
                key="dl_jsonl",
                use_container_width=True,
            ):
                st.session_state.session_downloaded = True
