"""Brew router — optimization loop: recommend, record, repeat best.

Implements the core espresso optimization workflow:
  GET  /brew                         — Main brew page
  POST /brew/set-setup               — Set active brew setup (cookie)
  POST /brew/recommend               — Trigger BayBE recommendation
  GET  /brew/recommend/{rec_id}      — Display recommendation + rate form
  POST /brew/record                  — Record measurement (taste/failed)
  GET  /brew/best                    — Show highest-rated shot
  GET  /brew/manual                  — Manual brew entry form
  POST /brew/extend-ranges           — Extend bean parameter bounds
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
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean
from app.services.optimizer import (
    DEFAULT_BOUNDS,
    _resolve_bounds,
    _round_value,
)
from app.services.optimizer_key import make_campaign_key

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


def _get_active_setup(request: Request, db: Session) -> Optional[BrewSetup]:
    """Return active brew setup from cookie, or None if not set / retired / deleted."""
    setup_id = request.cookies.get("active_setup_id")
    if not setup_id:
        return None
    return (
        db.query(BrewSetup)
        .filter(BrewSetup.id == setup_id, BrewSetup.is_retired == False)  # noqa: E712
        .first()
    )


def _get_method_from_setup(setup: Optional[BrewSetup]) -> str:
    """Derive brew method name from the active setup. Defaults to 'espresso'."""
    if setup is None:
        return "espresso"
    if setup.brew_method is None:
        return "espresso"
    return setup.brew_method.name.lower()


def _get_campaign_key(bean: Bean, setup: Optional[BrewSetup]) -> str:
    """Build a campaign key from bean + active setup."""
    method = _get_method_from_setup(setup)
    setup_id = str(setup.id) if setup else None
    return make_campaign_key(str(bean.id), method, setup_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def brew_index(request: Request, db: Session = Depends(get_db)):
    """Main brew page — entry point for the optimization loop."""
    bean = _require_active_bean(request, db)
    active_setup = _get_active_setup(request, db)

    has_measurements = False
    beans = db.query(Bean).order_by(Bean.name).all()
    setups = (
        db.query(BrewSetup).filter(BrewSetup.is_retired == False).order_by(BrewSetup.name).all()  # noqa: E712
    )

    if bean:
        has_measurements = db.query(Measurement).filter(Measurement.bean_id == bean.id).count() > 0

    return templates.TemplateResponse(
        request,
        "brew/index.html",
        {
            "active_bean": bean,
            "active_setup": active_setup,
            "has_measurements": has_measurements,
            "beans": beans,
            "setups": setups,
        },
    )


@router.post("/set-setup", response_class=HTMLResponse)
async def set_active_setup(
    request: Request,
    setup_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Set the active brew setup (stored in cookie)."""
    setup = (
        db.query(BrewSetup)
        .filter(BrewSetup.id == setup_id, BrewSetup.is_retired == False)  # noqa: E712
        .first()
    )
    response = RedirectResponse(url="/brew", status_code=303)
    if setup:
        response.set_cookie(
            key="active_setup_id",
            value=str(setup.id),
            max_age=60 * 60 * 24 * 365,  # 1 year
            httponly=True,
            samesite="lax",
        )
    return response


