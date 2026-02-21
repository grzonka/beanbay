"""Tests for Bean and Measurement SQLAlchemy models."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bean import Bean
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
        preinfusion_pct=75.0,
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
    assert measurement.preinfusion_pct == 75.0
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
        preinfusion_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=7.0,
    )
    m2 = Measurement(
        bean_id=bean.id,
        grind_setting=21.0,
        temperature=94.0,
        preinfusion_pct=80.0,
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
        preinfusion_pct=75.0,
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
        preinfusion_pct=75.0,
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
