"""Brew router — optimization loop: recommend, record, repeat best.

Implements the core espresso optimization workflow:
  GET  /brew                         — Main brew page
  POST /brew/recommend               — Trigger BayBE recommendation
  GET  /brew/recommend/{rec_id}      — Display recommendation + rate form
  POST /brew/record                  — Record measurement (taste/failed)
  GET  /brew/best                    — Show highest-rated shot
  GET  /brew/manual                  — Manual brew entry form
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean
from app.services.optimizer import _resolve_bounds, _round_value

router = APIRouter(prefix="/brew", tags=["brew"])
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PENDING_FILE = "pending_recommendations.json"


def _pending_path(data_dir: Path) -> Path:
    """Return path to the pending recommendations JSON file."""
    return data_dir / _PENDING_FILE


def _save_pending(data_dir: Path, rec_id: str, rec: dict) -> None:
    """Persist a pending recommendation to disk."""
    path = _pending_path(data_dir)
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}
    data[rec_id] = rec
    path.write_text(json.dumps(data))


def _load_pending(data_dir: Path, rec_id: str) -> Optional[dict]:
    """Load a single pending recommendation from disk, or None if not found."""
    path = _pending_path(data_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get(rec_id)
    except (json.JSONDecodeError, OSError):
        return None


def _remove_pending(data_dir: Path, rec_id: str) -> None:
    """Remove a pending recommendation from disk."""
    path = _pending_path(data_dir)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        data.pop(rec_id, None)
        path.write_text(json.dumps(data))
    except (json.JSONDecodeError, OSError):
        pass


def _require_active_bean(request: Request, db: Session) -> Optional[Bean]:
    """Return active bean or None (caller should redirect)."""
    return _get_active_bean(request, db)


def _best_measurement(bean_id: str, db: Session) -> Optional[Measurement]:
    """Return highest-taste measurement for a bean (excluding failed shots)."""
    return (
        db.query(Measurement)
        .filter(
            Measurement.bean_id == bean_id,
            Measurement.is_failed == False,  # noqa: E712
        )
        .order_by(Measurement.taste.desc())
        .first()
    )


def _brew_ratio(dose_in: float, target_yield: float) -> str:
    """Return dose:yield ratio string, e.g. '1:2.1'."""
    if dose_in and dose_in > 0:
        ratio = target_yield / dose_in
        return f"1:{ratio:.1f}"
    return "—"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def brew_index(request: Request, db: Session = Depends(get_db)):
    """Main brew page — entry point for the optimization loop."""
    bean = _require_active_bean(request, db)
    if not bean:
        return templates.TemplateResponse(
            request,
            "brew/index.html",
            {"no_active_bean": True},
        )

    has_measurements = db.query(Measurement).filter(Measurement.bean_id == bean.id).count() > 0
    beans = db.query(Bean).order_by(Bean.name).all()

    return templates.TemplateResponse(
        request,
        "brew/index.html",
        {"active_bean": bean, "has_measurements": has_measurements, "beans": beans},
    )


@router.post("/recommend", response_class=HTMLResponse)
async def trigger_recommend(request: Request, db: Session = Depends(get_db)):
    """Generate a BayBE recommendation for the active bean."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    optimizer = request.app.state.optimizer
    rec = await optimizer.recommend(bean.id, overrides=bean.parameter_overrides)

    # Compute recommendation insights (explore vs exploit explanation + predicted taste)
    insights = optimizer.get_recommendation_insights(
        bean.id, rec, overrides=bean.parameter_overrides
    )
    rec["insights"] = insights

    # Store recommendation to disk (survives server restarts)
    rec_id = rec["recommendation_id"]
    _save_pending(settings.data_dir, rec_id, rec)

    return RedirectResponse(url=f"/brew/recommend/{rec_id}", status_code=303)