@router.post("/recommend", response_class=HTMLResponse)
async def trigger_recommend(request: Request, db: Session = Depends(get_db)):
    """Generate a BayBE recommendation for the active bean."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    active_setup = _get_active_setup(request, db)
    campaign_key = _get_campaign_key(bean, active_setup)
    method = _get_method_from_setup(active_setup)

    optimizer = request.app.state.optimizer
    rec = await optimizer.recommend(campaign_key, overrides=bean.parameter_overrides, method=method)

    # Compute recommendation insights (explore vs exploit explanation + predicted taste)
    insights = optimizer.get_recommendation_insights(
        campaign_key, rec, overrides=bean.parameter_overrides, method=method
    )
    rec["insights"] = insights
    rec["method"] = method
    rec["setup_id"] = str(active_setup.id) if active_setup else None

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
    preinfusion_pct: Optional[float] = Form(None),
    dose_in: float = Form(...),
    target_yield: Optional[float] = Form(None),
    saturation: Optional[str] = Form(None),
    bloom_weight: Optional[float] = Form(None),
    brew_volume: Optional[float] = Form(None),
    method: str = Form("espresso"),
    brew_setup_id: Optional[str] = Form(None),
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
        bounds = _resolve_bounds(bean.parameter_overrides, method=method)
        if method == "pour-over":
            param_values = {
                "grind_setting": grind_setting,
                "temperature": temperature,
                "bloom_weight": bloom_weight or 40.0,
                "dose_in": dose_in,
                "brew_volume": brew_volume or 250.0,
            }
        else:
            param_values = {
                "grind_setting": grind_setting,
                "temperature": temperature,
                "preinfusion_pct": preinfusion_pct or 75.0,
                "dose_in": dose_in,
                "target_yield": target_yield or 40.0,
            }
        violations = []
        for param, value in param_values.items():
            if param not in bounds:
                continue
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
            preinfusion_pct=preinfusion_pct if method != "pour-over" else None,
            dose_in=dose_in,
            target_yield=target_yield if method != "pour-over" else None,
            saturation=saturation if method != "pour-over" else None,
            brew_setup_id=brew_setup_id if brew_setup_id else None,
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
        campaign_key = make_campaign_key(
            str(bean.id), method, brew_setup_id if brew_setup_id else None
        )
        if method == "pour-over":
            measurement_data = {
                "grind_setting": grind_setting,
                "temperature": temperature,
                "bloom_weight": bloom_weight or 40.0,
                "dose_in": dose_in,
                "brew_volume": brew_volume or 250.0,
                "taste": taste,
            }
        else:
            measurement_data = {
                "grind_setting": grind_setting,
                "temperature": temperature,
                "preinfusion_pct": preinfusion_pct or 75.0,
                "dose_in": dose_in,
                "target_yield": target_yield or 40.0,
                "saturation": saturation or "yes",
                "taste": taste,
            }
        optimizer.add_measurement(
            campaign_key, measurement_data, overrides=bean.parameter_overrides, method=method
        )

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

    active_setup = _get_active_setup(request, db)
    method = _get_method_from_setup(active_setup)
    bounds = _resolve_bounds(bean.parameter_overrides, method=method)
    best = _best_measurement(bean.id, db)

    # Pre-fill values: use best measurement if available, else midpoint of bounds
    if best and method == "pour-over":
        prefill = {
            "grind_setting": best.grind_setting,
            "temperature": best.temperature,
            "bloom_weight": 40.0,  # pour-over params not stored on old measurements
            "dose_in": best.dose_in,
            "brew_volume": 250.0,
        }
    elif best:
        prefill = {
            "grind_setting": best.grind_setting,
            "temperature": best.temperature,
            "preinfusion_pct": best.preinfusion_pct,
            "dose_in": best.dose_in,
            "target_yield": best.target_yield,
            "saturation": best.saturation,
        }
    elif method == "pour-over":
        prefill = {
            param: _round_value((lo + hi) / 2, step)
            for (param, (lo, hi)), step in zip(
                bounds.items(),
                [0.5, 1.0, 1.0, 0.5, 5.0],  # grind, temp, bloom, dose, volume
            )
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
    setup_id = str(active_setup.id) if active_setup else None

    return templates.TemplateResponse(
        request,
        "brew/manual.html",
        {
            "active_bean": bean,
            "active_setup": active_setup,
            "method": method,
            "setup_id": setup_id,
            "bounds": bounds,
            "prefill": prefill,
            "manual_session_id": manual_session_id,
        },
    )


@router.post("/extend-ranges")
async def extend_ranges(
    request: Request,
    db: Session = Depends(get_db),
):
    """Extend bean parameter ranges when manual input exceeds current bounds."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    form = await request.form()
    overrides = dict(bean.parameter_overrides or {})

    for param in DEFAULT_BOUNDS:
        new_min = form.get(f"{param}_min")
        new_max = form.get(f"{param}_max")
        if new_min is not None or new_max is not None:
            current = overrides.get(param, {})
            if new_min is not None:
                current["min"] = float(new_min)
            if new_max is not None:
                current["max"] = float(new_max)
            overrides[param] = current

    bean.parameter_overrides = overrides
    db.commit()

    return JSONResponse(content={"status": "ok"})
