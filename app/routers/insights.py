"""Insights router — optimization progress, convergence, and trust signals."""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean

router = APIRouter(prefix="/insights", tags=["insights"])
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_convergence(measurements_list: list[dict]) -> dict:
    """Compute convergence status from ordered measurements.

    Args:
        measurements_list: List of measurement dicts ordered by created_at asc.
            Each dict has keys: taste, is_failed, created_at, grind_setting.

    Returns:
        Dict with status, label, description, color keys.
    """
    n = len(measurements_list)

    if n < 3:
        return {
            "status": "getting_started",
            "label": "Getting started",
            "description": "Pull a few more shots to give the optimizer enough data to start learning.",
            "color": "muted",
        }

    if n < 8:
        return {
            "status": "early_exploration",
            "label": "Early exploration",
            "description": "The optimizer is mapping out the parameter space. Each shot teaches it something new.",
            "color": "blue",
        }

    # n >= 8: check improvement trend
    non_failed = [m for m in measurements_list if not m["is_failed"]]

    if len(non_failed) < 3:
        # Not enough non-failed shots to evaluate trend
        return {
            "status": "refining",
            "label": "Refining",
            "description": "The optimizer is fine-tuning. It may still find small improvements.",
            "color": "amber",
        }

    last_3 = non_failed[-3:]
    before_last_3 = non_failed[:-3]

    if before_last_3:
        best_before = max(m["taste"] for m in before_last_3)
        max_recent = max(m["taste"] for m in last_3)

        if max_recent > best_before:
            return {
                "status": "narrowing_in",
                "label": "Narrowing in",
                "description": "Recent shots are hitting new highs. The optimizer is finding promising territory.",
                "color": "amber",
            }

    # Check last 5 non-failed for no improvement
    last_5 = non_failed[-5:]
    before_last_5 = non_failed[:-5]

    if before_last_5:
        best_before_5 = max(m["taste"] for m in before_last_5)
        max_last_5 = max(m["taste"] for m in last_5)

        if max_last_5 <= best_before_5:
            return {
                "status": "near_optimal",
                "label": "Likely near optimal",
                "description": "The optimizer hasn't found anything better recently. Your current best recipe may be close to the limit for this bean.",
                "color": "green",
            }

    return {
        "status": "refining",
        "label": "Refining",
        "description": "The optimizer is fine-tuning. It may still find small improvements.",
        "color": "amber",
    }


def _build_chart_data(measurements_list: list[dict]) -> dict:
    """Build Chart.js-ready data from ordered measurements.

    Args:
        measurements_list: List of measurement dicts ordered by created_at asc.

    Returns:
        Dict with labels, individual_scores, cumulative_best, failed_indices.
    """
    labels = []
    individual_scores = []
    cumulative_best = []
    failed_indices = []

    running_best = None

    for i, m in enumerate(measurements_list):
        labels.append(i + 1)
        individual_scores.append(m["taste"] if m["taste"] is not None else 0)

        if m["is_failed"]:
            failed_indices.append(i)

        # Update running best (only from non-failed shots)
        if not m["is_failed"] and m["taste"] is not None:
            if running_best is None or m["taste"] > running_best:
                running_best = m["taste"]

        cumulative_best.append(running_best)

    return {
        "labels": labels,
        "individual_scores": individual_scores,
        "cumulative_best": cumulative_best,
        "failed_indices": failed_indices,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def insights_page(
    request: Request,
    bean_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Insights page — optimization progress and convergence for the selected bean."""
    # Resolve bean: query param takes precedence, then cookie fallback
    bean = None
    if bean_id:
        bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        bean = _get_active_bean(request, db)

    # Always fetch all beans for the picker dropdown
    beans = db.query(Bean).order_by(Bean.name).all()
    selected_bean_id = bean.id if bean else None

    # No bean selected — render a minimal page with the picker
    if not bean:
        return templates.TemplateResponse(
            request,
            "insights/index.html",
            {
                "active_bean": None,
                "beans": beans,
                "selected_bean_id": selected_bean_id,
                "shot_count": 0,
                "convergence": None,
                "optimizer_phase": None,
                "best_taste": None,
                "chart_data": None,
                "heatmap_data": None,
            },
        )

    # Get all measurements for this bean, ordered by creation time
    measurements_raw = (
        db.query(Measurement)
        .filter(Measurement.bean_id == bean.id)
        .order_by(Measurement.created_at.asc())
        .all()
    )

    measurements = [
        {
            "taste": m.taste,
            "is_failed": m.is_failed,
            "created_at": m.created_at,
            "grind_setting": m.grind_setting,
            "temperature": m.temperature,
            "dose_in": m.dose_in,
            "target_yield": m.target_yield,
            "preinfusion_pressure_pct": m.preinfusion_pressure_pct,
            "saturation": m.saturation,
        }
        for m in measurements_raw
    ]

    shot_count = len(measurements)
    convergence = _compute_convergence(measurements)

    # Determine optimizer phase
    optimizer = request.app.state.optimizer
    campaign = optimizer.get_or_create_campaign(bean.id, overrides=bean.parameter_overrides)
    from baybe.recommenders.pure.nonpredictive.sampling import RandomRecommender

    selected = campaign.recommender.select_recommender(
        batch_size=1,
        searchspace=campaign.searchspace,
        objective=campaign.objective,
        measurements=campaign.measurements,
    )
    if isinstance(selected, RandomRecommender):
        optimizer_phase = "random"
    else:
        optimizer_phase = "bayesian_early" if shot_count < 8 else "bayesian"

    # Best measurement
    best_taste = None
    if measurements:
        non_failed = [m for m in measurements if not m["is_failed"]]
        if non_failed:
            best_taste = max(m["taste"] for m in non_failed)

    # Chart data (only if enough data)
    chart_data = None
    if shot_count >= 2:
        chart_data = _build_chart_data(measurements)

    # Heatmap data (grind vs temperature, colored by taste)
    heatmap_data = None
    if shot_count >= 3:
        heatmap_data = {
            "points": [
                {
                    "x": m["grind_setting"],
                    "y": m["temperature"],
                    "taste": m["taste"],
                    "is_failed": m["is_failed"],
                }
                for m in measurements
            ]
        }

    return templates.TemplateResponse(
        request,
        "insights/index.html",
        {
            "active_bean": bean,
            "beans": beans,
            "selected_bean_id": selected_bean_id,
            "shot_count": shot_count,
            "convergence": convergence,
            "optimizer_phase": optimizer_phase,
            "best_taste": best_taste,
            "chart_data": chart_data,
            "heatmap_data": heatmap_data,
        },
    )
