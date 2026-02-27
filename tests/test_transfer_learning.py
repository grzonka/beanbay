"""Tests for TransferLearningService — BayBE campaign seeding via TaskParameter."""

from app.models.bean import Bean
from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.services.similarity import SimilarBean
from app.services.transfer_learning import TransferMetadata, build_transfer_campaign


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_bean(db, name, process=None, variety=None):
    bean = Bean(name=name, process=process, variety=variety)
    db.add(bean)
    db.flush()
    return bean


def make_brew_method(db, name):
    m = db.query(BrewMethod).filter(BrewMethod.name == name).first()
    if not m:
        m = BrewMethod(name=name)
        db.add(m)
        db.flush()
    return m


def make_brew_setup(db, method_id):
    s = BrewSetup(brew_method_id=method_id)
    db.add(s)
    db.flush()
    return s


def make_espresso_measurement(db, bean_id, brew_setup_id=None, taste=7.0):
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


def make_similar_bean(bean_id, bean_name="SimilarBean", count=3):
    return SimilarBean(
        bean_id=bean_id,
        bean_name=bean_name,
        process="natural",
        variety="Bourbon",
        measurement_count=count,
    )


# ---------------------------------------------------------------------------
# Task 4 tests
# ---------------------------------------------------------------------------


def test_build_transfer_campaign_returns_none_when_no_similar_beans(db_session):
    """Returns None when similar_beans list is empty."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    result = build_transfer_campaign(target, [], "espresso", None, db_session)
    assert result is None


def test_build_transfer_campaign_returns_campaign_when_similar_beans_have_data(db_session):
    """Returns (Campaign, TransferMetadata) when similar beans have measurements."""
    target = make_bean(db_session, "NewBean", process="natural", variety="Bourbon")
    source = make_bean(db_session, "OldBean", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, source.id)

    similar = [make_similar_bean(source.id, "OldBean", 3)]
    result = build_transfer_campaign(target, similar, "espresso", None, db_session)
    assert result is not None
    campaign, metadata = result
    assert campaign is not None
    assert isinstance(metadata, TransferMetadata)


def test_returned_campaign_has_task_parameter(db_session):
    """Returned campaign's search space includes a TaskParameter named 'bean_task'."""
    from baybe.parameters import TaskParameter

    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, source.id)

    similar = [make_similar_bean(source.id, "Source", 3)]
    campaign, _ = build_transfer_campaign(target, similar, "espresso", None, db_session)

    param_names = [p.name for p in campaign.searchspace.parameters]
    assert "bean_task" in param_names
    task_param = next(p for p in campaign.searchspace.parameters if p.name == "bean_task")
    assert isinstance(task_param, TaskParameter)


def test_task_parameter_active_values_is_target_bean(db_session):
    """TaskParameter active_values contains only the target bean's ID."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, source.id)

    similar = [make_similar_bean(source.id, "Source", 3)]
    campaign, _ = build_transfer_campaign(target, similar, "espresso", None, db_session)

    task_param = next(p for p in campaign.searchspace.parameters if p.name == "bean_task")
    assert list(task_param.active_values) == [target.id]


def test_campaign_has_preloaded_training_measurements(db_session):
    """Returned campaign has training measurements loaded (not empty)."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    n = 4
    for _ in range(n):
        make_espresso_measurement(db_session, source.id)

    similar = [make_similar_bean(source.id, "Source", n)]
    campaign, metadata = build_transfer_campaign(target, similar, "espresso", None, db_session)

    assert not campaign.measurements.empty
    assert len(campaign.measurements) == n
    assert metadata.total_training_measurements == n


def test_transfer_metadata_contributing_beans(db_session):
    """TransferMetadata.contributing_beans lists the similar beans correctly."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Heirloom Natural", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, source.id)

    similar = [make_similar_bean(source.id, "Heirloom Natural", 3)]
    _, metadata = build_transfer_campaign(target, similar, "espresso", None, db_session)

    assert len(metadata.contributing_beans) == 1
    assert metadata.contributing_beans[0]["bean_id"] == source.id
    assert metadata.contributing_beans[0]["name"] == "Heirloom Natural"


def test_transfer_metadata_total_training_measurements(db_session):
    """TransferMetadata.total_training_measurements matches measurements loaded."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source_a = make_bean(db_session, "SourceA", process="natural", variety="Bourbon")
    source_b = make_bean(db_session, "SourceB", process="natural", variety="Bourbon")
    for _ in range(3):
        make_espresso_measurement(db_session, source_a.id)
    for _ in range(5):
        make_espresso_measurement(db_session, source_b.id)

    similar = [
        make_similar_bean(source_a.id, "SourceA", 3),
        make_similar_bean(source_b.id, "SourceB", 5),
    ]
    _, metadata = build_transfer_campaign(target, similar, "espresso", None, db_session)
    assert metadata.total_training_measurements == 8


def test_build_transfer_campaign_works_for_espresso_method(db_session):
    """Build works for espresso method — legacy (NULL brew_setup_id) measurements included."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    # Legacy espresso measurements (NULL brew_setup_id)
    for _ in range(3):
        make_espresso_measurement(db_session, source.id, brew_setup_id=None)

    similar = [make_similar_bean(source.id, "Source", 3)]
    result = build_transfer_campaign(target, similar, "espresso", None, db_session)
    assert result is not None
    campaign, _ = result
    assert not campaign.measurements.empty


def test_build_transfer_campaign_recommend_executes(db_session):
    """Smoke test: campaign.recommend() executes without error after transfer seeding."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    for i in range(5):
        make_espresso_measurement(db_session, source.id, taste=6.0 + i * 0.5)

    similar = [make_similar_bean(source.id, "Source", 5)]
    campaign, _ = build_transfer_campaign(target, similar, "espresso", None, db_session)

    # Should produce a recommendation for the target bean
    rec_df = campaign.recommend(batch_size=1)
    assert len(rec_df) == 1
    rec = rec_df.iloc[0].to_dict()
    # Should recommend for the target bean's task
    assert rec["bean_task"] == target.id


def test_build_transfer_campaign_returns_none_when_no_training_data(db_session):
    """Returns None when similar_beans exist in list but have no DB measurements."""
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    # Source bean exists but has no measurements in DB
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    # Don't add measurements — similar bean list says count=3 but DB is empty
    similar = [make_similar_bean(source.id, "Source", 3)]
    # Should return None because no actual training data collected
    result = build_transfer_campaign(target, similar, "espresso", None, db_session)
    assert result is None
