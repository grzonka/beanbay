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
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.models.pending_recommendation import PendingRecommendation
from app.routers.beans import _get_active_bean
from app.services.optimizer import (
    _resolve_bounds,
    _round_value,
)
from app.services.parameter_registry import (
    PARAMETER_REGISTRY,
    get_default_bounds,
    get_param_columns,
)
from app.services.optimizer_key import make_campaign_key

router = APIRouter(prefix="/brew", tags=["brew"])
templates = Jinja2Templates(directory="app/templates")

# All measurement columns that can be set from form data, keyed by param name.
# This covers core params + all method-specific params across Phases 20 and 21.
_MEASUREMENT_FLOAT_COLUMNS = {
    "grind_setting",
    "temperature",
    "dose_in",
    "target_yield",
    "preinfusion_pressure_pct",
    "preinfusion_time",
    "preinfusion_pressure",
    "brew_pressure",
    "bloom_pause",
    "flow_rate",
    "bloom_weight",
    "brew_volume",
    "steep_time",
}
_MEASUREMENT_STR_COLUMNS = {
    "saturation",
    "pressure_profile",
    "temp_profile",
    "brew_mode",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_pending(db: Session, rec_id: str, rec: dict) -> None:
    """Persist a pending recommendation to the DB."""
    existing = db.query(PendingRecommendation).filter_by(recommendation_id=rec_id).first()
    if existing is None:
        db.add(PendingRecommendation(recommendation_id=rec_id, recommendation_data=rec))
        db.commit()


def _load_pending(db: Session, rec_id: str) -> Optional[dict]:
    """Load a single pending recommendation from the DB, or None if not found."""
    row = db.query(PendingRecommendation).filter_by(recommendation_id=rec_id).first()
    return row.recommendation_data if row is not None else None


def _remove_pending(db: Session, rec_id: str) -> None:
    """Remove a pending recommendation from the DB."""
    db.query(PendingRecommendation).filter_by(recommendation_id=rec_id).delete()
    db.commit()


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


def _extract_params_from_form(method: str, form_data: dict) -> dict:
    """Extract all parameter values from raw form data for the given method.

    Returns a dict of {param_name: value} for all known measurement columns
    that appear in the form data. Handles both float and string params.
    Includes legacy params (preinfusion_pressure_pct, saturation) for backward compat
    with old campaigns that still have them in their searchspace.
    """
    result = {}
    for col in _MEASUREMENT_FLOAT_COLUMNS:
        val = form_data.get(col)
        if val is not None and val != "":
            try:
                result[col] = float(val)
            except (ValueError, TypeError):
                pass
    for col in _MEASUREMENT_STR_COLUMNS:
        val = form_data.get(col)
        if val is not None and val != "":
            result[col] = str(val)
    return result


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
    brewer = active_setup.brewer if active_setup else None

    optimizer = request.app.state.optimizer

    # Check if campaign param set is outdated (brewer capabilities changed)
    if optimizer.is_campaign_outdated(campaign_key, method, brewer):
        if not optimizer.was_rebuild_declined(campaign_key):
            return RedirectResponse(
                url=f"/brew/campaign-outdated?campaign_key={campaign_key}&method={method}",
                status_code=303,
            )

    rec = await optimizer.recommend(
        campaign_key,
        overrides=bean.parameter_overrides,
        method=method,
        target_bean=bean,
        db=db,
        brewer=brewer,
    )

    # Compute recommendation insights (explore vs exploit explanation + predicted taste)
    insights = optimizer.get_recommendation_insights(
        campaign_key, rec, overrides=bean.parameter_overrides, method=method, brewer=brewer
    )
    rec["insights"] = insights
    rec["method"] = method
    rec["setup_id"] = str(active_setup.id) if active_setup else None

    # Retrieve transfer metadata (set on first campaign creation if transfer learning applied)
    transfer_metadata = optimizer.get_transfer_metadata(campaign_key)
    rec["transfer_metadata"] = transfer_metadata

    # Store recommendation to DB (survives server restarts)
    rec_id = rec["recommendation_id"]
    _save_pending(db, rec_id, rec)

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

    rec = _load_pending(db, recommendation_id)

    if not rec:
        # Recommendation not found or invalid ID → back to brew
        return RedirectResponse(url="/brew", status_code=303)

    method = rec.get("method", "espresso")
    ratio = _brew_ratio(rec.get("dose_in", 0), rec.get("target_yield", 0))
    insights = rec.get("insights", {})
    transfer_metadata = rec.get("transfer_metadata")

    # Pass param_defs for generic hidden input rendering in template
    param_defs = PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])

    return templates.TemplateResponse(
        request,
        "brew/recommend.html",
        {
            "active_bean": bean,
            "rec": rec,
            "recommendation_id": recommendation_id,
            "ratio": ratio,
            "insights": insights,
            "transfer_metadata": transfer_metadata,
            "param_defs": param_defs,
            "method": method,
        },
    )


