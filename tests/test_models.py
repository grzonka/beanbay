"""Tests for Bean and Measurement SQLAlchemy models."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bag import Bag
from app.models.bean import Bean
from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.equipment import Brewer, Grinder, Paper, WaterRecipe
from app.models.measurement import Measurement


def test_create_bean(db_session):
    """Bean is created with UUID id, name, roaster, origin."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db_session.add(bean)
    db_session.flush()

    assert bean.id is not None
    assert len(bean.id) == 36  # UUID format
    assert "-" in bean.id
    assert bean.name == "Test Ethiopian"
    assert bean.roaster == "Onyx"
    assert bean.origin == "Yirgacheffe"
    assert bean.created_at is not None


def test_create_measurement(db_session):
    """Measurement is created with all BayBE params and taste."""
    bean = Bean(name="Test Bean")
    db_session.add(bean)
    db_session.flush()

    measurement = Measurement(
        bean_id=bean.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=8.0,
    )
    db_session.add(measurement)
    db_session.flush()

    assert measurement.id is not None
    assert isinstance(measurement.id, int)
    assert measurement.grind_setting == 20.0
    assert measurement.temperature == 93.0
    assert measurement.preinfusion_pressure_pct == 75.0
    assert measurement.dose_in == 19.0
    assert measurement.target_yield == 40.0
    assert measurement.saturation == "yes"
    assert measurement.taste == 8.0


def test_bean_measurement_relationship(db_session):
    """Bean.measurements relationship works both directions."""
    bean = Bean(name="Relationship Bean")
    db_session.add(bean)
    db_session.flush()

    m1 = Measurement(
        bean_id=bean.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=7.0,
    )
    m2 = Measurement(
        bean_id=bean.id,
        grind_setting=21.0,
        temperature=94.0,
        preinfusion_pressure_pct=80.0,
        dose_in=19.5,
        target_yield=42.0,
        saturation="no",
        taste=8.5,
    )
    db_session.add_all([m1, m2])
    db_session.flush()

    assert len(bean.measurements) == 2
    for m in bean.measurements:
        assert m.bean == bean
        assert m.bean_id == bean.id


def test_measurement_recommendation_id_unique(db_session):
    """recommendation_id has a unique constraint."""
    bean = Bean(name="Unique Test")
    db_session.add(bean)
    db_session.flush()

    params = dict(
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=7.0,
    )

    m1 = Measurement(bean_id=bean.id, recommendation_id="rec-1", **params)
    db_session.add(m1)
    db_session.flush()

    m2 = Measurement(bean_id=bean.id, recommendation_id="rec-1", **params)
    db_session.add(m2)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_measurement_optional_fields(db_session):
    """Optional fields default to None, is_failed defaults to False."""
    bean = Bean(name="Optional Test")
    db_session.add(bean)
    db_session.flush()

    m = Measurement(
        bean_id=bean.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=6.0,
    )
    db_session.add(m)
    db_session.flush()

    assert m.extraction_time is None
    assert m.notes is None
    assert m.is_failed is False
    assert m.acidity is None
    assert m.sweetness is None
    assert m.body is None
    assert m.bitterness is None
    assert m.aroma is None
    assert m.intensity is None


def test_bean_parameter_overrides(db_session):
    """Bean.parameter_overrides stores and retrieves JSON overrides."""
    overrides = {
        "grind_setting": {"min": 18.0, "max": 22.0},
        "temperature": {"min": 90.0, "max": 94.0},
    }
    bean = Bean(name="Override Bean", parameter_overrides=overrides)
    db_session.add(bean)
    db_session.flush()

    assert bean.parameter_overrides is not None
    assert bean.parameter_overrides["grind_setting"]["min"] == 18.0
    assert bean.parameter_overrides["grind_setting"]["max"] == 22.0
    assert bean.parameter_overrides["temperature"]["min"] == 90.0
    assert bean.parameter_overrides["temperature"]["max"] == 94.0


def test_bean_parameter_overrides_default_none(db_session):
    """Bean.parameter_overrides defaults to None when not set."""
    bean = Bean(name="No Override Bean")
    db_session.add(bean)
    db_session.flush()

    assert bean.parameter_overrides is None


# ---------------------------------------------------------------------------
# Phase 13 model tests
# ---------------------------------------------------------------------------


def test_create_brew_method(db_session):
    """BrewMethod is created with UUID id and unique name."""
    bm = BrewMethod(name="V60")
    db_session.add(bm)
    db_session.flush()

    assert bm.id is not None
    assert len(bm.id) == 36
    assert bm.name == "V60"
    assert bm.created_at is not None


def test_brew_method_name_unique(db_session):
    """BrewMethod name has a unique constraint."""
    db_session.add(BrewMethod(name="AeroPress"))
    db_session.flush()

    db_session.add(BrewMethod(name="AeroPress"))
    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_create_grinder(db_session):
    """Grinder is created with UUID id and name."""
    g = Grinder(name="Niche Zero")
    db_session.add(g)
    db_session.flush()

    assert g.id is not None
    assert len(g.id) == 36
    assert g.name == "Niche Zero"
    assert g.created_at is not None


def test_create_brewer(db_session):
    """Brewer is created with UUID id and name."""
    b = Brewer(name="Hario V60")
    db_session.add(b)
    db_session.flush()

    assert b.id is not None
    assert b.name == "Hario V60"


