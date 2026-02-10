"""OphthalmoCapture — Utility Functions."""

import os


# Known image magic byte signatures
_IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff",          "JPEG"),
    (b"\x89PNG\r\n\x1a\n",    "PNG"),
    (b"II\x2a\x00",           "TIFF (LE)"),
    (b"MM\x00\x2a",           "TIFF (BE)"),
]


def setup_env():
    """Set up environment variables."""
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def validate_image_bytes(data: bytes) -> bool:
    """Verify that *data* starts with a known image magic-byte header.

    Returns True if valid, False otherwise.  This prevents non-image files
    from being accepted even if they have a valid extension.
    """
    if not data or len(data) < 8:
        return False
    for sig, _ in _IMAGE_SIGNATURES:
        if data[: len(sig)] == sig:
            return True
    return False
