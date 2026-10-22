import io

import pytest
from PIL import Image

from app import uploads


def png(size=(100, 100)):
    b = io.BytesIO()
    Image.new("RGB", size, (10, 90, 200)).save(b, "PNG")
    return b.getvalue()


def test_valid_png():
    ext, img = uploads.validate_image(png(), "image/png")
    assert ext == "png" and img.mode == "RGB"


@pytest.mark.parametrize("data,ct,status", [
    (b"", "image/png", 400),
    (b"not an image at all", "image/png", 415),
    (png(), "application/pdf", 415),
    (png((10, 10)), "image/png", 400),
    pytest.param(b"0" * (5 * 1024 * 1024 + 1), "image/png", 413, id="oversized"),
])
def test_rejections(data, ct, status):
    with pytest.raises(uploads.UploadError) as e:
        uploads.validate_image(data, ct)
    assert e.value.status == status


def test_truncated_image_rejected():
    with pytest.raises(uploads.UploadError):
        uploads.validate_image(png()[:60], "image/png")


def test_path_traversal_not_resolvable(tmp_env):
    assert uploads.resolve_image_path("../../etc/passwd") is None
    assert uploads.resolve_image_path("abc.png") is None
    name = uploads.save_image(png(), "png")
    assert uploads.resolve_image_path(name) is not None
