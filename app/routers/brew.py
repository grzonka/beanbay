"""Brew router — optimization loop: recommend, record, repeat best.

Implements the core espresso optimization workflow:
  GET  /brew                         — Main brew page
  POST /brew/recommend               — Trigger BayBE recommendation
  GET  /brew/recommend/{rec_id}      — Display recommendation + rate form
  POST /brew/record                  — Record measurement (taste/failed)
  GET  /brew/best                    — Show highest-rated shot
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement

router = APIRouter(prefix="/brew", tags=["brew"])
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_active_bean(request: Request, db: Session) -> Optional[Bean]:
    """Read active bean from cookie."""
    bean_id = request.cookies.get("active_bean_id")
    if bean_id:
        return db.query(Bean).filter(Bean.id == bean_id).first()
    return None


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
        return RedirectResponse(url="/beans", status_code=303)

    has_measurements = db.query(Measurement).filter(Measurement.bean_id == bean.id).count() > 0

    return templates.TemplateResponse(
        request,
        "brew/index.html",
        {"active_bean": bean, "has_measurements": has_measurements},
    )


@router.post("/recommend", response_class=HTMLResponse)
async def trigger_recommend(request: Request, db: Session = Depends(get_db)):
    """Generate a BayBE recommendation for the active bean."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    optimizer = request.app.state.optimizer
    rec = await optimizer.recommend(bean.id, overrides=bean.parameter_overrides)

    # Store recommendation in session (redirect to display page)
    rec_id = rec["recommendation_id"]

    # Redirect to the display page, passing rec params via URL or via a temp store.
    # We use a simple server-side approach: store recommendation in request.app.state
    # keyed by recommendation_id. This is fine for a single-user home app.
    request.app.state.pending_recommendations = getattr(
        request.app.state, "pending_recommendations", {}
    )
    request.app.state.pending_recommendations[rec_id] = rec

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
        # Recommendation expired (server restart) or invalid ID → back to brew
        return RedirectResponse(url="/brew", status_code=303)

    ratio = _brew_ratio(rec.get("dose_in", 0), rec.get("target_yield", 0))

    return templates.TemplateResponse(
        request,
        "brew/recommend.html",
        {
            "active_bean": bean,
            "rec": rec,
            "recommendation_id": recommendation_id,
            "ratio": ratio,
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
    db: Session = Depends(get_db),
):
    """Record a measurement — saves to SQLite and BayBE campaign."""
    bean = _require_active_bean(request, db)
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    # Auto-set taste to 1 for failed shots (choked / gusher)
    failed = is_failed == "true" or is_failed == "1" or is_failed == "on"
    if failed:
        taste = 1.0

    # Clamp taste to valid range
    taste = max(1.0, min(10.0, taste))

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

    # Clean up pending recommendation
    pending = getattr(request.app.state, "pending_recommendations", {})
    pending.pop(recommendation_id, None)

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