@router.get("/recommend/{recommendation_id}", response_class=HTMLResponse)
async def show_recommendation(
    request: Request,
    recommendation_id: str,
    db: Session = Depends(get_db),
):
    """Display a recommendation with large params + rate form."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    pending = getattr(request.app.state, "pending_recommendations", {})
    rec = pending.get(recommendation_id)

    if not rec:
        # Try file-based store (survives server restarts; also covers cold start)
        rec = _load_pending(settings.data_dir, recommendation_id)

    if not rec:
        # Recommendation not found or invalid ID → back to brew
        return RedirectResponse(url="/brew", status_code=303)

    ratio = _brew_ratio(rec.get("dose_in", 0), rec.get("target_yield", 0))
    insights = rec.get("insights", {})

    return templates.TemplateResponse(
        request,
        "brew/recommend.html",
        {
            "active_bean": bean,
            "rec": rec,
            "recommendation_id": recommendation_id,
            "ratio": ratio,
            "insights": insights,
        },
    )


@router.post("/record", response_class=HTMLResponse)
async def record_measurement(
    request: Request,
    recommendation_id: str = Form(...),
    grind_setting: float = Form(...),
    temperature: float = Form(...),
    preinfusion_pct: float = Form(...),
    dose_in: float = Form(...),
    target_yield: float = Form(...),
    saturation: str = Form(...),
    taste: float = Form(7.0),
    extraction_time: Optional[float] = Form(None),
    is_failed: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    acidity: Optional[float] = Form(None),
    sweetness: Optional[float] = Form(None),
    body: Optional[float] = Form(None),
    bitterness: Optional[float] = Form(None),
    aroma: Optional[float] = Form(None),
    intensity: Optional[float] = Form(None),
    flavor_tags: Optional[str] = Form(None),
    is_manual: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Record a measurement — saves to SQLite and BayBE campaign."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    # Validate manual brews against bean parameter bounds
    if is_manual == "true":
        bounds = _resolve_bounds(bean.parameter_overrides)
        param_values = {
            "grind_setting": grind_setting,
            "temperature": temperature,
            "preinfusion_pct": preinfusion_pct,
            "dose_in": dose_in,
            "target_yield": target_yield,
        }
        violations = []
        for param, value in param_values.items():
            lo, hi = bounds[param]
            if value < lo or value > hi:
                violations.append({"param": param, "value": value, "min": lo, "max": hi})
        if violations:
            return JSONResponse(
                status_code=422,
                content={"error": "Parameters out of range", "violations": violations},
            )

    # Auto-set taste to 1 for failed shots (choked / gusher)
    failed = is_failed == "true" or is_failed == "1" or is_failed == "on"
    if failed:
        taste = 1.0

    # Clamp taste to valid range
    taste = max(1.0, min(10.0, taste))

    # Clamp flavor dimensions to 1-5 if provided
    def _clamp_flavor(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        return max(1.0, min(5.0, val))

    # Convert comma-separated flavor_tags string to JSON list
    flavor_tags_json = None
    if flavor_tags:
        tags = [t.strip() for t in flavor_tags.split(",") if t.strip()][:10]
        if tags:
            flavor_tags_json = json.dumps(tags)

    # Deduplication: skip if recommendation_id already recorded
    existing = (
        db.query(Measurement).filter(Measurement.recommendation_id == recommendation_id).first()
    )
    if not existing:
        measurement = Measurement(
            bean_id=bean.id,
            recommendation_id=recommendation_id,
            grind_setting=grind_setting,
            temperature=temperature,
            preinfusion_pct=preinfusion_pct,
            dose_in=dose_in,
            target_yield=target_yield,
            saturation=saturation,
            taste=taste,
            extraction_time=extraction_time if extraction_time else None,
            is_failed=failed,
            is_manual=(is_manual == "true"),
            notes=notes.strip() if notes else None,
            acidity=_clamp_flavor(acidity),
            sweetness=_clamp_flavor(sweetness),
            body=_clamp_flavor(body),
            bitterness=_clamp_flavor(bitterness),
            aroma=_clamp_flavor(aroma),
            intensity=_clamp_flavor(intensity),
            flavor_tags=flavor_tags_json,
        )
        db.add(measurement)
        db.commit()

        # Also add to BayBE campaign
        optimizer = request.app.state.optimizer
        measurement_data = {
            "grind_setting": grind_setting,
            "temperature": temperature,
            "preinfusion_pct": preinfusion_pct,
            "dose_in": dose_in,
            "target_yield": target_yield,
            "saturation": saturation,
            "taste": taste,
        }
        optimizer.add_measurement(bean.id, measurement_data, overrides=bean.parameter_overrides)

    # Clean up pending recommendation (from both in-memory and file store)
    pending = getattr(request.app.state, "pending_recommendations", {})
    pending.pop(recommendation_id, None)
    _remove_pending(settings.data_dir, recommendation_id)

    return RedirectResponse(url="/brew", status_code=303)


@router.get("/best", response_class=HTMLResponse)
async def show_best(request: Request, db: Session = Depends(get_db)):
    """Show the best recipe (highest taste score) for the active bean."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    best = _best_measurement(bean.id, db)

    ratio = None
    best_session_id = None
    if best:
        ratio = _brew_ratio(best.dose_in, best.target_yield)
        best_session_id = str(uuid.uuid4())

    return templates.TemplateResponse(
        request,
        "brew/best.html",
        {
            "active_bean": bean,
            "best": best,
            "ratio": ratio,
            "best_session_id": best_session_id,
        },
    )


@router.get("/manual", response_class=HTMLResponse)
async def manual_brew(request: Request, db: Session = Depends(get_db)):
    """Manual brew entry form — pre-filled from best measurement or midpoint."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bounds = _resolve_bounds(bean.parameter_overrides)
    best = _best_measurement(bean.id, db)

    # Pre-fill values: use best measurement if available, else midpoint of bounds
    if best:
        prefill = {
            "grind_setting": best.grind_setting,
            "temperature": best.temperature,
            "preinfusion_pct": best.preinfusion_pct,
            "dose_in": best.dose_in,
            "target_yield": best.target_yield,
            "saturation": best.saturation,
        }
    else:
        prefill = {
            param: _round_value((lo + hi) / 2, step)
            for (param, (lo, hi)), step in zip(
                bounds.items(),
                [
                    0.5,  # grind_setting
                    1.0,  # temperature
                    5.0,  # preinfusion_pct
                    0.5,  # dose_in
                    1.0,  # target_yield
                ],
            )
        }
        prefill["saturation"] = "yes"

    manual_session_id = str(uuid.uuid4())

    return templates.TemplateResponse(
        request,
        "brew/manual.html",
        {
            "active_bean": bean,
            "bounds": bounds,
            "prefill": prefill,
            "manual_session_id": manual_session_id,
        },
    )
