"""Tests for equipment CRUD endpoints — grinders, brewers, papers, water recipes."""

import pytest

from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.equipment import Brewer, Grinder, Paper, WaterRecipe


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def espresso_method(db_session):
    """Create (or reuse) the Espresso BrewMethod."""
    method = db_session.query(BrewMethod).filter(BrewMethod.name == "Espresso").first()
    if not method:
        method = BrewMethod(name="Espresso")
        db_session.add(method)
        db_session.commit()
        db_session.refresh(method)
    return method


@pytest.fixture()
def sample_grinder(db_session):
    """Create a sample stepped grinder."""
    grinder = Grinder(
        name="Comandante C40",
        dial_type="stepped",
        step_size=0.5,
        min_value=1.0,
        max_value=40.0,
    )
    db_session.add(grinder)
    db_session.commit()
    db_session.refresh(grinder)
    return grinder


@pytest.fixture()
def sample_brewer(db_session, espresso_method):
    """Create a sample brewer with an associated BrewMethod."""
    brewer = Brewer(name="Rancilio Silvia")
    brewer.methods = [espresso_method]
    db_session.add(brewer)
    db_session.commit()
    db_session.refresh(brewer)
    return brewer


@pytest.fixture()
def sample_paper(db_session):
    """Create a sample paper with description."""
    paper = Paper(name="Cafec Abaca T-90", description="Bleached, light roast filter")
    db_session.add(paper)
    db_session.commit()
    db_session.refresh(paper)
    return paper


@pytest.fixture()
def sample_water_recipe(db_session):
    """Create a sample water recipe with some mineral values."""
    recipe = WaterRecipe(
        name="Third Wave Water Classic Light",
        notes="Mixed in 1 gallon distilled",
        gh=65.0,
        kh=40.0,
    )
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    return recipe


# ── Equipment page ─────────────────────────────────────────────────────────


def test_equipment_page_loads(client):
    """GET /equipment returns 200 with Equipment in page."""
    response = client.get("/equipment")
    assert response.status_code == 200
    assert "Equipment" in response.text


def test_equipment_page_shows_counts(
    client, sample_grinder, sample_brewer, sample_paper, sample_water_recipe
):
    """Equipment page shows count badges for all sections."""
    response = client.get("/equipment")
    assert response.status_code == 200
    assert "Grinders" in response.text
    assert "Brewers" in response.text
    assert "Papers" in response.text
    assert "Water Recipes" in response.text


# ── Grinder tests ──────────────────────────────────────────────────────────


