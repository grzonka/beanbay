"""Bean management routes — CRUD, activation, parameter overrides."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bag import Bag
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.services.parameter_registry import get_default_bounds

router = APIRouter(prefix="/beans", tags=["beans"])
templates = Jinja2Templates(directory="app/templates")


def _get_active_bean(request: Request, db: Session) -> Optional[Bean]:
    """Read active bean from cookie."""
    bean_id = request.cookies.get("active_bean_id")
    if bean_id:
        return db.query(Bean).filter(Bean.id == bean_id).first()
    return None


def _bean_with_shot_count(db: Session, bean: Bean) -> dict:
    """Build a dict with bean fields + shot_count + bags."""
    count = db.query(func.count(Measurement.id)).filter(Measurement.bean_id == bean.id).scalar()
    return {
        "id": bean.id,
        "name": bean.name,
        "roaster": bean.roaster,
        "origin": bean.origin,
        "roast_date": bean.roast_date,
        "process": bean.process,
        "variety": bean.variety,
        "created_at": bean.created_at,
        "parameter_overrides": bean.parameter_overrides,
        "shot_count": count or 0,
        "bags": sorted(bean.bags, key=lambda b: b.created_at, reverse=True) if bean.bags else [],
    }


def _is_htmx(request: Request) -> bool:
    """Check if request is from htmx."""
    return request.headers.get("HX-Request") == "true"


@router.get("", response_class=HTMLResponse)
async def list_beans(request: Request, db: Session = Depends(get_db)):
    """Bean list page — the home screen."""
    beans_raw = db.query(Bean).order_by(Bean.created_at.desc()).all()
    beans = [_bean_with_shot_count(db, b) for b in beans_raw]
    active_bean = _get_active_bean(request, db)

    return templates.TemplateResponse(
        request,
        "beans/list.html",
        {"beans": beans, "active_bean": active_bean},
    )


@router.post("", response_class=HTMLResponse)
async def create_bean(
    request: Request,
    name: str = Form(...),
    roaster: str = Form(""),
    origin: str = Form(""),
    roast_date: str = Form(""),
    process: str = Form(""),
    variety: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new bean."""
    bean = Bean(
        name=name.strip(),
        roaster=roaster.strip() or None,
        origin=origin.strip() or None,
        roast_date=datetime.strptime(roast_date, "%Y-%m-%d").date() if roast_date.strip() else None,
        process=process.strip() or None,
        variety=variety.strip() or None,
    )
    db.add(bean)
    db.commit()
    db.refresh(bean)

    if _is_htmx(request):
        # Return just the bean card fragment to prepend to the list
        bean_data = _bean_with_shot_count(db, bean)
        active_bean = _get_active_bean(request, db)
        return templates.TemplateResponse(
            request,
            "beans/_bean_card.html",
            {"bean": bean_data, "active_bean": active_bean},
        )

    return RedirectResponse(url="/beans", status_code=303)


@router.post("/deactivate")
async def deactivate_bean(request: Request):
    """Clear the active bean (delete cookie)."""
    if _is_htmx(request):
        response = templates.TemplateResponse(
            request,
            "beans/_active_indicator.html",
            {"active_bean": None},
        )
    else:
        response = RedirectResponse(url="/beans", status_code=303)
    response.delete_cookie("active_bean_id")
    return response


