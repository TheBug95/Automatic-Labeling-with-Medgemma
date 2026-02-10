"""OphthalmoCapture — Export Service

Generates in-memory ZIP packages for individual images or the full session.
Also produces ML-ready formats (HuggingFace CSV, JSONL).
Everything is built from st.session_state — nothing touches disk.
"""

import io
import csv
import json
import zipfile
import datetime
import streamlit as st


def _sanitize(name: str) -> str:
    """Remove characters not safe for ZIP entry names."""
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name)


def _image_metadata(img: dict) -> dict:
    """Build a JSON-serialisable metadata dict for one image."""
    return {
        "filename": img["filename"],
        "label": img["label"],
        "locs_data": img.get("locs_data", {}),
        "transcription": img["transcription"],
        "transcription_original": img["transcription_original"],
        "doctor": img.get("labeled_by", ""),
        "timestamp": img["timestamp"].isoformat() if img.get("timestamp") else "",
        "has_audio": img["audio_bytes"] is not None,
    }


# ── Individual export ────────────────────────────────────────────────────────

def export_single_image(image_id: str) -> tuple[bytes, str]:
    """Create a ZIP for one image's labeling data.

    Returns (zip_bytes, suggested_filename).
    """
    img = st.session_state.images[image_id]
    safe_name = _sanitize(img["filename"].rsplit(".", 1)[0])
    folder = f"etiquetado_{safe_name}"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # metadata.json
        meta = _image_metadata(img)
        zf.writestr(f"{folder}/metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))

        # transcripcion.txt
        zf.writestr(f"{folder}/transcripcion.txt", img["transcription"] or "")

        # audio_dictado.wav (if recorded)
        if img["audio_bytes"]:
            zf.writestr(f"{folder}/audio_dictado.wav", img["audio_bytes"])

    zip_bytes = buf.getvalue()
    return zip_bytes, f"{folder}.zip"


# ── Bulk export (full session) ───────────────────────────────────────────────

def export_full_session() -> tuple[bytes, str]:
    """Create a ZIP with all images' labeling data + a summary CSV.

    Returns (zip_bytes, suggested_filename).
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    root = f"sesion_{now}"
    images = st.session_state.images
    order = st.session_state.image_order

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── Summary CSV ──────────────────────────────────────────────────
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["filename", "label", "nuclear_opalescence",
                         "nuclear_color", "cortical_opacity",
                         "has_audio", "has_transcription", "doctor"])
        for img_id in order:
            img = images[img_id]
            locs = img.get("locs_data", {})
            writer.writerow([
                img["filename"],
                img["label"] or "",
                locs.get("nuclear_opalescence", ""),
                locs.get("nuclear_color", ""),
                locs.get("cortical_opacity", ""),
                "yes" if img["audio_bytes"] else "no",
                "yes" if img["transcription"] else "no",
                img.get("labeled_by", ""),
            ])
        zf.writestr(f"{root}/resumen.csv", csv_buf.getvalue())

        # ── Full metadata JSON ───────────────────────────────────────────
        all_meta = []
        for img_id in order:
            all_meta.append(_image_metadata(images[img_id]))
        zf.writestr(
            f"{root}/etiquetas.json",
            json.dumps(all_meta, ensure_ascii=False, indent=2),
        )

        # ── Per-image folders ────────────────────────────────────────────
        for idx, img_id in enumerate(order, start=1):
            img = images[img_id]
            safe_name = _sanitize(img["filename"].rsplit(".", 1)[0])
            img_folder = f"{root}/{idx:03d}_{safe_name}"

            meta = _image_metadata(img)
            zf.writestr(f"{img_folder}/metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.writestr(f"{img_folder}/transcripcion.txt", img["transcription"] or "")

            if img["audio_bytes"]:
                zf.writestr(f"{img_folder}/audio_dictado.wav", img["audio_bytes"])

    zip_bytes = buf.getvalue()
    return zip_bytes, f"{root}.zip"


# ── Session summary ──────────────────────────────────────────────────────────

def get_session_summary() -> dict:
    """Return a summary dict for pre-download validation."""
    images = st.session_state.images
    total = len(images)
    labeled = sum(1 for img in images.values() if img["label"] is not None)
    with_audio = sum(1 for img in images.values() if img["audio_bytes"] is not None)
    with_text = sum(1 for img in images.values() if img["transcription"])
    return {
        "total": total,
        "labeled": labeled,
        "with_audio": with_audio,
        "with_transcription": with_text,
        "unlabeled": total - labeled,
    }


# ── ML-ready export formats (Idea F) ────────────────────────────────────────

def export_huggingface_csv() -> tuple[bytes, str]:
    """Export a CSV compatible with HuggingFace datasets.

    Columns: filename, label, label_code, transcription, doctor
    Only labeled images are included.

    Returns (csv_bytes, suggested_filename).
    """
    import config

    images = st.session_state.images
    order = st.session_state.image_order
    label_map = {opt["display"]: opt["code"] for opt in config.LABEL_OPTIONS}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["filename", "label", "label_code",
                     "nuclear_opalescence", "nuclear_color", "cortical_opacity",
                     "transcription", "doctor"])

    for img_id in order:
        img = images[img_id]
        if img["label"] is None:
            continue
        locs = img.get("locs_data", {})
        writer.writerow([
            img["filename"],
            img["label"],
            label_map.get(img["label"], ""),
            locs.get("nuclear_opalescence", ""),
            locs.get("nuclear_color", ""),
            locs.get("cortical_opacity", ""),
            img["transcription"],
            img.get("labeled_by", ""),
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    return csv_bytes, f"dataset_hf_{now}.csv"


def export_jsonl() -> tuple[bytes, str]:
    """Export JSONL (one JSON object per line) suitable for LLM fine-tuning.

    Each line: {"filename", "label", "label_code", "transcription", "doctor"}
    Only labeled images are included.

    Returns (jsonl_bytes, suggested_filename).
    """
    import config

    images = st.session_state.images
    order = st.session_state.image_order
    label_map = {opt["display"]: opt["code"] for opt in config.LABEL_OPTIONS}

    lines = []
    for img_id in order:
        img = images[img_id]
        if img["label"] is None:
            continue
        locs = img.get("locs_data", {})
        obj = {
            "filename": img["filename"],
            "label": img["label"],
            "label_code": label_map.get(img["label"], ""),
            "nuclear_opalescence": locs.get("nuclear_opalescence"),
            "nuclear_color": locs.get("nuclear_color"),
            "cortical_opacity": locs.get("cortical_opacity"),
            "transcription": img["transcription"],
            "doctor": img.get("labeled_by", ""),
        }
        lines.append(json.dumps(obj, ensure_ascii=False))

    jsonl_bytes = "\n".join(lines).encode("utf-8")
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    return jsonl_bytes, f"dataset_{now}.jsonl"
