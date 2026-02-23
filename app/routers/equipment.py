"""Equipment management routes — grinders, brewers, papers, water recipes."""

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brew_method import BrewMethod
from app.models.equipment import Brewer, Grinder, Paper, WaterRecipe

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

    # Counts for badges
    grinder_count = len(grinders)
    brewer_count = len(brewers)
    paper_count = len(papers)
    water_recipe_count = len(water_recipes)

    return templates.TemplateResponse(
        request,
        "equipment/index.html",
        {
            "grinders": grinders,
            "brewers": brewers,
            "papers": papers,
            "water_recipes": water_recipes,
            "brew_methods": brew_methods,
            "grinder_count": grinder_count,
            "brewer_count": brewer_count,
            "paper_count": paper_count,
            "water_recipe_count": water_recipe_count,
            "show_retired": show_retired,
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
    db: Session = Depends(get_db),
):
    """Create a new brewer with optional method associations."""
    form = await request.form()
    method_ids = form.getlist("method_ids")

    brewer = Brewer(name=name.strip())
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
            {"brewer": brewer},
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
        {"brewer": brewer, "brew_methods": brew_methods},
    )


@router.post("/brewers/{brewer_id}", response_class=HTMLResponse)
async def update_brewer(
    request: Request,
    brewer_id: str,
    name: str = Form(...),
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