def test_create_paper(db_session):
    """Paper is created with UUID id and name."""
    p = Paper(name="Hario V60 White")
    db_session.add(p)
    db_session.flush()

    assert p.id is not None
    assert p.name == "Hario V60 White"


def test_create_water_recipe(db_session):
    """WaterRecipe is created with name and optional recipe_details."""
    wr = WaterRecipe(name="Peak Water", recipe_details="TDS 80 ppm")
    db_session.add(wr)
    db_session.flush()

    assert wr.id is not None
    assert wr.name == "Peak Water"
    assert wr.recipe_details == "TDS 80 ppm"


def test_create_brew_setup(db_session):
    """BrewSetup requires only a brew_method_id; all equipment FKs are optional."""
    bm = BrewMethod(name="Chemex")
    db_session.add(bm)
    db_session.flush()

    bs = BrewSetup(brew_method_id=bm.id)
    db_session.add(bs)
    db_session.flush()

    assert bs.id is not None
    assert bs.brew_method_id == bm.id
    assert bs.grinder_id is None
    assert bs.brewer_id is None
    assert bs.paper_id is None
    assert bs.water_recipe_id is None


def test_create_brew_setup_full(db_session):
    """BrewSetup with all equipment linked and relationships navigable."""
    bm = BrewMethod(name="Kalita Wave")
    g = Grinder(name="Comandante C40")
    br = Brewer(name="Kalita Wave 155")
    p = Paper(name="Kalita Wave 155 White")
    wr = WaterRecipe(name="Third Wave Water")
    db_session.add_all([bm, g, br, p, wr])
    db_session.flush()

    bs = BrewSetup(
        name="My Kalita Setup",
        brew_method_id=bm.id,
        grinder_id=g.id,
        brewer_id=br.id,
        paper_id=p.id,
        water_recipe_id=wr.id,
    )
    db_session.add(bs)
    db_session.flush()

    assert bs.brew_method.name == "Kalita Wave"
    assert bs.grinder.name == "Comandante C40"
    assert bs.brewer.name == "Kalita Wave 155"
    assert bs.paper.name == "Kalita Wave 155 White"
    assert bs.water_recipe.name == "Third Wave Water"


def test_create_bag(db_session):
    """Bag is created with FK to bean and all optional fields."""
    from datetime import date

    bean = Bean(name="Bag Test Bean")
    db_session.add(bean)
    db_session.flush()

    bag = Bag(
        bean_id=bean.id,
        purchase_date=date(2026, 1, 15),
        cost=18.50,
        weight_grams=250.0,
        notes="First bag",
    )
    db_session.add(bag)
    db_session.flush()

    assert bag.id is not None
    assert bag.bean_id == bean.id
    assert bag.cost == 18.50
    assert bag.weight_grams == 250.0
    assert bag.notes == "First bag"


def test_bean_multiple_bags(db_session):
    """Bean.bags relationship returns all associated bags."""
    bean = Bean(name="Multi-Bag Bean")
    db_session.add(bean)
    db_session.flush()

    bag1 = Bag(bean_id=bean.id, weight_grams=250.0)
    bag2 = Bag(bean_id=bean.id, weight_grams=250.0)
    db_session.add_all([bag1, bag2])
    db_session.flush()

    assert len(bean.bags) == 2
    for bag in bean.bags:
        assert bag.bean == bean


def test_bean_extended_fields(db_session):
    """Bean stores roast_date, process, variety correctly."""
    from datetime import date

    bean = Bean(
        name="Extended Bean",
        roast_date=date(2026, 2, 1),
        process="washed",
        variety="Bourbon",
    )
    db_session.add(bean)
    db_session.flush()

    assert bean.roast_date == date(2026, 2, 1)
    assert bean.process == "washed"
    assert bean.variety == "Bourbon"


def test_bean_extended_fields_nullable(db_session):
    """Bean extended fields (roast_date, process, variety) default to None."""
    bean = Bean(name="Minimal Bean")
    db_session.add(bean)
    db_session.flush()

    assert bean.roast_date is None
    assert bean.process is None
    assert bean.variety is None


def test_measurement_brew_setup_relationship(db_session):
    """Measurement.brew_setup links to BrewSetup and is navigable."""
    bean = Bean(name="Setup Measurement Bean")
    bm = BrewMethod(name="Siphon")
    db_session.add_all([bean, bm])
    db_session.flush()

    bs = BrewSetup(brew_method_id=bm.id)
    db_session.add(bs)
    db_session.flush()

    m = Measurement(
        bean_id=bean.id,
        brew_setup_id=bs.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=8.0,
    )
    db_session.add(m)
    db_session.flush()

    assert m.brew_setup_id == bs.id
    assert m.brew_setup.brew_method.name == "Siphon"


def test_measurement_brew_setup_nullable(db_session):
    """Measurement.brew_setup_id is nullable for backward compatibility."""
    bean = Bean(name="No Setup Bean")
    db_session.add(bean)
    db_session.flush()

    m = Measurement(
        bean_id=bean.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=7.5,
    )
    db_session.add(m)
    db_session.flush()

    assert m.brew_setup_id is None
    assert m.brew_setup is None
