"""History routes — shot history list with bean, setup and taste score filters."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.bean import Bean
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean

router = APIRouter(prefix="/history", tags=["history"])
templates = Jinja2Templates(directory="app/templates")


def _is_htmx(request: Request) -> bool:
    """Check if request is from htmx."""
    return request.headers.get("HX-Request") == "true"


def _build_shot_dicts(
    db: Session,
    bean_id: Optional[str],
    min_taste: Optional[float],
    setup_id: Optional[str] = None,
) -> list[dict]:
    """Query measurements with optional filters, return enriched dicts."""
    query = (
        db.query(Measurement)
        .join(Bean, Measurement.bean_id == Bean.id)
        .options(joinedload(Measurement.brew_setup))
    )

    if bean_id:
        query = query.filter(Measurement.bean_id == bean_id)
    if min_taste is not None:
        query = query.filter(Measurement.taste >= min_taste)
    if setup_id:
        query = query.filter(Measurement.brew_setup_id == setup_id)

    measurements = query.order_by(Measurement.created_at.desc()).all()

    shots = []
    for m in measurements:
        brew_ratio = round(m.target_yield / m.dose_in, 2) if m.dose_in and m.target_yield else None
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
                "is_manual": getattr(m, "is_manual", False) or False,
                "notes": m.notes,
                "bean_name": m.bean.name if m.bean else "",
                "bean_id": m.bean_id,
                "dose_in": m.dose_in,
                "target_yield": m.target_yield,
                "brew_ratio": brew_ratio,
                "flavor_tags": tags,
                "brew_setup_name": m.brew_setup.name if m.brew_setup else None,
                "brew_method": (
                    m.brew_setup.brew_method.name
                    if m.brew_setup and m.brew_setup.brew_method
                    else "espresso"
                ),
            }
        )
    return shots


def _load_shot_detail(shot_id: int, db: Session) -> dict:
    """Load a single measurement by ID, return enriched dict (raises 404 if missing)."""
    m = db.query(Measurement).filter(Measurement.id == shot_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Shot not found")

    brew_ratio = None
    if m.dose_in and m.target_yield:
        brew_ratio = f"1:{round(m.target_yield / m.dose_in, 1)}"

    tags = []
    if m.flavor_tags:
        try:
            tags = json.loads(m.flavor_tags)
        except (ValueError, TypeError):
            tags = []

    return {
        "id": m.id,
        "created_at": m.created_at,
        "taste": m.taste,
        "grind_setting": m.grind_setting,
        "temperature": m.temperature,
        "preinfusion_pressure_pct": m.preinfusion_pressure_pct,
        "dose_in": m.dose_in,
        "target_yield": m.target_yield,
        "saturation": m.saturation,
        "preinfusion_time": m.preinfusion_time,
        "preinfusion_pressure": m.preinfusion_pressure,
        "brew_pressure": m.brew_pressure,
        "pressure_profile": m.pressure_profile,
        "bloom_pause": m.bloom_pause,
        "flow_rate": m.flow_rate,
        "temp_profile": m.temp_profile,
        "steep_time": m.steep_time,
        "brew_volume": m.brew_volume,
        "bloom_weight": m.bloom_weight,
        "brew_mode": m.brew_mode,
        "extraction_time": m.extraction_time,
        "is_failed": m.is_failed,
        "is_manual": getattr(m, "is_manual", False) or False,
        "notes": m.notes,
        "acidity": m.acidity,
        "sweetness": m.sweetness,
        "body": m.body,
        "bitterness": m.bitterness,
        "aroma": m.aroma,
        "intensity": m.intensity,
        "flavor_tags_list": tags,
        "bean_name": m.bean.name if m.bean else "",
        "bean_id": m.bean_id,
        "brew_ratio": brew_ratio,
    }


# ---------------------------------------------------------------------------
# List routes (must be before /{shot_id} wildcard)
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def history_page(
    request: Request,
    bean_id: Optional[str] = None,
    min_taste: Optional[float] = None,
    setup_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Full history page."""
    active_bean = _get_active_bean(request, db)
    beans = db.query(Bean).order_by(Bean.name).all()
    setups = (
        db.query(BrewSetup).filter(BrewSetup.is_retired.is_(False)).order_by(BrewSetup.name).all()
    )
    shots = _build_shot_dicts(db, bean_id, min_taste, setup_id)

    return templates.TemplateResponse(
        request,
        "history/index.html",
        {
            "beans": beans,
            "setups": setups,
            "shots": shots,
            "active_bean": active_bean,
            "filter_bean_id": bean_id,
            "filter_setup_id": setup_id,
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
    setup_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """htmx partial — filtered shot list only."""
    shots = _build_shot_dicts(db, bean_id, min_taste, setup_id)

    return templates.TemplateResponse(
        request,
        "history/_shot_list.html",
        {
            "shots": shots,
            "filter_bean_id": bean_id,
            "filter_min_taste": min_taste,
        },
    )


# ---------------------------------------------------------------------------
# Shot detail / edit routes
# ---------------------------------------------------------------------------


@router.get("/{shot_id}", response_class=HTMLResponse)
async def shot_detail(
    request: Request,
    shot_id: int,
    db: Session = Depends(get_db),
):
    """Shot detail modal — returns modal HTML with HX-Trigger: openShotModal."""
    shot = _load_shot_detail(shot_id, db)

    response = templates.TemplateResponse(
        request,
        "history/_shot_modal.html",
        {"shot": shot, "ratio": shot.get("brew_ratio")},
    )
    response.headers["HX-Trigger"] = "openShotModal"
    return response


@router.get("/{shot_id}/edit", response_class=HTMLResponse)
async def shot_edit_form(
    request: Request,
    shot_id: int,
    db: Session = Depends(get_db),
):
    """Shot edit form — returns edit form HTML inside modal."""
    shot = _load_shot_detail(shot_id, db)

    return templates.TemplateResponse(
        request,
        "history/_shot_edit.html",
        {"shot": shot},
    )


@router.post("/{shot_id}/edit", response_class=HTMLResponse)
async def shot_edit_save(
    request: Request,
    shot_id: int,
    notes: Optional[str] = Form(None),
    acidity: Optional[str] = Form(None),
    sweetness: Optional[str] = Form(None),
    body: Optional[str] = Form(None),
    bitterness: Optional[str] = Form(None),
    aroma: Optional[str] = Form(None),
    intensity: Optional[str] = Form(None),
    flavor_tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Save shot edits — updates notes, flavor dimensions, flavor tags.
    Returns updated modal HTML + oob-swapped shot row.
    """
    m = db.query(Measurement).filter(Measurement.id == shot_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Shot not found")

    # Notes: empty string → None
    m.notes = notes.strip() if notes and notes.strip() else None

    # Flavor dimensions: submitted value → float, missing/empty → None
    def _parse_dim(val: Optional[str]) -> Optional[float]:
        if val is None or val.strip() == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    m.acidity = _parse_dim(acidity)
    m.sweetness = _parse_dim(sweetness)
    m.body = _parse_dim(body)
    m.bitterness = _parse_dim(bitterness)
    m.aroma = _parse_dim(aroma)
    m.intensity = _parse_dim(intensity)

    # Flavor tags: comma-separated → JSON list; empty → None
    if flavor_tags and flavor_tags.strip():
        tag_list = [t.strip() for t in flavor_tags.split(",") if t.strip()]
        m.flavor_tags = json.dumps(tag_list) if tag_list else None
    else:
        m.flavor_tags = None

    db.commit()
    db.refresh(m)

    # Build updated shot dict
    shot = _load_shot_detail(shot_id, db)
    brew_ratio = shot.get("brew_ratio")

    # Render updated modal as main response
    modal_html = templates.get_template("history/_shot_modal.html").render(
        {"request": request, "shot": shot, "ratio": brew_ratio}
    )

    # Build plain row dict (matching _build_shot_dicts structure)
    row_shot = {
        "id": m.id,
        "created_at": m.created_at,
        "taste": m.taste,
        "grind_setting": m.grind_setting,
        "is_failed": m.is_failed,
        "is_manual": getattr(m, "is_manual", False) or False,
        "notes": m.notes,
        "bean_name": m.bean.name if m.bean else "",
        "bean_id": m.bean_id,
        "dose_in": m.dose_in,
        "target_yield": m.target_yield,
        "brew_ratio": brew_ratio,
        "flavor_tags": shot["flavor_tags_list"],
        "brew_setup_name": m.brew_setup.name if m.brew_setup else None,
    }

    # Render updated shot row for oob swap
    row_html = templates.get_template("history/_shot_row.html").render(
        {"request": request, "shot": row_shot}
    )

    # Add hx-swap-oob to the row root element so htmx replaces it in the list
    oob_row_html = row_html.replace(
        f'id="shot-{m.id}"',
        f'id="shot-{m.id}" hx-swap-oob="outerHTML:#shot-{m.id}"',
        1,
    )

    return HTMLResponse(content=modal_html + oob_row_html)


# ---------------------------------------------------------------------------
# Batch delete
# ---------------------------------------------------------------------------


@router.post("/delete-batch")
async def delete_batch(request: Request, db: Session = Depends(get_db)):
    """Delete selected measurements and rebuild BayBE campaigns for affected beans."""
    import pandas as pd

    from app.services.parameter_registry import get_param_columns

    form = await request.form()
    shot_ids = form.getlist("shot_ids")
    if not shot_ids:
        return RedirectResponse(url="/history", status_code=303)

    # Convert to ints
    shot_ids_int = [int(sid) for sid in shot_ids]

    # Find affected beans before deleting
    measurements = db.query(Measurement).filter(Measurement.id.in_(shot_ids_int)).all()
    affected_bean_ids = {m.bean_id for m in measurements}

    # Delete measurements
    db.query(Measurement).filter(Measurement.id.in_(shot_ids_int)).delete(synchronize_session=False)
    db.commit()

    # Rebuild campaigns for affected beans
    optimizer = request.app.state.optimizer
    for bean_id in affected_bean_ids:
        bean = db.query(Bean).filter(Bean.id == bean_id).first()
        remaining = db.query(Measurement).filter(Measurement.bean_id == bean_id).all()
        overrides = bean.parameter_overrides if bean else None

        # Group remaining measurements by (method, setup_id) to rebuild per-campaign
        from app.services.optimizer_key import make_campaign_key
        from collections import defaultdict

        campaigns_to_rebuild: dict[tuple, list] = defaultdict(list)
        for m in remaining:
            if m.brew_setup is not None and m.brew_setup.brew_method is not None:
                method = m.brew_setup.brew_method.name.lower()
                setup_id = str(m.brew_setup_id)
                brewer = m.brew_setup.brewer
            else:
                method = "espresso"
                setup_id = None
                brewer = None
            campaigns_to_rebuild[(method, setup_id, id(brewer))].append((m, brewer))

        if campaigns_to_rebuild:
            for (method, setup_id, _), measurements_and_brewers in campaigns_to_rebuild.items():
                brewer = measurements_and_brewers[0][1]  # same brewer for all in group
                param_columns = get_param_columns(method, brewer)
                campaign_key = make_campaign_key(str(bean_id), method, setup_id)
                df = pd.DataFrame(
                    [
                        {
                            **{
                                col: getattr(m, col)
                                for col in param_columns
                                if getattr(m, col) is not None
                            },
                            "taste": m.taste,
                        }
                        for m, _ in measurements_and_brewers
                    ]
                )
                # Drop rows where any param column is missing
                df = df.dropna(subset=param_columns)
                optimizer.rebuild_campaign(
                    campaign_key, df, overrides=overrides, method=method, brewer=brewer
                )
        else:
            # No remaining measurements — rebuild empty Tier 1 campaign
            campaign_key = make_campaign_key(str(bean_id), "espresso", None)
            optimizer.rebuild_campaign(campaign_key, pd.DataFrame(), overrides=overrides)

    return RedirectResponse(url="/history", status_code=303)
