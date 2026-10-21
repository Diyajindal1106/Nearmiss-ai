"""Tests the DECISION RULES with synthetic similarities. These do not exercise CLIP itself;
see test_clip_integration.py (runs only when the model is installed/downloaded)."""
import numpy as np
from PIL import Image

from app.classifier import NONE_KEY, image_quality, interpret


def sims(none=0.20, **over):
    base = {"pothole": 0.20, "broken_stairs": 0.20, "wet_floor": 0.20, "exposed_wire": 0.20, NONE_KEY: none}
    base.update(over)
    return base


def test_clear_winner_is_suggested():
    r = interpret(sims(exposed_wire=0.31, none=0.19))
    assert r["status"] == "ok" and r["suggested_category"] == "exposed_wire"
    assert r["scores"][0]["category"] == "exposed_wire"


def test_flat_scores_are_uncertain():
    r = interpret(sims())
    assert r["status"] == "uncertain" and r["suggested_category"] is None
    assert "Uncertain" in r["suggested_label"]


def test_irrelevant_image_is_uncertain():
    r = interpret(sims(none=0.30))
    assert r["status"] == "uncertain" and r["closest_category"] is None


def test_close_call_between_two_hazards_is_uncertain():
    r = interpret(sims(pothole=0.285, broken_stairs=0.284, none=0.18))
    assert r["status"] == "uncertain"


def test_low_absolute_similarity_is_uncertain():
    r = interpret({"pothole": 0.12, "broken_stairs": 0.05, "wet_floor": 0.05, "exposed_wire": 0.05, NONE_KEY: 0.04})
    assert r["status"] == "uncertain"


def test_blurry_forces_uncertain():
    r = interpret(sims(pothole=0.33, none=0.19), {"too_blurry": True})
    assert r["status"] == "uncertain" and "blurry" in r["reason"]


def test_shares_sum_to_one_with_none():
    r = interpret(sims(pothole=0.3))
    total = sum(s["relative_share"] for s in r["scores"]) + r["not_a_hazard_share"]
    assert abs(total - 1) < 1e-3


def test_image_quality_flags_flat_image():
    flat = Image.new("RGB", (200, 200), (128, 128, 128))
    q = image_quality(flat)
    assert q["too_blurry"] and q["warnings"]


def test_image_quality_passes_textured_image():
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(0, 255, (200, 200, 3), dtype=np.uint8))
    assert not image_quality(img)["too_blurry"]