def test_create_grinder_stepped(client, db_session):
    """POST /equipment/grinders with stepped config creates grinder in DB."""
    response = client.post(
        "/equipment/grinders",
        data={
            "name": "Comandante C40",
            "dial_type": "stepped",
            "step_size": "1",
            "min_value": "1",
            "max_value": "40",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    grinder = db_session.query(Grinder).filter(Grinder.name == "Comandante C40").first()
    assert grinder is not None
    assert grinder.dial_type == "stepped"
    assert grinder.step_size == 1.0
    assert grinder.min_value == 1.0
    assert grinder.max_value == 40.0


def test_create_grinder_stepless(client, db_session):
    """POST /equipment/grinders with stepless config creates grinder."""
    response = client.post(
        "/equipment/grinders",
        data={
            "name": "Lagom P64",
            "dial_type": "stepless",
            "min_value": "0",
            "max_value": "100",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    grinder = db_session.query(Grinder).filter(Grinder.name == "Lagom P64").first()
    assert grinder is not None
    assert grinder.dial_type == "stepless"
    assert grinder.step_size is None


def test_edit_grinder(client, sample_grinder, db_session):
    """POST /equipment/grinders/{id} updates name and dial config."""
    response = client.post(
        f"/equipment/grinders/{sample_grinder.id}",
        data={
            "name": "Comandante C40 MK4",
            "dial_type": "stepped",
            "step_size": "0.5",
            "min_value": "0",
            "max_value": "50",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Grinder).filter(Grinder.id == sample_grinder.id).first()
    assert updated.name == "Comandante C40 MK4"
    assert updated.max_value == 50.0


def test_edit_grinder_form(client, sample_grinder):
    """GET /equipment/grinders/{id}/edit returns form with HX-Request."""
    response = client.get(
        f"/equipment/grinders/{sample_grinder.id}/edit",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Comandante C40" in response.text


# ── Brewer tests ───────────────────────────────────────────────────────────


def test_create_brewer_with_methods(client, db_session, espresso_method):
    """POST /equipment/brewers with method_ids creates brewer with associations."""
    response = client.post(
        "/equipment/brewers",
        data={
            "name": "Rancilio Silvia",
            "method_ids": [espresso_method.id],
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    brewer = db_session.query(Brewer).filter(Brewer.name == "Rancilio Silvia").first()
    assert brewer is not None
    assert len(brewer.methods) == 1
    assert brewer.methods[0].id == espresso_method.id


def test_edit_brewer(client, sample_brewer, db_session):
    """POST /equipment/brewers/{id} updates name."""
    response = client.post(
        f"/equipment/brewers/{sample_brewer.id}",
        data={
            "name": "Rancilio Silvia V6",
            "method_ids": [],
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Brewer).filter(Brewer.id == sample_brewer.id).first()
    assert updated.name == "Rancilio Silvia V6"
    assert updated.methods == []


def test_edit_brewer_form(client, sample_brewer):
    """GET /equipment/brewers/{id}/edit returns form with HX-Request."""
    response = client.get(
        f"/equipment/brewers/{sample_brewer.id}/edit",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Rancilio Silvia" in response.text


# ── Paper tests ────────────────────────────────────────────────────────────


def test_create_paper(client, db_session):
    """POST /equipment/papers creates a paper in DB."""
    response = client.post(
        "/equipment/papers",
        data={"name": "Hario V60 02"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    paper = db_session.query(Paper).filter(Paper.name == "Hario V60 02").first()
    assert paper is not None
    assert paper.description is None


def test_create_paper_with_description(client, db_session):
    """POST /equipment/papers with description stores it."""
    response = client.post(
        "/equipment/papers",
        data={"name": "Cafec Abaca", "description": "Bleached abaca fiber"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    paper = db_session.query(Paper).filter(Paper.name == "Cafec Abaca").first()
    assert paper is not None
    assert paper.description == "Bleached abaca fiber"


def test_edit_paper(client, sample_paper, db_session):
    """POST /equipment/papers/{id} updates name and description."""
    response = client.post(
        f"/equipment/papers/{sample_paper.id}",
        data={"name": "Cafec Abaca T-100", "description": "Updated description"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Paper).filter(Paper.id == sample_paper.id).first()
    assert updated.name == "Cafec Abaca T-100"
    assert updated.description == "Updated description"


def test_edit_paper_form(client, sample_paper):
    """GET /equipment/papers/{id}/edit returns form with HX-Request."""
    response = client.get(
        f"/equipment/papers/{sample_paper.id}/edit",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Cafec Abaca T-90" in response.text


# ── Water recipe tests ─────────────────────────────────────────────────────


def test_create_water_recipe_basic(client, db_session):
    """POST /equipment/water-recipes with name + notes creates recipe."""
    response = client.post(
        "/equipment/water-recipes",
        data={"name": "Tap Water", "notes": "Filtered"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    recipe = db_session.query(WaterRecipe).filter(WaterRecipe.name == "Tap Water").first()
    assert recipe is not None
    assert recipe.notes == "Filtered"
    assert recipe.gh is None
    assert recipe.kh is None


def test_create_water_recipe_with_minerals(client, db_session):
    """POST /equipment/water-recipes with all 7 mineral fields stores them."""
    response = client.post(
        "/equipment/water-recipes",
        data={
            "name": "Perfect Espresso Water",
            "notes": "SCA target profile",
            "gh": "150",
            "kh": "75",
            "ca": "70",
            "mg": "10",
            "na": "10",
            "cl": "80",
            "so4": "60",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    recipe = (
        db_session.query(WaterRecipe).filter(WaterRecipe.name == "Perfect Espresso Water").first()
    )
    assert recipe is not None
    assert recipe.gh == 150.0
    assert recipe.kh == 75.0
    assert recipe.ca == 70.0
    assert recipe.mg == 10.0
    assert recipe.na == 10.0
    assert recipe.cl == 80.0
    assert recipe.so4 == 60.0


def test_edit_water_recipe(client, sample_water_recipe, db_session):
    """POST /equipment/water-recipes/{id} updates name, notes, and minerals."""
    response = client.post(
        f"/equipment/water-recipes/{sample_water_recipe.id}",
        data={
            "name": "TWW Classic Updated",
            "notes": "New notes",
            "gh": "70",
            "kh": "45",
            "ca": "",
            "mg": "",
            "na": "",
            "cl": "",
            "so4": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(WaterRecipe).filter(WaterRecipe.id == sample_water_recipe.id).first()
    assert updated.name == "TWW Classic Updated"
    assert updated.notes == "New notes"
    assert updated.gh == 70.0
    assert updated.kh == 45.0
    assert updated.ca is None
    assert updated.mg is None


def test_edit_water_recipe_form(client, sample_water_recipe):
    """GET /equipment/water-recipes/{id}/edit returns form with HX-Request."""
    response = client.get(
        f"/equipment/water-recipes/{sample_water_recipe.id}/edit",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Third Wave Water Classic Light" in response.text


# ── Brew Setup fixture ────────────────────────────────────────────────────


@pytest.fixture()
def sample_setup(
    db_session, sample_grinder, sample_brewer, sample_paper, sample_water_recipe, espresso_method
):
    """Create a brew setup using all equipment components."""
    setup = BrewSetup(
        name="My Espresso Setup",
        brew_method_id=espresso_method.id,
        grinder_id=sample_grinder.id,
        brewer_id=sample_brewer.id,
        paper_id=sample_paper.id,
        water_recipe_id=sample_water_recipe.id,
    )
    db_session.add(setup)
    db_session.commit()
    db_session.refresh(setup)
    return setup


# ── Retire / Restore — Grinder ───────────────────────────────────────────


def test_retire_grinder(client, sample_grinder, db_session):
    """POST /equipment/grinders/{id}/retire sets is_retired=True."""
    response = client.post(
        f"/equipment/grinders/{sample_grinder.id}/retire",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Grinder).filter(Grinder.id == sample_grinder.id).first()
    assert updated.is_retired is True


def test_restore_grinder(client, sample_grinder, db_session):
    """POST /equipment/grinders/{id}/restore sets is_retired=False."""
    sample_grinder.is_retired = True
    db_session.commit()

    response = client.post(
        f"/equipment/grinders/{sample_grinder.id}/restore",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Grinder).filter(Grinder.id == sample_grinder.id).first()
    assert updated.is_retired is False


def test_retire_grinder_cascades_to_setups(client, sample_setup, db_session):
    """Retiring a grinder auto-retires all setups using that grinder."""
    grinder_id = sample_setup.grinder_id
    assert sample_setup.is_retired is False

    client.post(f"/equipment/grinders/{grinder_id}/retire", follow_redirects=False)

    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert setup.is_retired is True


def test_restore_grinder_does_not_auto_restore_setups(client, sample_setup, db_session):
    """Restoring a grinder does NOT auto-restore previously retired setups."""
    grinder_id = sample_setup.grinder_id
    # First retire the grinder (which auto-retires the setup)
    client.post(f"/equipment/grinders/{grinder_id}/retire", follow_redirects=False)
    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert setup.is_retired is True

    # Now restore the grinder
    client.post(f"/equipment/grinders/{grinder_id}/restore", follow_redirects=False)
    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    # Setup remains retired — user must restore it manually
    assert setup.is_retired is True


# ── Retire / Restore — Brewer ────────────────────────────────────────────


def test_retire_brewer(client, sample_brewer, db_session):
    """POST /equipment/brewers/{id}/retire sets is_retired=True."""
    response = client.post(
        f"/equipment/brewers/{sample_brewer.id}/retire",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Brewer).filter(Brewer.id == sample_brewer.id).first()
    assert updated.is_retired is True


def test_restore_brewer(client, sample_brewer, db_session):
    """POST /equipment/brewers/{id}/restore sets is_retired=False."""
    sample_brewer.is_retired = True
    db_session.commit()

    response = client.post(
        f"/equipment/brewers/{sample_brewer.id}/restore",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Brewer).filter(Brewer.id == sample_brewer.id).first()
    assert updated.is_retired is False


def test_retire_brewer_cascades_to_setups(client, sample_setup, db_session):
    """Retiring a brewer auto-retires all setups using that brewer."""
    brewer_id = sample_setup.brewer_id
    client.post(f"/equipment/brewers/{brewer_id}/retire", follow_redirects=False)

    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert setup.is_retired is True


# ── Retire / Restore — Paper ─────────────────────────────────────────────


def test_retire_paper(client, sample_paper, db_session):
    """POST /equipment/papers/{id}/retire sets is_retired=True."""
    response = client.post(
        f"/equipment/papers/{sample_paper.id}/retire",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Paper).filter(Paper.id == sample_paper.id).first()
    assert updated.is_retired is True


def test_restore_paper(client, sample_paper, db_session):
    """POST /equipment/papers/{id}/restore sets is_retired=False."""
    sample_paper.is_retired = True
    db_session.commit()

    response = client.post(
        f"/equipment/papers/{sample_paper.id}/restore",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Paper).filter(Paper.id == sample_paper.id).first()
    assert updated.is_retired is False


def test_retire_paper_cascades_to_setups(client, sample_setup, db_session):
    """Retiring a paper auto-retires all setups using that paper."""
    paper_id = sample_setup.paper_id
    client.post(f"/equipment/papers/{paper_id}/retire", follow_redirects=False)

    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert setup.is_retired is True


# ── Retire / Restore — Water Recipe ─────────────────────────────────────


def test_retire_water_recipe(client, sample_water_recipe, db_session):
    """POST /equipment/water-recipes/{id}/retire sets is_retired=True."""
    response = client.post(
        f"/equipment/water-recipes/{sample_water_recipe.id}/retire",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(WaterRecipe).filter(WaterRecipe.id == sample_water_recipe.id).first()
    assert updated.is_retired is True


def test_restore_water_recipe(client, sample_water_recipe, db_session):
    """POST /equipment/water-recipes/{id}/restore sets is_retired=False."""
    sample_water_recipe.is_retired = True
    db_session.commit()

    response = client.post(
        f"/equipment/water-recipes/{sample_water_recipe.id}/restore",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(WaterRecipe).filter(WaterRecipe.id == sample_water_recipe.id).first()
    assert updated.is_retired is False


def test_retire_water_recipe_cascades_to_setups(client, sample_setup, db_session):
    """Retiring a water recipe auto-retires all setups using it."""
    recipe_id = sample_setup.water_recipe_id
    client.post(f"/equipment/water-recipes/{recipe_id}/retire", follow_redirects=False)

    db_session.expire_all()
    setup = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert setup.is_retired is True


# ── Retire / Restore — Brew Setup ────────────────────────────────────────


def test_retire_setup(client, sample_setup, db_session):
    """POST /equipment/setups/{id}/retire sets is_retired=True on the setup."""
    response = client.post(
        f"/equipment/setups/{sample_setup.id}/retire",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert updated.is_retired is True


def test_restore_setup(client, sample_setup, db_session):
    """POST /equipment/setups/{id}/restore sets is_retired=False."""
    sample_setup.is_retired = True
    db_session.commit()

    response = client.post(
        f"/equipment/setups/{sample_setup.id}/restore",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(BrewSetup).filter(BrewSetup.id == sample_setup.id).first()
    assert updated.is_retired is False


# ── Show retired toggle ───────────────────────────────────────────────────


def test_retired_equipment_hidden_by_default(client, sample_grinder, db_session):
    """Retired grinder is NOT shown on the default equipment page as a card."""
    sample_grinder.is_retired = True
    db_session.commit()

    response = client.get("/equipment")
    assert response.status_code == 200
    # When no active (non-retired) grinders exist, the grinder list shows the empty state
    assert "No grinders yet" in response.text


def test_retired_equipment_shown_with_toggle(client, sample_grinder, db_session):
    """Retired grinder IS shown as a card when show_retired=true query param is set."""
    sample_grinder.is_retired = True
    db_session.commit()

    response = client.get("/equipment?show_retired=true")
    assert response.status_code == 200
    # When show_retired=true, the retired grinder card is rendered
    assert "Comandante C40" in response.text
    assert "Retired" in response.text


# ── Wizard excludes retired equipment ────────────────────────────────────


def test_wizard_excludes_retired_grinder(client, sample_grinder, db_session):
    """Brew setup wizard does not offer retired grinders for selection."""
    sample_grinder.is_retired = True
    db_session.commit()

    response = client.get("/equipment/setups/new")
    assert response.status_code == 200
    # Retired grinder should not appear in wizard step options
    assert "Comandante C40" not in response.text


def test_wizard_excludes_retired_brewer(client, sample_brewer, db_session):
    """Brew setup wizard does not offer retired brewers for selection."""
    sample_brewer.is_retired = True
    db_session.commit()

    response = client.get("/equipment/setups/new")
    assert response.status_code == 200
    assert "Rancilio Silvia" not in response.text


# ── Brew page setup selection ─────────────────────────────────────────────


def test_brew_page_set_setup_cookie(client, sample_setup):
    """POST /brew/set-setup sets active_setup_id cookie."""
    response = client.post(
        "/brew/set-setup",
        data={"setup_id": sample_setup.id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "active_setup_id" in response.cookies


def test_brew_page_shows_active_setup(client, sample_setup):
    """GET /brew shows active setup name when cookie is set."""
    # Set the active setup cookie
    client.cookies.set("active_setup_id", sample_setup.id)

    response = client.get("/brew")
    assert response.status_code == 200
    assert "My Espresso Setup" in response.text


def test_brew_page_set_setup_ignores_retired(client, sample_setup, db_session):
    """POST /brew/set-setup does not set cookie for a retired setup."""
    sample_setup.is_retired = True
    db_session.commit()

    response = client.post(
        "/brew/set-setup",
        data={"setup_id": sample_setup.id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    # Cookie should not be set (or not contain the retired setup id)
    assert "active_setup_id" not in response.cookies


def test_brew_page_retired_setup_not_in_selector(client, sample_setup, db_session):
    """Retired setups do not appear in the brew page setup selector."""
    sample_setup.is_retired = True
    db_session.commit()

    response = client.get("/brew")
    assert response.status_code == 200
    assert "My Espresso Setup" not in response.text


# ── Brewer capability CRUD tests ──────────────────────────────────────────


def test_create_brewer_with_capability_fields(client, db_session):
    """POST /equipment/brewers with capability fields stores them in DB."""
    response = client.post(
        "/equipment/brewers",
        data={
            "name": "Decent DE1",
            "temp_control_type": "profiling",
            "temp_min": "85",
            "temp_max": "96",
            "temp_step": "0.5",
            "preinfusion_type": "programmable",
            "preinfusion_max_time": "60",
            "pressure_control_type": "programmable",
            "pressure_min": "2",
            "pressure_max": "9",
            "flow_control_type": "programmable",
            "has_bloom": "true",
            "stop_mode": "gravimetric",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    brewer = db_session.query(Brewer).filter(Brewer.name == "Decent DE1").first()
    assert brewer is not None
    assert brewer.temp_control_type == "profiling"
    assert brewer.temp_min == 85.0
    assert brewer.temp_max == 96.0
    assert brewer.temp_step == 0.5
    assert brewer.preinfusion_type == "programmable"
    assert brewer.preinfusion_max_time == 60.0
    assert brewer.pressure_control_type == "programmable"
    assert brewer.pressure_min == 2.0
    assert brewer.pressure_max == 9.0
    assert brewer.flow_control_type == "programmable"
    assert brewer.has_bloom is True
    assert brewer.stop_mode == "gravimetric"


def test_create_brewer_capability_defaults(client, db_session):
    """POST /equipment/brewers with only name uses safe defaults for capability fields."""
    response = client.post(
        "/equipment/brewers",
        data={"name": "Hario V60"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    brewer = db_session.query(Brewer).filter(Brewer.name == "Hario V60").first()
    assert brewer is not None
    assert brewer.temp_control_type == "none"
    assert brewer.preinfusion_type == "none"
    assert brewer.pressure_control_type == "fixed"
    assert brewer.flow_control_type == "none"
    assert brewer.has_bloom is False
    assert brewer.stop_mode == "manual"
    assert brewer.temp_min is None
    assert brewer.temp_max is None


def test_edit_brewer_updates_capability_fields(client, sample_brewer, db_session):
    """POST /equipment/brewers/{id} updates capability fields correctly."""
    response = client.post(
        f"/equipment/brewers/{sample_brewer.id}",
        data={
            "name": sample_brewer.name,
            "temp_control_type": "pid",
            "temp_min": "88",
            "temp_max": "96",
            "temp_step": "1",
            "preinfusion_type": "timed",
            "preinfusion_max_time": "10",
            "pressure_control_type": "opv_adjustable",
            "pressure_min": "",
            "pressure_max": "",
            "flow_control_type": "none",
            "stop_mode": "volumetric",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Brewer).filter(Brewer.id == sample_brewer.id).first()
    assert updated.temp_control_type == "pid"
    assert updated.temp_min == 88.0
    assert updated.temp_max == 96.0
    assert updated.temp_step == 1.0
    assert updated.preinfusion_type == "timed"
    assert updated.preinfusion_max_time == 10.0
    assert updated.pressure_control_type == "opv_adjustable"
    assert updated.pressure_min is None
    assert updated.pressure_max is None
    assert updated.flow_control_type == "none"
    assert updated.stop_mode == "volumetric"


def test_edit_brewer_clears_optional_floats(client, sample_brewer, db_session):
    """Submitting empty strings for float capability fields sets them to None."""
    response = client.post(
        f"/equipment/brewers/{sample_brewer.id}",
        data={
            "name": sample_brewer.name,
            "temp_control_type": "none",
            "temp_min": "",
            "temp_max": "",
            "temp_step": "",
            "preinfusion_type": "none",
            "preinfusion_max_time": "",
            "pressure_control_type": "fixed",
            "pressure_min": "",
            "pressure_max": "",
            "flow_control_type": "none",
            "stop_mode": "manual",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Brewer).filter(Brewer.id == sample_brewer.id).first()
    assert updated.temp_min is None
    assert updated.temp_max is None
    assert updated.temp_step is None
    assert updated.preinfusion_max_time is None
    assert updated.pressure_min is None
    assert updated.pressure_max is None


def test_brewer_card_shows_tier_badge(client, db_session):
    """Equipment page renders a tier badge on the brewer card."""
    # Create a T2 brewer (PID temp control)
    brewer = Brewer(
        name="Rancilio Silvia Pro X",
        temp_control_type="pid",
    )
    db_session.add(brewer)
    db_session.commit()

    response = client.get("/equipment")
    assert response.status_code == 200
    assert "Rancilio Silvia Pro X" in response.text
    assert "T2" in response.text  # tier badge


def test_brewer_form_shows_capability_fields(client, sample_brewer):
    """GET /equipment/brewers/{id}/edit returns form containing capability select fields."""
    response = client.get(
        f"/equipment/brewers/{sample_brewer.id}/edit",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "temp_control_type" in response.text
    assert "preinfusion_type" in response.text
    assert "pressure_control_type" in response.text
    assert "flow_control_type" in response.text
    assert "stop_mode" in response.text
    assert "Advanced Capabilities" in response.text
