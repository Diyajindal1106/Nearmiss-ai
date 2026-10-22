"""Image analysis with a real pretrained CLIP model (Hugging Face Transformers).

Zero-shot approach: the uploaded image and a set of candidate text descriptions are
embedded by CLIP; cosine similarities are compared. No hazard-specific training was
done, so results are SUGGESTIONS that a human must verify.

Honesty rules enforced here:
  * Real inference only. If the model cannot load/run, we return status="unavailable"
    with an error message. We never substitute made-up labels.
  * "relative_share" is a softmax over the candidate prompts only. It is NOT a
    calibrated probability of the hazard being present.
  * Low-evidence images return status="uncertain" -> manual review required.
"""
import logging
import math
import threading

import numpy as np
from PIL import Image

from . import config

log = logging.getLogger("nearmiss.classifier")

DISCLAIMER = "AI suggestion — human verification required."
SCORE_NOTE = (
    "Cosine similarity is the raw image–text similarity from CLIP. 'Relative share' is a "
    "softmax across the candidate descriptions only — it is not a calibrated probability "
    "and does not mean the hazard is present or that an accident is likely."
)
NONE_KEY = "not_a_hazard"


# ----------------------------------------------------------------- pure logic
def image_quality(img: Image.Image) -> dict:
    """Cheap sharpness / exposure heuristics (variance of a Laplacian). Untuned."""
    g = img.convert("L")
    g.thumbnail((256, 256))
    a = np.asarray(g, dtype=np.float32)
    lap = (
        -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    )
    var = float(lap.var())
    mean = float(a.mean())
    warnings = []
    if var < config.BLUR_WARN_VARIANCE:
        warnings.append("Image may be blurry or low-detail.")
    if mean < 25:
        warnings.append("Image is very dark.")
    elif mean > 235:
        warnings.append("Image is very bright / overexposed.")
    return {
        "sharpness": round(var, 1),
        "mean_brightness": round(mean, 1),
        "warnings": warnings,
        "too_blurry": var < config.BLUR_REJECT_VARIANCE,
    }


def softmax(values: list[float], scale: float) -> list[float]:
    m = max(values)
    exps = [math.exp(scale * (v - m)) for v in values]
    s = sum(exps)
    return [e / s for e in exps]


def interpret(cosines: dict[str, float], quality: dict | None = None) -> dict:
    """Turn per-class cosine similarities into a suggestion (or an honest 'uncertain').

    `cosines` must contain the four hazard keys plus NONE_KEY. Pure function so the
    decision rules can be unit-tested without the model.
    """
    keys = list(cosines)
    shares = dict(zip(keys, softmax([cosines[k] for k in keys], config.CLIP_LOGIT_SCALE)))
    ranked = sorted(keys, key=lambda k: -shares[k])
    top, second = ranked[0], ranked[1]
    margin = shares[top] - shares[second]

    reason = None
    if quality and quality.get("too_blurry"):
        reason = "Image is too blurry or featureless to classify reliably."
    elif top == NONE_KEY:
        reason = "The image looks more like something other than the four supported hazards."
    elif shares[top] < config.MIN_TOP_SHARE:
        reason = "No hazard description stood out clearly from the others."
    elif margin < config.MIN_MARGIN:
        reason = "Two or more hazard descriptions scored similarly."
    elif cosines[top] < config.MIN_COSINE:
        reason = "The image–text similarity is low for every hazard description."

    hazard_keys = [k for k in keys if k != NONE_KEY]
    scores = [
        {
            "category": k,
            "label": config.CATEGORIES[k]["label"],
            "cosine_similarity": round(cosines[k], 4),
            "relative_share": round(shares[k], 4),
        }
        for k in sorted(hazard_keys, key=lambda k: -shares[k])
    ]
    uncertain = reason is not None
    return {
        "status": "uncertain" if uncertain else "ok",
        "suggested_category": None if uncertain else top,
        "suggested_label": "Uncertain — manual review required"
        if uncertain
        else config.CATEGORIES[top]["label"],
        "closest_category": top if top != NONE_KEY else None,
        "reason": reason,
        "scores": scores,
        "not_a_hazard_share": round(shares[NONE_KEY], 4),
        "top_share": round(shares[top], 4),
        "margin": round(margin, 4),
        "thresholds": {
            "min_top_share": config.MIN_TOP_SHARE,
            "min_margin": config.MIN_MARGIN,
            "min_cosine": config.MIN_COSINE,
        },
    }


