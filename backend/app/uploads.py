"""Upload validation and safe storage. Filenames are always server-generated."""
import io
import re
import uuid

from PIL import Image, UnidentifiedImageError

from . import config

Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_SIDE * config.MAX_IMAGE_SIDE

SAFE_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
_FORMAT_TO_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class UploadError(ValueError):
    """Raised with a user-readable message; mapped to HTTP 400/413/415."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def validate_image(data: bytes, content_type: str | None) -> tuple[str, Image.Image]:
    """Check size, declared type and ACTUAL content. Returns (extension, RGB image)."""
    if not data:
        raise UploadError("The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise UploadError(
            f"Image is too large (max {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB).", 413
        )
    if content_type not in config.ALLOWED_MIME:
        raise UploadError("Unsupported file type. Please upload a JPEG, PNG or WebP image.", 415)
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()  # detects truncated / corrupt files
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise UploadError("The file is not a valid, readable image.", 415)
    if fmt not in _FORMAT_TO_EXT:
        raise UploadError("Unsupported image format. Please use JPEG, PNG or WebP.", 415)
    w, h = img.size
    if min(w, h) < config.MIN_IMAGE_SIDE:
        raise UploadError(f"Image is too small (minimum {config.MIN_IMAGE_SIDE}px per side).")
    if max(w, h) > config.MAX_IMAGE_SIDE:
        raise UploadError(f"Image dimensions are too large (maximum {config.MAX_IMAGE_SIDE}px).")
    return _FORMAT_TO_EXT[fmt], img.convert("RGB")


def save_image(data: bytes, ext: str) -> str:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (config.UPLOAD_DIR / name).write_bytes(data)
    return name


def resolve_image_path(filename: str):
    """Map a public filename to a path ONLY if it matches our generated pattern."""
    if not SAFE_NAME.match(filename or ""):
        return None
    p = config.UPLOAD_DIR / filename
    return p if p.is_file() else None
