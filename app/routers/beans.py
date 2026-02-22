"""Bean management routes — CRUD, activation, parameter overrides."""

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.services.optimizer import DEFAULT_BOUNDS

router = APIRouter(prefix="/beans", tags=["beans"])
templates = Jinja2Templates(directory="app/templates")


def _get_active_bean(request: Request, db: Session) -> Optional[Bean]:
    """Read active bean from cookie."""
    bean_id = request.cookies.get("active_bean_id")
    if bean_id:
        return db.query(Bean).filter(Bean.id == bean_id).first()
    return None


def _bean_with_shot_count(db: Session, bean: Bean) -> dict:
    """Build a dict with bean fields + shot_count."""
    count = db.query(func.count(Measurement.id)).filter(Measurement.bean_id == bean.id).scalar()
    return {
        "id": bean.id,
        "name": bean.name,
        "roaster": bean.roaster,
        "origin": bean.origin,
        "created_at": bean.created_at,
        "parameter_overrides": bean.parameter_overrides,
        "shot_count": count or 0,
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
    db: Session = Depends(get_db),
):
    """Create a new bean."""
    bean = Bean(
        name=name.strip(),
        roaster=roaster.strip() or None,
        origin=origin.strip() or None,
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
        {"bean": bean_data, "active_bean": active_bean, "default_bounds": DEFAULT_BOUNDS},
    )


@router.post("/{bean_id}", response_class=HTMLResponse)
async def update_bean(
    request: Request,
    bean_id: str,
    name: str = Form(...),
    roaster: str = Form(""),
    origin: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update bean info (name, roaster, origin)."""
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bean.name = name.strip()
    bean.roaster = roaster.strip() or None
    bean.origin = origin.strip() or None
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

    for param, (default_min, default_max) in DEFAULT_BOUNDS.items():
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
        from fastapi.responses import HTMLResponse as _HTMLResponse

        return templates.TemplateResponse(
            request,
            "beans/detail.html",
            {
                "bean": bean_data,
                "active_bean": active_bean,
                "default_bounds": DEFAULT_BOUNDS,
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