def unavailable(error: str) -> dict:
    return {
        "status": "unavailable",
        "suggested_category": None,
        "suggested_label": "AI analysis unavailable — please choose the category manually",
        "closest_category": None,
        "reason": error,
        "scores": [],
        "not_a_hazard_share": None,
        "top_share": None,
        "margin": None,
        "thresholds": None,
    }


# ------------------------------------------------------------------ the model
class HazardClassifier:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = "not_loaded"  # not_loaded | loading | ready | error
        self._error: str | None = None
        self._model = self._processor = self._torch = None
        self._text_feats: dict[str, "object"] = {}

    def status(self) -> dict:
        return {
            "state": self._state,
            "model": config.CLIP_MODEL_NAME,
            "error": self._error,
            "device": "cpu",
        }

    def load(self) -> None:
        """Load CLIP once. Raises on failure (callers convert to 'unavailable')."""
        with self._lock:
            if self._state == "ready":
                return
            self._state, self._error = "loading", None
            try:
                import torch  # imported lazily so the API starts without ML deps
                from transformers import CLIPModel, CLIPProcessor

                kw = {"local_files_only": True} if config.CLIP_OFFLINE else {}
                model = CLIPModel.from_pretrained(config.CLIP_MODEL_NAME, **kw).eval()
                processor = CLIPProcessor.from_pretrained(config.CLIP_MODEL_NAME, **kw)
                feats: dict[str, object] = {}
                with torch.no_grad():
                    for key, spec in {
                        **{k: v["prompts"] for k, v in config.CATEGORIES.items()},
                        NONE_KEY: config.NEGATIVE_PROMPTS,
                    }.items():
                        inputs = processor(text=spec, return_tensors="pt", padding=True)
                        t = model.get_text_features(**inputs)
                        if hasattr(t, "pooler_output") and t.pooler_output is not None:
                            t = t.pooler_output
                        t = t / t.norm(dim=-1, keepdim=True)
                        feats[key] = t
                self._model, self._processor, self._torch, self._text_feats = (
                    model, processor, torch, feats,
                )
                self._state = "ready"
                log.info("CLIP model loaded: %s", config.CLIP_MODEL_NAME)
            except Exception as exc:  # noqa: BLE001 - report any load failure honestly
                self._state = "error"
                self._error = f"{type(exc).__name__}: {exc}"[:400]
                log.error("CLIP load failed: %s", self._error)
                raise

    def analyze(self, img: Image.Image) -> dict:
        """Run real inference. Never returns fabricated labels."""
        try:
            self.load()
        except Exception:  # noqa: BLE001
            return unavailable(
                "The image-analysis model could not be loaded. " + (self._error or "")
            ) | {"model": config.CLIP_MODEL_NAME}
        try:
            quality = image_quality(img)
            torch = self._torch
            with torch.no_grad():
                inputs = self._processor(images=img, return_tensors="pt")
                f = self._model.get_image_features(**inputs)
                if hasattr(f, "pooler_output") and f.pooler_output is not None:
                    f = f.pooler_output
                f = f / f.norm(dim=-1, keepdim=True)
                cosines = {
                    k: float((f @ t.T).mean().item()) for k, t in self._text_feats.items()
                }
            result = interpret(cosines, quality)
            result["quality"] = quality
            result["model"] = config.CLIP_MODEL_NAME
            return result
        except Exception as exc:  # noqa: BLE001
            log.exception("inference failed")
            return unavailable(f"Inference failed: {type(exc).__name__}") | {
                "model": config.CLIP_MODEL_NAME
            }


classifier = HazardClassifier()
