"""Equipment management routes — grinders, brewers, papers, water recipes, brew setups."""

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.equipment import (
    Brewer,
    Grinder,
    Paper,
    WaterRecipe,
)
from app.utils.brewer_capabilities import derive_tier

router = APIRouter(prefix="/equipment", tags=["equipment"])
templates = Jinja2Templates(directory="app/templates")


def _is_htmx(request: Request) -> bool:
    """Check if request is from htmx."""
    return request.headers.get("HX-Request") == "true"


def _parse_float(value: str) -> Optional[float]:
    """Parse a form string to float or None."""
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
async def equipment_index(
    request: Request,
    show_retired: bool = False,
    db: Session = Depends(get_db),
):
    """Equipment management page — shows all equipment types."""
    if show_retired:
        grinders = db.query(Grinder).order_by(Grinder.name).all()
        brewers = db.query(Brewer).order_by(Brewer.name).all()
        papers = db.query(Paper).order_by(Paper.name).all()
        water_recipes = db.query(WaterRecipe).order_by(WaterRecipe.name).all()
    else:
        grinders = (
            db.query(Grinder).filter(Grinder.is_retired.is_(False)).order_by(Grinder.name).all()
        )
        brewers = db.query(Brewer).filter(Brewer.is_retired.is_(False)).order_by(Brewer.name).all()
        papers = db.query(Paper).filter(Paper.is_retired.is_(False)).order_by(Paper.name).all()
        water_recipes = (
            db.query(WaterRecipe)
            .filter(WaterRecipe.is_retired.is_(False))
            .order_by(WaterRecipe.name)
            .all()
        )

    brew_methods = db.query(BrewMethod).order_by(BrewMethod.name).all()

    # Load brew setups with all related objects (no N+1 queries)
    setups = (
        db.query(BrewSetup)
        .options(
            joinedload(BrewSetup.grinder),
            joinedload(BrewSetup.brewer),
            joinedload(BrewSetup.paper),
            joinedload(BrewSetup.water_recipe),
            joinedload(BrewSetup.brew_method),
        )
        .filter(BrewSetup.is_retired.is_(False))
        .order_by(BrewSetup.name)
        .all()
    )

    # Counts for badges
    grinder_count = len(grinders)
    brewer_count = len(brewers)
    paper_count = len(papers)
    water_recipe_count = len(water_recipes)
    setup_count = len(setups)

    return templates.TemplateResponse(
        request,
        "equipment/index.html",
        {
            "grinders": grinders,
            "brewers": brewers,
            "papers": papers,
            "water_recipes": water_recipes,
            "brew_methods": brew_methods,
            "setups": setups,
            "grinder_count": grinder_count,
            "brewer_count": brewer_count,
            "paper_count": paper_count,
            "water_recipe_count": water_recipe_count,
            "setup_count": setup_count,
            "show_retired": show_retired,
            "derive_tier": derive_tier,
        },
    )


# ── Grinder routes ──────────────────────────────────────────────────────────


