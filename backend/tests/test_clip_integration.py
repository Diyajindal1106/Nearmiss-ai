"""Real-model smoke test. Skipped automatically unless torch + transformers are installed
and the CLIP weights are available (first run downloads ~600 MB)."""
import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from PIL import Image  # noqa: E402

from app.classifier import HazardClassifier  # noqa: E402


def test_real_inference_returns_scores_or_honest_unavailable():
    clf = HazardClassifier()
    out = clf.analyze(Image.new("RGB", (224, 224), (120, 120, 120)))
    assert out["status"] in {"ok", "uncertain", "unavailable"}
    if out["status"] != "unavailable":
        assert len(out["scores"]) == 4 and all("cosine_similarity" in s for s in out["scores"])
        assert out["status"] == "uncertain"  # a flat grey square must not be called a hazard
