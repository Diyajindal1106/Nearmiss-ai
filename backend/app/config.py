"""Central, documented configuration for NearMiss AI.

Everything that influences prioritisation or AI decisions lives here so it can be
inspected and tuned in one place. All numbers below are ILLUSTRATIVE DEFAULTS chosen
for a prototype; none has been validated against real incident data.
"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
    load_dotenv(BASE_DIR.parent.parent / ".env")
except ImportError:
    pass

DB_PATH = Path(os.getenv("NEARMISS_DB", BASE_DIR / "data" / "nearmiss.db"))
UPLOAD_DIR = Path(os.getenv("NEARMISS_UPLOADS", BASE_DIR / "uploads"))

# ---------------------------------------------------------------- uploads
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MIN_IMAGE_SIDE = 64  # px
MAX_IMAGE_SIDE = 8000  # px (guards against decompression bombs)

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "NEARMISS_CORS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

# -------------------------------------------------------------- categories
# default_severity is an ILLUSTRATIVE 1-5 starting estimate that an admin can change.
# prompts are the candidate descriptions CLIP compares the image against.
CATEGORIES = {
    "pothole": {
        "label": "Pothole / damaged road",
        "default_severity": 3,
        "prompts": [
            "a photo of a pothole in a road",
            "a photo of a damaged, cracked road surface with a hole",
            "a photo of broken asphalt on a road",
        ],
    },
    "broken_stairs": {
        "label": "Broken steps / damaged stairs",
        "default_severity": 4,
        "prompts": [
            "a photo of broken stairs",
            "a photo of damaged concrete steps with a missing or cracked step",
            "a photo of a staircase in disrepair",
        ],
    },
    "wet_floor": {
        "label": "Slippery / wet floor",
        "default_severity": 3,
        "prompts": [
            "a photo of a wet slippery floor",
            "a photo of water spilled on a corridor floor",
            "a photo of a puddle on an indoor floor with a wet floor sign",
        ],
    },
    "exposed_wire": {
        "label": "Exposed electrical wire",
        "default_severity": 5,
        "prompts": [
            "a photo of exposed electrical wires",
            "a photo of loose live cables hanging from a wall",
            "a photo of a damaged electrical outlet with bare wires",
        ],
    },
}

# Prompts describing images that are NOT one of the four hazards. They let the model
# "vote" for 'nothing relevant here' instead of being forced to pick a hazard.
NEGATIVE_PROMPTS = [
    "a photo of a clean, intact and safe corridor",
    "a photo of an undamaged road",
    "a photo of a person",
    "a photo of a selfie",
    "a photo of food on a table",
    "a photo of a document or a screenshot",
    "a photo of an animal",
    "a photo of a landscape or the sky",
]

# --------------------------------------------------------- CLIP decision rules
# UNTUNED heuristics. See README "Limitations": CLIP is weakest on thin / low-contrast
# hazards (wires, thin water films), and these cut-offs should be calibrated on a
# labelled campus photo set before any real use.
CLIP_MODEL_NAME = os.getenv("NEARMISS_CLIP_MODEL", "openai/clip-vit-base-patch32")
CLIP_OFFLINE = os.getenv("NEARMISS_OFFLINE", "0") == "1"
CLIP_LOGIT_SCALE = 100.0  # CLIP's usual learned temperature
MIN_TOP_SHARE = 0.45  # top class must hold at least this share of the softmax
MIN_MARGIN = 0.10  # ...and lead the runner-up by at least this much
MIN_COSINE = 0.18  # ...and have at least this raw image-text cosine similarity
BLUR_WARN_VARIANCE = 40.0  # Laplacian variance below this -> "may be blurry" warning
BLUR_REJECT_VARIANCE = 10.0  # below this -> too blurry to classify

# ------------------------------------------------------------- risk scoring
# score = 100 * (w_sev * severity_n + w_sim * similar_n + w_age * age_n), each n in [0,1]
_DEFAULT_WEIGHTS = {"severity": 0.50, "similar_reports": 0.30, "unresolved_age": 0.20}
SCORE_WEIGHTS = {**_DEFAULT_WEIGHTS, **json.loads(os.getenv("NEARMISS_WEIGHTS", "{}"))}
SIMILAR_CAP = 4  # this many other open related reports = full marks for that factor
AGE_CAP_DAYS = 14.0  # this many days unresolved = full marks for that factor
# Minimum score for each label (checked from the top). Illustrative.
PRIORITY_LEVELS = [("urgent", 70.0), ("high", 50.0), ("medium", 30.0), ("low", 0.0)]

STATUSES = ["open", "in_progress", "resolved"]
PRIORITY_OVERRIDES = ["low", "medium", "high", "urgent"]

# ------------------------------------------------------------ campus layout
# A SCHEMATIC layout (percent units on a 100x60 canvas). Not GPS, not to scale.
BUILDINGS = {
    "main_gate": {"label": "Main Gate", "x": 4, "y": 24, "w": 16, "h": 12},
    "block_a": {"label": "Block A", "x": 28, "y": 6, "w": 18, "h": 14},
    "block_b": {"label": "Block B", "x": 52, "y": 6, "w": 18, "h": 14},
    "block_c": {"label": "Block C", "x": 76, "y": 6, "w": 18, "h": 14},
    "science_lab": {"label": "Science Lab", "x": 76, "y": 26, "w": 18, "h": 14},
    "library": {"label": "Library", "x": 40, "y": 28, "w": 22, "h": 12},
    "cafeteria": {"label": "Cafeteria", "x": 28, "y": 44, "w": 18, "h": 11},
    "hostel": {"label": "Hostel", "x": 56, "y": 44, "w": 22, "h": 11},
}