@router.post("/grinders", response_class=HTMLResponse)
async def create_grinder(
    request: Request,
    name: str = Form(...),
    dial_type: str = Form("stepless"),
    step_size: str = Form(""),
    min_value: str = Form(""),
    max_value: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new grinder."""
    grinder = Grinder(
        name=name.strip(),
        dial_type=dial_type,
        step_size=_parse_float(step_size) if dial_type == "stepped" else None,
        min_value=_parse_float(min_value),
        max_value=_parse_float(max_value),
    )
    db.add(grinder)
    db.commit()
    db.refresh(grinder)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request,
            "equipment/_grinder_card.html",
            {"grinder": grinder},
        )

    return RedirectResponse(url="/equipment", status_code=303)


@router.get("/grinders/{grinder_id}/edit", response_class=HTMLResponse)
async def edit_grinder_form(
    request: Request,
    grinder_id: str,
    db: Session = Depends(get_db),
):
    """Return grinder edit form partial for htmx modal."""
    grinder = db.query(Grinder).filter(Grinder.id == grinder_id).first()
    if not grinder:
        return RedirectResponse(url="/equipment", status_code=303)

    return templates.TemplateResponse(
        request,
        "equipment/_grinder_form.html",
        {"grinder": grinder},
    )


@router.post("/grinders/{grinder_id}", response_class=HTMLResponse)
async def update_grinder(
    request: Request,
    grinder_id: str,
    name: str = Form(...),
    dial_type: str = Form("stepless"),
    step_size: str = Form(""),
    min_value: str = Form(""),
    max_value: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update an existing grinder."""
    grinder = db.query(Grinder).filter(Grinder.id == grinder_id).first()
    if not grinder:
        return RedirectResponse(url="/equipment", status_code=303)

    grinder.name = name.strip()
    grinder.dial_type = dial_type
    grinder.step_size = _parse_float(step_size) if dial_type == "stepped" else None
    grinder.min_value = _parse_float(min_value)
    grinder.max_value = _parse_float(max_value)
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


# ── Brewer routes ───────────────────────────────────────────────────────────


@router.post("/brewers", response_class=HTMLResponse)
async def create_brewer(
    request: Request,
    name: str = Form(...),
    temp_control_type: str = Form("none"),
    temp_min: str = Form(""),
    temp_max: str = Form(""),
    temp_step: str = Form(""),
    preinfusion_type: str = Form("none"),
    preinfusion_max_time: str = Form(""),
    pressure_control_type: str = Form("fixed"),
    pressure_min: str = Form(""),
    pressure_max: str = Form(""),
    flow_control_type: str = Form("none"),
    has_bloom: bool = Form(False),
    stop_mode: str = Form("manual"),
    db: Session = Depends(get_db),
):
    """Create a new brewer with optional method associations and capability fields."""
    form = await request.form()
    method_ids = form.getlist("method_ids")

    brewer = Brewer(
        name=name.strip(),
        temp_control_type=temp_control_type,
        temp_min=_parse_float(temp_min),
        temp_max=_parse_float(temp_max),
        temp_step=_parse_float(temp_step),
        preinfusion_type=preinfusion_type,
        preinfusion_max_time=_parse_float(preinfusion_max_time),
        pressure_control_type=pressure_control_type,
        pressure_min=_parse_float(pressure_min),
        pressure_max=_parse_float(pressure_max),
        flow_control_type=flow_control_type,
        has_bloom=has_bloom,
        stop_mode=stop_mode,
    )
    if method_ids:
        methods = db.query(BrewMethod).filter(BrewMethod.id.in_(method_ids)).all()
        brewer.methods = methods

    db.add(brewer)
    db.commit()
    db.refresh(brewer)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request,
            "equipment/_brewer_card.html",
            {"brewer": brewer, "derive_tier": derive_tier},
        )

    return RedirectResponse(url="/equipment", status_code=303)


@router.get("/brewers/{brewer_id}/edit", response_class=HTMLResponse)
async def edit_brewer_form(
    request: Request,
    brewer_id: str,
    db: Session = Depends(get_db),
):
    """Return brewer edit form partial for htmx modal."""
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    if not brewer:
        return RedirectResponse(url="/equipment", status_code=303)

    brew_methods = db.query(BrewMethod).order_by(BrewMethod.name).all()

    return templates.TemplateResponse(
        request,
        "equipment/_brewer_form.html",
        {"brewer": brewer, "brew_methods": brew_methods, "derive_tier": derive_tier},
    )


@router.post("/brewers/{brewer_id}", response_class=HTMLResponse)
async def update_brewer(
    request: Request,
    brewer_id: str,
    name: str = Form(...),
    temp_control_type: str = Form("none"),
    temp_min: str = Form(""),
    temp_max: str = Form(""),
    temp_step: str = Form(""),
    preinfusion_type: str = Form("none"),
    preinfusion_max_time: str = Form(""),
    pressure_control_type: str = Form("fixed"),
    pressure_min: str = Form(""),
    pressure_max: str = Form(""),
    flow_control_type: str = Form("none"),
    has_bloom: bool = Form(False),
    stop_mode: str = Form("manual"),
    db: Session = Depends(get_db),
):
    """Update an existing brewer."""
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    if not brewer:
        return RedirectResponse(url="/equipment", status_code=303)

    form = await request.form()
    method_ids = form.getlist("method_ids")

    brewer.name = name.strip()
    brewer.methods = (
        db.query(BrewMethod).filter(BrewMethod.id.in_(method_ids)).all() if method_ids else []
    )
    brewer.temp_control_type = temp_control_type
    brewer.temp_min = _parse_float(temp_min)
    brewer.temp_max = _parse_float(temp_max)
    brewer.temp_step = _parse_float(temp_step)
    brewer.preinfusion_type = preinfusion_type
    brewer.preinfusion_max_time = _parse_float(preinfusion_max_time)
    brewer.pressure_control_type = pressure_control_type
    brewer.pressure_min = _parse_float(pressure_min)
    brewer.pressure_max = _parse_float(pressure_max)
    brewer.flow_control_type = flow_control_type
    brewer.has_bloom = has_bloom
    brewer.stop_mode = stop_mode
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


