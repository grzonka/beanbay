"""History routes — shot history list with bean and taste score filters."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean

router = APIRouter(prefix="/history", tags=["history"])
templates = Jinja2Templates(directory="app/templates")


def _is_htmx(request: Request) -> bool:
    """Check if request is from htmx."""
    return request.headers.get("HX-Request") == "true"


def _build_shot_dicts(
    db: Session, bean_id: Optional[str], min_taste: Optional[float]
) -> list[dict]:
    """Query measurements with optional filters, return enriched dicts."""
    query = db.query(Measurement).join(Bean, Measurement.bean_id == Bean.id)

    if bean_id:
        query = query.filter(Measurement.bean_id == bean_id)
    if min_taste is not None:
        query = query.filter(Measurement.taste >= min_taste)

    measurements = query.order_by(Measurement.created_at.desc()).all()

    shots = []
    for m in measurements:
        brew_ratio = round(m.target_yield / m.dose_in, 2) if m.dose_in else None
        tags = []
        if m.flavor_tags:
            try:
                tags = json.loads(m.flavor_tags)
            except (ValueError, TypeError):
                tags = []
        shots.append(
            {
                "id": m.id,
                "created_at": m.created_at,
                "taste": m.taste,
                "grind_setting": m.grind_setting,
                "is_failed": m.is_failed,
                "notes": m.notes,
                "bean_name": m.bean.name if m.bean else "",
                "bean_id": m.bean_id,
                "dose_in": m.dose_in,
                "target_yield": m.target_yield,
                "brew_ratio": brew_ratio,
                "flavor_tags": tags,
            }
        )
    return shots


@router.get("", response_class=HTMLResponse)
async def history_page(
    request: Request,
    bean_id: Optional[str] = None,
    min_taste: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """Full history page."""
    active_bean = _get_active_bean(request, db)
    beans = db.query(Bean).order_by(Bean.name).all()
    shots = _build_shot_dicts(db, bean_id, min_taste)

    return templates.TemplateResponse(
        request,
        "history/index.html",
        {
            "beans": beans,
            "shots": shots,
            "active_bean": active_bean,
            "filter_bean_id": bean_id,
            "filter_min_taste": int(min_taste)
            if min_taste and min_taste == int(min_taste)
            else min_taste,
        },
    )


@router.get("/shots", response_class=HTMLResponse)
async def history_shots_partial(
    request: Request,
    bean_id: Optional[str] = None,
    min_taste: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """htmx partial — filtered shot list only."""
    shots = _build_shot_dicts(db, bean_id, min_taste)

    return templates.TemplateResponse(
        request,
        "history/_shot_list.html",
        {
            "shots": shots,
            "filter_bean_id": bean_id,
            "filter_min_taste": min_taste,
        },
    )
