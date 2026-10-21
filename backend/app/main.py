"""NearMiss AI - FastAPI application.  Run:  uvicorn app.main:app --reload --port 8000"""
import logging
import os
import threading

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from . import config, db, repository, uploads
from .classifier import DISCLAIMER, SCORE_NOTE, classifier
from .schemas import ReportCreate, ReportUpdate

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NearMiss AI API",
    version="0.1.0",
    description=(
        "Early-stage prototype. AI output is a suggestion requiring human verification; "
        "risk scores are a prioritisation aid, not a prediction of accidents."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if os.getenv("NEARMISS_PRELOAD") == "1":  # optional: warm the model in the background
        threading.Thread(target=lambda: _safe_load(), daemon=True).start()


def _safe_load() -> None:
    try:
        classifier.load()
    except Exception:  # noqa: BLE001 - status endpoint reports the error
        pass


@app.exception_handler(repository.NotFound)
async def _nf(_, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(repository.RuleViolation)
async def _rv(_, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(uploads.UploadError)
async def _ue(_, exc):
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


# --------------------------------------------------------------------- meta
@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "ai_model": classifier.status()}


@app.get("/api/config", tags=["meta"])
def get_config():
    return {
        "categories": {k: {"label": v["label"], "default_severity": v["default_severity"]}
                       for k, v in config.CATEGORIES.items()},
        "buildings": config.BUILDINGS,
        "statuses": config.STATUSES,
        "priority_levels": [{"key": k, "min_score": m} for k, m in config.PRIORITY_LEVELS],
        "priority_overrides": config.PRIORITY_OVERRIDES,
        "scoring": {
            "weights": config.SCORE_WEIGHTS,
            "similar_cap": config.SIMILAR_CAP,
            "age_cap_days": config.AGE_CAP_DAYS,
            "note": "Illustrative defaults; a prioritisation aid, not an accident prediction.",
        },
        "upload": {"max_bytes": config.MAX_UPLOAD_BYTES, "types": list(config.ALLOWED_MIME)},
    }


# ----------------------------------------------------------- image analysis
@app.post("/api/analyze", tags=["ai"])
async def analyze_image(file: UploadFile = File(...)):
    """Validate + store the image, run real CLIP inference, return suggestion + scores.

    If the model is unavailable the image is still stored and status="unavailable" is
    returned so the user can classify manually. Fallback is never presented as AI output.
    """
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    ext, img = uploads.validate_image(data, file.content_type)  # raises UploadError
    result = await run_in_threadpool(classifier.analyze, img)
    filename = uploads.save_image(data, ext)
    upload_id = filename.rsplit(".", 1)[0]
    result = {**result, "disclaimer": DISCLAIMER, "score_note": SCORE_NOTE}
    import json as _json
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO analyses(id, image_filename, result, created_at) VALUES (?,?,?,?)",
            (upload_id, filename, _json.dumps(result), db.now_iso()),
        )
    return {**result, "upload_id": upload_id, "image_url": f"/api/images/{filename}"}


@app.get("/api/images/{filename}", tags=["ai"])
def get_image(filename: str):
    path = uploads.resolve_image_path(filename)
    if not path:
        raise HTTPException(404, "Image not found")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})


# ------------------------------------------------------------------ reports
@app.post("/api/reports", status_code=201, tags=["reports"])
def create_report(body: ReportCreate):
    with db.connect() as conn:
        return repository.create_report(conn, body.model_dump())


@app.get("/api/reports", tags=["reports"])
def list_reports(
    search: str | None = None,
    status: str | None = Query(None, pattern="^(open|in_progress|resolved)$"),
    category: str | None = None,
    priority: str | None = Query(None, pattern="^(low|medium|high|urgent)$"),
    building: str | None = None,
    sort: str = Query("priority", pattern="^(priority|newest|oldest|severity)$"),
):
    with db.connect() as conn:
        return repository.list_reports(conn, search, status, category, priority, building, sort)


@app.get("/api/reports/{report_id}", tags=["reports"])
def report_detail(report_id: int):
    with db.connect() as conn:
        return repository.get_report(conn, report_id)


@app.patch("/api/reports/{report_id}", tags=["reports"])
def update_report(report_id: int, body: ReportUpdate):
    with db.connect() as conn:
        return repository.update_report(conn, report_id, body.model_dump(exclude_unset=True))


# ---------------------------------------------------------------- dashboard
@app.get("/api/stats", tags=["dashboard"])
def dashboard_stats():
    with db.connect() as conn:
        return repository.stats(conn)