@router.post("/record", response_class=HTMLResponse)
async def record_measurement(
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a measurement — saves to SQLite and BayBE campaign.

    Reads all form data generically so it works for all 7 brew methods.
    The set of recognized param columns covers core + all method-specific params.
    """
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    form = await request.form()
    form_data = dict(form)

    recommendation_id = form_data.get("recommendation_id", "")
    method = str(form_data.get("method", "espresso"))
    brew_setup_id = form_data.get("brew_setup_id") or None
    is_manual = form_data.get("is_manual") == "true"
    is_failed_raw = form_data.get("is_failed", "")
    failed = is_failed_raw in ("true", "1", "on")

    # Extract all recognized param values from form
    params = _extract_params_from_form(method, form_data)

    # Validate manual brews against bean parameter bounds
    if is_manual:
        bounds = _resolve_bounds(bean.parameter_overrides, method=method)
        violations = []
        for param, value in params.items():
            if param not in bounds:
                continue
            if isinstance(value, str):
                continue  # skip categorical params
            lo, hi = bounds[param]
            if value < lo or value > hi:
                violations.append({"param": param, "value": value, "min": lo, "max": hi})
        if violations:
            return JSONResponse(
                status_code=422,
                content={"error": "Parameters out of range", "violations": violations},
            )

    # Taste
    try:
        taste = float(form_data.get("taste", 7.0))
    except (ValueError, TypeError):
        taste = 7.0
    if failed:
        taste = 1.0
    taste = max(1.0, min(10.0, taste))

    # Clamp flavor dimensions to 1-5 if provided
    def _clamp_flavor(key: str) -> Optional[float]:
        val = form_data.get(key)
        if val is None or val == "":
            return None
        try:
            return max(1.0, min(5.0, float(val)))
        except (ValueError, TypeError):
            return None

    # Extraction time
    try:
        extraction_time_raw = form_data.get("extraction_time")
        extraction_time = float(extraction_time_raw) if extraction_time_raw else None
    except (ValueError, TypeError):
        extraction_time = None

    # Convert comma-separated flavor_tags string to JSON list
    flavor_tags_json = None
    flavor_tags = form_data.get("flavor_tags")
    if flavor_tags:
        tags = [t.strip() for t in str(flavor_tags).split(",") if t.strip()][:10]
        if tags:
            flavor_tags_json = json.dumps(tags)

    notes_raw = form_data.get("notes")
    notes = notes_raw.strip() if notes_raw else None

    # Deduplication: skip if recommendation_id already recorded
    existing = (
        db.query(Measurement).filter(Measurement.recommendation_id == recommendation_id).first()
    )
    if not existing:
        measurement = Measurement(
            bean_id=bean.id,
            recommendation_id=recommendation_id,
            # Core params (always present for any method)
            grind_setting=params.get("grind_setting", 0.0),
            # temperature is nullable: cold-brew has no heated water
            temperature=params.get("temperature"),
            dose_in=params.get("dose_in", 0.0),
            # Espresso params
            target_yield=params.get("target_yield"),
            preinfusion_pressure_pct=params.get("preinfusion_pressure_pct"),
            saturation=params.get("saturation"),
            preinfusion_time=params.get("preinfusion_time"),
            preinfusion_pressure=params.get("preinfusion_pressure"),
            brew_pressure=params.get("brew_pressure"),
            pressure_profile=params.get("pressure_profile"),
            bloom_pause=params.get("bloom_pause"),
            flow_rate=params.get("flow_rate"),
            temp_profile=params.get("temp_profile"),
            brew_mode=params.get("brew_mode"),
            # New method params (Phase 21)
            steep_time=params.get("steep_time"),
            brew_volume=params.get("brew_volume"),
            bloom_weight=params.get("bloom_weight"),
            # Metadata
            brew_setup_id=brew_setup_id,
            taste=taste,
            extraction_time=extraction_time,
            is_failed=failed,
            is_manual=is_manual,
            notes=notes,
            acidity=_clamp_flavor("acidity"),
            sweetness=_clamp_flavor("sweetness"),
            body=_clamp_flavor("body"),
            bitterness=_clamp_flavor("bitterness"),
            aroma=_clamp_flavor("aroma"),
            intensity=_clamp_flavor("intensity"),
            flavor_tags=flavor_tags_json,
        )
        db.add(measurement)
        db.commit()

        # Also add to BayBE campaign — pass all extracted params; add_measurement filters
        # to the campaign's actual searchspace columns.
        optimizer = request.app.state.optimizer
        campaign_key = make_campaign_key(str(bean.id), method, brew_setup_id)
        active_setup_for_record = _get_active_setup(request, db)
        brewer_for_record = active_setup_for_record.brewer if active_setup_for_record else None
        measurement_data = dict(params)
        measurement_data["taste"] = taste
        optimizer.add_measurement(
            campaign_key,
            measurement_data,
            overrides=bean.parameter_overrides,
            method=method,
            target_bean_id=str(bean.id),
            brewer=brewer_for_record,
        )

    # Clean up pending recommendation from DB
    _remove_pending(db, recommendation_id)

    return RedirectResponse(url="/brew", status_code=303)


@router.get("/best", response_class=HTMLResponse)
async def show_best(request: Request, db: Session = Depends(get_db)):
    """Show the best recipe (highest taste score) for the active bean."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    active_setup = _get_active_setup(request, db)
    method = _get_method_from_setup(active_setup)
    brewer = active_setup.brewer if active_setup else None

    best = _best_measurement(bean.id, db)

    ratio = None
    best_session_id = None
    if best:
        ratio = _brew_ratio(best.dose_in, best.target_yield)
        best_session_id = str(uuid.uuid4())

    # Get param_defs filtered by brewer capabilities for dynamic hidden input rendering
    from app.services.parameter_registry import get_param_columns

    active_param_names = get_param_columns(method, brewer)
    param_defs = [
        pdef
        for pdef in PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])
        if pdef["name"] in active_param_names
    ]

    return templates.TemplateResponse(
        request,
        "brew/best.html",
        {
            "active_bean": bean,
            "best": best,
            "ratio": ratio,
            "best_session_id": best_session_id,
            "param_defs": param_defs,
            "method": method,
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
    brewer = active_setup.brewer if active_setup else None
    bounds = _resolve_bounds(bean.parameter_overrides, method=method)
    best = _best_measurement(bean.id, db)

    # Get the active param columns for this method+brewer combo
    active_param_names = get_param_columns(method, brewer)
    # Full param_defs (for the template to render correct input types, steps, units)
    param_defs = [
        pdef
        for pdef in PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])
        if pdef["name"] in active_param_names
    ]

    # Pre-fill values: use best measurement if available, else midpoint of bounds
    prefill: dict = {}
    if best:
        # Pull values from the best measurement for all active params
        for pdef in param_defs:
            name = pdef["name"]
            val = getattr(best, name, None)
            if val is not None:
                prefill[name] = val
        # Fill any missing active params with midpoints
        for pdef in param_defs:
            name = pdef["name"]
            if name not in prefill:
                if pdef["type"] == "continuous" and name in bounds:
                    lo, hi = bounds[name]
                    step = pdef.get("rounding") or 1.0
                    prefill[name] = _round_value((lo + hi) / 2, step)
                elif pdef["type"] == "categorical":
                    prefill[name] = pdef["values"][0]
    else:
        # No best measurement — use midpoints
        for pdef in param_defs:
            name = pdef["name"]
            if pdef["type"] == "continuous" and name in bounds:
                lo, hi = bounds[name]
                step = pdef.get("rounding") or 1.0
                prefill[name] = _round_value((lo + hi) / 2, step)
            elif pdef["type"] == "categorical":
                prefill[name] = pdef["values"][0]

    manual_session_id = str(uuid.uuid4())
    setup_id = str(active_setup.id) if active_setup else None

    return templates.TemplateResponse(
        request,
        "brew/manual.html",
        {
            "active_bean": bean,
            "active_setup": active_setup,
            "brewer": brewer,
            "method": method,
            "setup_id": setup_id,
            "bounds": bounds,
            "prefill": prefill,
            "manual_session_id": manual_session_id,
            "param_defs": param_defs,
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

    active_setup = _get_active_setup(request, db)
    method = _get_method_from_setup(active_setup)

    form = await request.form()
    overrides = dict(bean.parameter_overrides or {})

    # Extend any param whose min/max appears in the form, for the current method
    for param in get_default_bounds(method):
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


@router.get("/campaign-outdated", response_class=HTMLResponse)
async def show_campaign_outdated(
    request: Request,
    campaign_key: str,
    method: str = "espresso",
    db: Session = Depends(get_db),
):
    """Show the campaign outdated prompt — brewer capabilities changed."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    active_setup = _get_active_setup(request, db)
    brewer = active_setup.brewer if active_setup else None

    # Compute which params are new (in current brewer set but not in current campaign)
    from app.services.optimizer import _param_set_fingerprint
    from app.services.parameter_registry import get_param_columns

    current_params = set(get_param_columns(method, brewer))
    # Load the stored fingerprint to derive which params are in the old campaign
    # We show all params in the new set that weren't in Tier 1 (brewer=None)
    tier1_params = set(get_param_columns(method, None))
    new_params = sorted(current_params - tier1_params)

    return templates.TemplateResponse(
        request,
        "brew/campaign_outdated.html",
        {
            "active_bean": bean,
            "campaign_key": campaign_key,
            "method": method,
            "new_params": new_params,
        },
    )


@router.post("/rebuild-campaign", response_class=HTMLResponse)
async def rebuild_campaign_route(
    request: Request,
    db: Session = Depends(get_db),
):
    """Rebuild the campaign with the current brewer's full parameter set."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    form = await request.form()
    campaign_key = str(form.get("campaign_key", ""))
    method = str(form.get("method", "espresso"))

    active_setup = _get_active_setup(request, db)
    brewer = active_setup.brewer if active_setup else None

    optimizer = request.app.state.optimizer
    optimizer.accept_rebuild(
        campaign_key,
        method=method,
        brewer=brewer,
        overrides=bean.parameter_overrides,
    )

    # Redirect to trigger a fresh recommendation with the new params
    return RedirectResponse(url="/brew/recommend", status_code=303)


@router.post("/decline-rebuild", response_class=HTMLResponse)
async def decline_rebuild_route(
    request: Request,
    db: Session = Depends(get_db),
):
    """Decline the campaign rebuild prompt — increment the decline counter."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    form = await request.form()
    campaign_key = str(form.get("campaign_key", ""))

    optimizer = request.app.state.optimizer
    optimizer.decline_rebuild(campaign_key)

    return RedirectResponse(url="/brew", status_code=303)
