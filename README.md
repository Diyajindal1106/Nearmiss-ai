# NearMiss AI — Detect Danger Before Disaster

> “Don’t wait for an accident to fix a problem.”

AI-assisted hazard reporting and risk prioritisation for campuses. **Early-stage ideation prototype** (Code Alpha Ideathon). It has *not* been validated with real users and has *not* been shown to prevent accidents.

Flow: **Upload image → CLIP suggestion → human confirms → risk score → similar-report grouping → admin review → resolution tracking.**

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, plain CSS, lucide-react, react-router |
| Backend | Python, FastAPI, Pydantic, SQLite (stdlib `sqlite3`) |
| AI | Pretrained **CLIP** (`openai/clip-vit-base-patch32`) via Hugging Face Transformers, CPU inference, no API key |

## Status of verification (read this first)

This project was written in a sandbox that blocked PyPI, npm and Hugging Face. What was and wasn't run:

| Item | Status |
|---|---|
| Scoring, grouping, repository (create/update/stats/seed), upload validation, CLIP decision rules | **Tested**: 44 unit tests pass (run with a small pytest stand-in; they are standard pytest files) |
| React UI | **Run in Chromium** against a stand-in server that reused the real backend modules: landing, dashboard, search/empty states, form validation, upload, submit, detail, admin save, resolve-needs-notes rule, map, mobile width. Lucide icons and react-router were stubbed in that run. |
| `app/main.py` (FastAPI routes), `tests/test_api.py` | **Written but never executed** (FastAPI not installable there). Expect to fix small issues on first run. |
| Real CLIP inference, model download, `test_clip_integration.py` | **Not run.** The model-unavailable path *was* exercised and returns an honest "AI analysis unavailable". CLIP code and thresholds are untested/untuned. |
| `npm install`, `vite build` | **Not run.** |

## Setup

Requirements: Python 3.10+, Node 18+, ~1.5 GB free disk (PyTorch CPU + model), internet for the first model download (~600 MB).

### macOS / Linux
```bash
cd nearmiss-ai/backend
python3 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only build
pip install -r requirements.txt
python -m app.seed            # creates data/nearmiss.db with labelled demo reports
uvicorn app.main:app --reload --port 8000
```
Second terminal:
```bash
cd nearmiss-ai/frontend
npm install
npm run dev                   # http://localhost:5173
```

### Windows PowerShell
```powershell
cd nearmiss-ai\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```
Second PowerShell window:
```powershell
cd nearmiss-ai\frontend
npm install
npm run dev
```

API docs (Swagger): http://localhost:8000/docs · Tests: `cd backend && pytest -q`

### Model download and CPU inference
The first image analysis downloads CLIP weights to the Hugging Face cache (`~/.cache/huggingface`). That first request can take minutes; later ones take roughly a second or two on a laptop CPU. To pre-download: `python -c "from transformers import CLIPModel, CLIPProcessor as P; n='openai/clip-vit-base-patch32'; CLIPModel.from_pretrained(n); P.from_pretrained(n)"`. To warm the model at startup set `NEARMISS_PRELOAD=1`; to forbid network use after downloading set `NEARMISS_OFFLINE=1`. Override the model with `NEARMISS_CLIP_MODEL`.

Environment variables (all optional, no secrets): `NEARMISS_DB`, `NEARMISS_UPLOADS`, `NEARMISS_CORS`, `NEARMISS_WEIGHTS` (JSON, e.g. `{"severity":0.6,"similar_reports":0.2,"unresolved_age":0.2}`), `NEARMISS_CLIP_MODEL`, `NEARMISS_OFFLINE`, `NEARMISS_PRELOAD`. Reset demo data: `python -m app.seed --reset`.

## How it works

**AI suggestion (`app/classifier.py`).** CLIP embeds the image and three text prompts per hazard (plus “not a hazard” prompts such as people, food, clean corridors). Per-class cosine similarity is the mean over prompts. The UI shows the raw **cosine similarity** and a **relative share** (softmax over the candidates only, **not a calibrated probability**). The result is `uncertain` ("Uncertain — manual review required") when the top class is "not a hazard", the share, margin or absolute similarity is below threshold, or the image is too blurry. If the model fails to load or run, the status is `unavailable` and the user picks a category manually; fallback output is never presented as AI output. The reporter must click *Confirm suggestion* or choose a category; provenance (confirmed / overridden / manual / admin-changed) is stored. The server keeps the analysis itself, so a client cannot forge AI results.

**Known limitations.** CLIP is zero-shot and generic: thin or low-contrast hazards (exposed wires, thin water films, shallow cracks) are harder than potholes or stairs. Thresholds in `config.py` are untuned guesses and should be calibrated on a labelled photo set. CLIP can be wrong with confidence.

**Priority score (`app/scoring.py`).** `score = 100 × (0.50·severity + 0.30·similar + 0.20·age)`, each factor normalised to 0–1: severity (1–5 → 0–1; category defaults are illustrative, admin-adjustable), other *open* linked reports (cap 4), days unresolved (cap 14). Levels: ≥70 Urgent, ≥50 High, ≥30 Medium, else Low. All weights/caps/thresholds are illustrative defaults in `config.py`. The detail page shows the exact breakdown. Admins may override the level (shown with ✎). It is a triage aid, not an accident prediction.

**Grouping (`app/grouping.py`).** Deterministic rule: same building/block + same confirmed category. Description word-overlap and location-detail overlap are shown as evidence only. Nothing is merged or deleted. This is not machine-learning clustering.

**Campus map.** A schematic layout (coordinates in `config.BUILDINGS`), not GPS, not to scale.

**Security notes.** Upload type, size (5 MB), dimensions and real image content are validated; files are stored under random names and served only if the name matches that pattern. **There is no authentication**: anyone who can open the admin page can edit. Add login before any real use.

## Troubleshooting
- **`Cannot reach the backend` in the UI** → backend not running on port 8000, or you changed the port (update `frontend/vite.config.js`).
- **Analysis says “AI analysis unavailable … No module named 'torch'”** → install PyTorch (command above) in the same venv you run uvicorn from.
- **`OSError … couldn't connect to huggingface.co`** → needs internet on first run (or a pre-populated cache plus `NEARMISS_OFFLINE=1`).
- **Out-of-memory / slow** → close other apps; CLIP-B/32 needs ~1 GB RAM. Everything runs on CPU.
- **Windows: `torch` install fails** → use 64-bit Python 3.10–3.12 and the CPU index URL above.
- **Port 5173 in use** → Vite picks another port; add it to `NEARMISS_CORS` if you bypass the proxy.
- **`Activate.ps1` blocked** → `Set-ExecutionPolicy -Scope Process Bypass`.

## Live demo script (≈4 min)
1. **Landing** – tagline, problem, four steps. State up front: “prototype, sample data, not validated.”
2. **Dashboard** – point out the *Sample data* labels and that every number is computed. Show the Block B group of 3 linked reports and the ranking.
3. **Report a hazard** – upload a real photo (e.g. a stair or wet floor). Show the CLIP table, the “human verification required” notice and the similarity-vs-share note. Confirm or change the category; submit.
4. **New report page** – score breakdown and the linked related reports; the dashboard count has increased.
5. **Uncertain path** – upload a selfie/screenshot to show “Uncertain — manual review required.”
6. **Admin review** – assign a team, set status In progress, override priority, try Resolved without notes (blocked), add notes, save; show the status history.
7. **Campus map** – click a block; schematic, not GPS.
8. **Close honestly** – what’s next: pilot with facilities staff, calibrate thresholds on real photos, add login, validate weights.
