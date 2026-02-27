"""Tests for SimilarityService — bean similarity matching for transfer learning."""

from app.models.bean import Bean
from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.services.similarity import SimilarityService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_bean(db, name, process=None, variety=None):
    bean = Bean(name=name, process=process, variety=variety)
    db.add(bean)
    db.flush()
    return bean


def make_brew_method(db, name):
    method = db.query(BrewMethod).filter(BrewMethod.name == name).first()
    if not method:
        method = BrewMethod(name=name)
        db.add(method)
        db.flush()
    return method


def make_brew_setup(db, method_id):
    setup = BrewSetup(brew_method_id=method_id)
    db.add(setup)
    db.flush()
    return setup


def make_espresso_measurement(db, bean_id, brew_setup_id=None, taste=7.0):
    """Create a minimal espresso-compatible measurement."""
    m = Measurement(
        bean_id=bean_id,
        brew_setup_id=brew_setup_id,
        grind_setting=18.0,
        temperature=91.0,
        preinfusion_pressure_pct=70.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
    )
    db.add(m)
    db.flush()
    return m


def make_pour_over_measurement(db, bean_id, brew_setup_id, taste=7.0):
    """Create a minimal pour-over measurement (no espresso-specific params)."""
    m = Measurement(
        bean_id=bean_id,
        brew_setup_id=brew_setup_id,
        grind_setting=28.0,
        temperature=94.0,
        preinfusion_pressure_pct=0.0,  # unused but non-null in schema
        dose_in=15.0,
        target_yield=250.0,
        saturation="no",
        taste=taste,
    )
    db.add(m)
    db.flush()
    return m


# ---------------------------------------------------------------------------
# SimilarityService.find_similar_beans
# ---------------------------------------------------------------------------


def test_find_similar_beans_empty_when_target_has_no_process(db_session):
    """Returns empty list when target bean has no process."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process=None, variety="Bourbon")
    other = make_bean(db_session, "Other", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, other.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert result == []


def test_find_similar_beans_empty_when_target_has_no_variety(db_session):
    """Returns empty list when target bean has no variety."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety=None)
    other = make_bean(db_session, "Other", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, other.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert result == []


def test_find_similar_beans_empty_when_no_match(db_session):
    """Returns empty list when no beans share both process and variety."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    other = make_bean(db_session, "Other", process="washed", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, other.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert result == []


def test_find_similar_beans_returns_matching_beans(db_session):
    """Returns similar beans with sufficient measurements."""
    svc = SimilarityService()
    target = make_bean(db_session, "New Natural Bourbon", process="natural", variety="Bourbon")
    similar = make_bean(db_session, "Old Natural Bourbon", process="natural", variety="Bourbon")
    for _ in range(5):
        make_espresso_measurement(db_session, similar.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert len(result) == 1
    assert result[0].bean_id == similar.id
    assert result[0].bean_name == "Old Natural Bourbon"
    assert result[0].measurement_count == 5


def test_find_similar_beans_excludes_beans_below_min_measurements(db_session):
    """Excludes beans with fewer than min_measurements."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    low_data = make_bean(db_session, "LowData", process="natural", variety="Bourbon")
    for _ in range(2):  # only 2, below default 3
        make_espresso_measurement(db_session, low_data.id)
    result = svc.find_similar_beans(target, "espresso", db_session, min_measurements=3)
    assert result == []


def test_find_similar_beans_excludes_target_itself(db_session):
    """Does not include the target bean in results, even if it matches itself."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    for _ in range(5):
        make_espresso_measurement(db_session, target.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert result == []


def test_find_similar_beans_requires_both_fields_to_match(db_session):
    """Only matches beans where BOTH process AND variety match."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    same_process_only = make_bean(db_session, "SameProcess", process="natural", variety="Geisha")
    same_variety_only = make_bean(db_session, "SameVariety", process="washed", variety="Bourbon")
    for b in [same_process_only, same_variety_only]:
        for _ in range(5):
            make_espresso_measurement(db_session, b.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert result == []


def test_find_similar_beans_orders_by_measurement_count_desc(db_session):
    """Orders similar beans by measurement count descending."""
    svc = SimilarityService()
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    bean_a = make_bean(db_session, "BeanA", process="natural", variety="Bourbon")
    bean_b = make_bean(db_session, "BeanB", process="natural", variety="Bourbon")
    # Bean B has more measurements
    for _ in range(3):
        make_espresso_measurement(db_session, bean_a.id)
    for _ in range(7):
        make_espresso_measurement(db_session, bean_b.id)
    result = svc.find_similar_beans(target, "espresso", db_session)
    assert len(result) == 2
    assert result[0].bean_id == bean_b.id  # more measurements first
    assert result[1].bean_id == bean_a.id


# ---------------------------------------------------------------------------
# SimilarityService.count_method_measurements
# ---------------------------------------------------------------------------


def test_count_method_measurements_espresso_legacy(db_session):
    """Counts legacy espresso measurements (NULL brew_setup_id) as espresso."""
    svc = SimilarityService()
    bean = make_bean(db_session, "Bean")
    for _ in range(4):
        make_espresso_measurement(db_session, bean.id, brew_setup_id=None)
    count = svc.count_method_measurements(bean.id, "espresso", db_session)
    assert count == 4


def test_count_method_measurements_pour_over(db_session):
    """Counts pour-over measurements via brew_setup → brew_method."""
    svc = SimilarityService()
    bean = make_bean(db_session, "Bean")
    method = make_brew_method(db_session, "pour-over")
    setup = make_brew_setup(db_session, method.id)
    for _ in range(3):
        make_pour_over_measurement(db_session, bean.id, setup.id)
    count = svc.count_method_measurements(bean.id, "pour-over", db_session)
    assert count == 3
    # Should not count espresso measurements
    espresso_count = svc.count_method_measurements(bean.id, "espresso", db_session)
    assert espresso_count == 0