# ── Paper / Filter routes ────────────────────────────────────────────────────


@router.post("/papers", response_class=HTMLResponse)
async def create_paper(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new paper/filter."""
    paper = Paper(
        name=name.strip(),
        description=description.strip() or None,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request,
            "equipment/_paper_card.html",
            {"paper": paper},
        )

    return RedirectResponse(url="/equipment", status_code=303)


@router.get("/papers/{paper_id}/edit", response_class=HTMLResponse)
async def edit_paper_form(
    request: Request,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Return paper edit form partial for htmx modal."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return RedirectResponse(url="/equipment", status_code=303)

    return templates.TemplateResponse(
        request,
        "equipment/_paper_form.html",
        {"paper": paper},
    )


@router.post("/papers/{paper_id}", response_class=HTMLResponse)
async def update_paper(
    request: Request,
    paper_id: str,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update an existing paper/filter."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return RedirectResponse(url="/equipment", status_code=303)

    paper.name = name.strip()
    paper.description = description.strip() or None
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


# ── Water Recipe routes ──────────────────────────────────────────────────────


@router.post("/water-recipes", response_class=HTMLResponse)
async def create_water_recipe(
    request: Request,
    name: str = Form(...),
    notes: str = Form(""),
    gh: str = Form(""),
    kh: str = Form(""),
    ca: str = Form(""),
    mg: str = Form(""),
    na: str = Form(""),
    cl: str = Form(""),
    so4: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new water recipe."""
    recipe = WaterRecipe(
        name=name.strip(),
        notes=notes.strip() or None,
        gh=_parse_float(gh),
        kh=_parse_float(kh),
        ca=_parse_float(ca),
        mg=_parse_float(mg),
        na=_parse_float(na),
        cl=_parse_float(cl),
        so4=_parse_float(so4),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request,
            "equipment/_water_card.html",
            {"recipe": recipe},
        )

    return RedirectResponse(url="/equipment", status_code=303)


@router.get("/water-recipes/{recipe_id}/edit", response_class=HTMLResponse)
async def edit_water_recipe_form(
    request: Request,
    recipe_id: str,
    db: Session = Depends(get_db),
):
    """Return water recipe edit form partial for htmx modal."""
    recipe = db.query(WaterRecipe).filter(WaterRecipe.id == recipe_id).first()
    if not recipe:
        return RedirectResponse(url="/equipment", status_code=303)

    return templates.TemplateResponse(
        request,
        "equipment/_water_form.html",
        {"recipe": recipe},
    )


@router.post("/water-recipes/{recipe_id}", response_class=HTMLResponse)
async def update_water_recipe(
    request: Request,
    recipe_id: str,
    name: str = Form(...),
    notes: str = Form(""),
    gh: str = Form(""),
    kh: str = Form(""),
    ca: str = Form(""),
    mg: str = Form(""),
    na: str = Form(""),
    cl: str = Form(""),
    so4: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update an existing water recipe."""
    recipe = db.query(WaterRecipe).filter(WaterRecipe.id == recipe_id).first()
    if not recipe:
        return RedirectResponse(url="/equipment", status_code=303)

    recipe.name = name.strip()
    recipe.notes = notes.strip() or None
    recipe.gh = _parse_float(gh)
    recipe.kh = _parse_float(kh)
    recipe.ca = _parse_float(ca)
    recipe.mg = _parse_float(mg)
    recipe.na = _parse_float(na)
    recipe.cl = _parse_float(cl)
    recipe.so4 = _parse_float(so4)
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


# ── Brew Setup routes ────────────────────────────────────────────────────────


def _get_wizard_context(db: Session) -> dict:
    """Fetch all active equipment for the wizard steps."""
    return {
        "brewers": db.query(Brewer)
        .filter(Brewer.is_retired.is_(False))
        .order_by(Brewer.name)
        .all(),
        "grinders": db.query(Grinder)
        .filter(Grinder.is_retired.is_(False))
        .order_by(Grinder.name)
        .all(),
        "papers": db.query(Paper).filter(Paper.is_retired.is_(False)).order_by(Paper.name).all(),
        "water_recipes": db.query(WaterRecipe)
        .filter(WaterRecipe.is_retired.is_(False))
        .order_by(WaterRecipe.name)
        .all(),
    }


@router.get("/setups/new", response_class=HTMLResponse)
async def new_setup_wizard(
    request: Request,
    db: Session = Depends(get_db),
):
    """Show the brew setup assembly wizard (create mode)."""
    ctx = _get_wizard_context(db)
    return templates.TemplateResponse(
        request,
        "equipment/_setup_wizard.html",
        {**ctx, "setup": None, "edit_mode": False},
    )


@router.post("/setups", response_class=HTMLResponse)
async def create_setup(
    request: Request,
    name: str = Form(...),
    brewer_id: str = Form(...),
    grinder_id: str = Form(...),
    paper_id: str = Form(""),
    water_recipe_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Create a new brew setup from wizard form."""
    # Resolve brew_method_id from brewer
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    brew_method_id = None
    if brewer and brewer.methods:
        brew_method_id = brewer.methods[0].id

    # Fallback: use the first available method if brewer has none
    if not brew_method_id:
        first_method = db.query(BrewMethod).order_by(BrewMethod.name).first()
        if first_method:
            brew_method_id = first_method.id

    if not brew_method_id:
        # No methods exist at all — cannot create setup
        # Redirect back to equipment page with an error scenario handled gracefully
        return RedirectResponse(url="/equipment", status_code=303)

    setup = BrewSetup(
        name=name.strip(),
        brewer_id=brewer_id or None,
        grinder_id=grinder_id or None,
        paper_id=paper_id.strip() or None,
        water_recipe_id=water_recipe_id or None,
        brew_method_id=brew_method_id,
    )
    db.add(setup)
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


@router.get("/setups/{setup_id}/edit", response_class=HTMLResponse)
async def edit_setup_wizard(
    request: Request,
    setup_id: str,
    db: Session = Depends(get_db),
):
    """Show the brew setup assembly wizard pre-filled for editing."""
    setup = (
        db.query(BrewSetup)
        .options(
            joinedload(BrewSetup.grinder),
            joinedload(BrewSetup.brewer),
            joinedload(BrewSetup.paper),
            joinedload(BrewSetup.water_recipe),
            joinedload(BrewSetup.brew_method),
        )
        .filter(BrewSetup.id == setup_id)
        .first()
    )
    if not setup:
        return RedirectResponse(url="/equipment", status_code=303)

    ctx = _get_wizard_context(db)
    return templates.TemplateResponse(
        request,
        "equipment/_setup_wizard.html",
        {**ctx, "setup": setup, "edit_mode": True},
    )


@router.post("/setups/{setup_id}", response_class=HTMLResponse)
async def update_setup(
    request: Request,
    setup_id: str,
    name: str = Form(...),
    brewer_id: str = Form(...),
    grinder_id: str = Form(...),
    paper_id: str = Form(""),
    water_recipe_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Update an existing brew setup."""
    setup = db.query(BrewSetup).filter(BrewSetup.id == setup_id).first()
    if not setup:
        return RedirectResponse(url="/equipment", status_code=303)

    # Resolve brew_method_id from brewer
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    brew_method_id = setup.brew_method_id  # keep existing if unresolvable
    if brewer and brewer.methods:
        brew_method_id = brewer.methods[0].id
    elif not brew_method_id:
        first_method = db.query(BrewMethod).order_by(BrewMethod.name).first()
        if first_method:
            brew_method_id = first_method.id

    setup.name = name.strip()
    setup.brewer_id = brewer_id or None
    setup.grinder_id = grinder_id or None
    setup.paper_id = paper_id.strip() or None
    setup.water_recipe_id = water_recipe_id or None
    setup.brew_method_id = brew_method_id
    db.commit()

    return RedirectResponse(url="/equipment", status_code=303)


# ── Retire / Restore routes ──────────────────────────────────────────────────


def _auto_retire_setups_for_grinder(db: Session, grinder_id: str) -> None:
    """Auto-retire all active BrewSetups that use this grinder."""
    db.query(BrewSetup).filter(
        BrewSetup.grinder_id == grinder_id,
        BrewSetup.is_retired.is_(False),
    ).update({"is_retired": True}, synchronize_session=False)


def _auto_retire_setups_for_brewer(db: Session, brewer_id: str) -> None:
    """Auto-retire all active BrewSetups that use this brewer."""
    db.query(BrewSetup).filter(
        BrewSetup.brewer_id == brewer_id,
        BrewSetup.is_retired.is_(False),
    ).update({"is_retired": True}, synchronize_session=False)


def _auto_retire_setups_for_paper(db: Session, paper_id: str) -> None:
    """Auto-retire all active BrewSetups that use this paper."""
    db.query(BrewSetup).filter(
        BrewSetup.paper_id == paper_id,
        BrewSetup.is_retired.is_(False),
    ).update({"is_retired": True}, synchronize_session=False)


def _auto_retire_setups_for_water_recipe(db: Session, water_recipe_id: str) -> None:
    """Auto-retire all active BrewSetups that use this water recipe."""
    db.query(BrewSetup).filter(
        BrewSetup.water_recipe_id == water_recipe_id,
        BrewSetup.is_retired.is_(False),
    ).update({"is_retired": True}, synchronize_session=False)


@router.post("/grinders/{grinder_id}/retire", response_class=HTMLResponse)
async def retire_grinder(
    request: Request,
    grinder_id: str,
    db: Session = Depends(get_db),
):
    """Retire a grinder and auto-retire all setups using it."""
    grinder = db.query(Grinder).filter(Grinder.id == grinder_id).first()
    if grinder:
        grinder.is_retired = True
        _auto_retire_setups_for_grinder(db, grinder_id)
        db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/grinders/{grinder_id}/restore", response_class=HTMLResponse)
async def restore_grinder(
    request: Request,
    grinder_id: str,
    db: Session = Depends(get_db),
):
    """Restore a retired grinder (does not auto-restore setups)."""
    grinder = db.query(Grinder).filter(Grinder.id == grinder_id).first()
    if grinder:
        grinder.is_retired = False
        db.commit()
    return RedirectResponse(url="/equipment?show_retired=true", status_code=303)


@router.post("/brewers/{brewer_id}/retire", response_class=HTMLResponse)
async def retire_brewer(
    request: Request,
    brewer_id: str,
    db: Session = Depends(get_db),
):
    """Retire a brewer and auto-retire all setups using it."""
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    if brewer:
        brewer.is_retired = True
        _auto_retire_setups_for_brewer(db, brewer_id)
        db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/brewers/{brewer_id}/restore", response_class=HTMLResponse)
async def restore_brewer(
    request: Request,
    brewer_id: str,
    db: Session = Depends(get_db),
):
    """Restore a retired brewer (does not auto-restore setups)."""
    brewer = db.query(Brewer).filter(Brewer.id == brewer_id).first()
    if brewer:
        brewer.is_retired = False
        db.commit()
    return RedirectResponse(url="/equipment?show_retired=true", status_code=303)


@router.post("/papers/{paper_id}/retire", response_class=HTMLResponse)
async def retire_paper(
    request: Request,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Retire a paper/filter and auto-retire all setups using it."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper:
        paper.is_retired = True
        _auto_retire_setups_for_paper(db, paper_id)
        db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/papers/{paper_id}/restore", response_class=HTMLResponse)
async def restore_paper(
    request: Request,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Restore a retired paper/filter (does not auto-restore setups)."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper:
        paper.is_retired = False
        db.commit()
    return RedirectResponse(url="/equipment?show_retired=true", status_code=303)


@router.post("/water-recipes/{recipe_id}/retire", response_class=HTMLResponse)
async def retire_water_recipe(
    request: Request,
    recipe_id: str,
    db: Session = Depends(get_db),
):
    """Retire a water recipe and auto-retire all setups using it."""
    recipe = db.query(WaterRecipe).filter(WaterRecipe.id == recipe_id).first()
    if recipe:
        recipe.is_retired = True
        _auto_retire_setups_for_water_recipe(db, recipe_id)
        db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/water-recipes/{recipe_id}/restore", response_class=HTMLResponse)
async def restore_water_recipe(
    request: Request,
    recipe_id: str,
    db: Session = Depends(get_db),
):
    """Restore a retired water recipe (does not auto-restore setups)."""
    recipe = db.query(WaterRecipe).filter(WaterRecipe.id == recipe_id).first()
    if recipe:
        recipe.is_retired = False
        db.commit()
    return RedirectResponse(url="/equipment?show_retired=true", status_code=303)


@router.post("/setups/{setup_id}/retire", response_class=HTMLResponse)
async def retire_setup(
    request: Request,
    setup_id: str,
    db: Session = Depends(get_db),
):
    """Retire a brew setup directly."""
    setup = db.query(BrewSetup).filter(BrewSetup.id == setup_id).first()
    if setup:
        setup.is_retired = True
        db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/setups/{setup_id}/restore", response_class=HTMLResponse)
async def restore_setup(
    request: Request,
    setup_id: str,
    db: Session = Depends(get_db),
):
    """Restore a retired brew setup."""
    setup = db.query(BrewSetup).filter(BrewSetup.id == setup_id).first()
    if setup:
        setup.is_retired = False
        db.commit()
    return RedirectResponse(url="/equipment?show_retired=true", status_code=303)