@router.post("/set-active")
async def set_active_bean(
    request: Request,
    bean_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Set active bean from a form POST (bean picker on brew page). Redirects back to /brew."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/brew", status_code=303)

    response = RedirectResponse(url="/brew", status_code=303)
    response.set_cookie(
        key="active_bean_id",
        value=bean_id,
        max_age=60 * 60 * 24 * 365,  # 1 year
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/{bean_id}", response_class=HTMLResponse)
async def bean_detail(request: Request, bean_id: str, db: Session = Depends(get_db)):
    """Bean detail page with parameter overrides."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bean_data = _bean_with_shot_count(db, bean)
    active_bean = _get_active_bean(request, db)

    return templates.TemplateResponse(
        request,
        "beans/detail.html",
        {
            "bean": bean_data,
            "active_bean": active_bean,
            "default_bounds": get_default_bounds("espresso"),
        },
    )


@router.post("/{bean_id}", response_class=HTMLResponse)
async def update_bean(
    request: Request,
    bean_id: str,
    name: str = Form(...),
    roaster: str = Form(""),
    origin: str = Form(""),
    roast_date: str = Form(""),
    process: str = Form(""),
    variety: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update bean info (name, roaster, origin, roast_date, process, variety)."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bean.name = name.strip()
    bean.roaster = roaster.strip() or None
    bean.origin = origin.strip() or None
    bean.roast_date = (
        datetime.strptime(roast_date, "%Y-%m-%d").date() if roast_date.strip() else None
    )
    bean.process = process.strip() or None
    bean.variety = variety.strip() or None
    db.commit()

    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)


@router.post("/{bean_id}/overrides", response_class=HTMLResponse)
async def update_overrides(
    request: Request,
    bean_id: str,
    db: Session = Depends(get_db),
):
    """Update parameter overrides from form data."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    form = await request.form()
    overrides = {}
    invalid_params = []

    for param, (default_min, default_max) in get_default_bounds("espresso").items():
        min_key = f"{param}_min"
        max_key = f"{param}_max"
        min_val = form.get(min_key, "").strip()
        max_val = form.get(max_key, "").strip()

        if min_val or max_val:
            try:
                spec = {}
                if min_val:
                    parsed_min = float(min_val)
                    if parsed_min != default_min:
                        spec["min"] = parsed_min
                if max_val:
                    parsed_max = float(max_val)
                    if parsed_max != default_max:
                        spec["max"] = parsed_max
                if spec:
                    overrides[param] = spec
            except ValueError:
                invalid_params.append(param.replace("_", " "))

    if invalid_params:
        # Surface error to user — return detail page with error message
        bean_data = _bean_with_shot_count(db, bean)
        active_bean = _get_active_bean(request, db)
        error_msg = f"Invalid values for: {', '.join(invalid_params)}. Please enter numbers only."

        return templates.TemplateResponse(
            request,
            "beans/detail.html",
            {
                "bean": bean_data,
                "active_bean": active_bean,
                "default_bounds": get_default_bounds("espresso"),
                "error": error_msg,
            },
            status_code=422,
        )

    bean.parameter_overrides = overrides if overrides else None
    db.commit()

    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)


@router.post("/{bean_id}/activate")
async def activate_bean(
    request: Request,
    bean_id: str,
    db: Session = Depends(get_db),
):
    """Set this bean as the active bean (stored in cookie)."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    if _is_htmx(request):
        # Return updated nav indicator
        response = templates.TemplateResponse(
            request,
            "beans/_active_indicator.html",
            {"active_bean": bean},
        )
    else:
        response = RedirectResponse(url="/beans", status_code=303)

    response.set_cookie(
        key="active_bean_id",
        value=bean_id,
        max_age=60 * 60 * 24 * 365,  # 1 year
        httponly=True,
        samesite="lax",
    )
    return response


@router.delete("/{bean_id}", response_class=HTMLResponse)
async def delete_bean(
    request: Request,
    bean_id: str,
    db: Session = Depends(get_db),
):
    """Delete a bean and all its measurements (htmx DELETE)."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if bean:
        db.delete(bean)
        db.commit()

    if _is_htmx(request):
        return HTMLResponse("")

    return RedirectResponse(url="/beans", status_code=303)


@router.post("/{bean_id}/bags", response_class=HTMLResponse)
async def add_bag(
    request: Request,
    bean_id: str,
    purchase_date: str = Form(""),
    cost: str = Form(""),
    weight_grams: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    """Add a bag to a bean."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bag = Bag(
        bean_id=bean_id,
        purchase_date=datetime.strptime(purchase_date, "%Y-%m-%d").date()
        if purchase_date.strip()
        else None,
        cost=float(cost) if cost.strip() else None,
        weight_grams=float(weight_grams) if weight_grams.strip() else None,
        notes=notes.strip() or None,
    )
    db.add(bag)
    db.commit()

    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)


@router.post("/{bean_id}/bags/{bag_id}/delete")
async def delete_bag(
    request: Request,
    bean_id: str,
    bag_id: str,
    db: Session = Depends(get_db),
):
    """Delete a bag."""
    bag = db.query(Bag).filter(Bag.id == bag_id, Bag.bean_id == bean_id).first()
    if bag:
        db.delete(bag)
        db.commit()

    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)


@router.post("/{bean_id}/delete")
async def delete_bean_form(
    request: Request,
    bean_id: str,
    db: Session = Depends(get_db),
):
    """Delete a bean — HTML form POST version (forms can't send DELETE)."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if bean:
        db.delete(bean)
        db.commit()

    return RedirectResponse(url="/beans", status_code=303)
