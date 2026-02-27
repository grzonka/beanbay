"""Integration tests for transfer learning wire-up in OptimizerService.

Tests that get_or_create_campaign uses TransferLearningService when similar beans
exist, writes .transfer metadata files, and that add_measurement handles bean_task.
"""

from app.models.bean import Bean
from app.models.brew_method import BrewMethod
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.services.optimizer_key import make_campaign_key


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


def make_espresso_measurement(db, bean_id, taste=7.0):
    """Espresso measurement with NULL brew_setup_id (legacy espresso)."""
    m = Measurement(
        bean_id=bean_id,
        brew_setup_id=None,
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
    """Pour-over measurement linked to a brew_setup."""
    m = Measurement(
        bean_id=bean_id,
        brew_setup_id=brew_setup_id,
        grind_setting=28.0,
        temperature=94.0,
        preinfusion_pressure_pct=0.0,
        dose_in=15.0,
        target_yield=250.0,
        saturation="no",
        taste=taste,
    )
    db.add(m)
    db.flush()
    return m


def campaign_key_for(bean, method="espresso", setup_id=None):
    return make_campaign_key(str(bean.id), method, setup_id)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_transfer_learning_activates_when_similar_beans_exist(db_session, optimizer_service):
    """get_or_create_campaign uses transfer learning when similar beans have measurements."""
    source = make_bean(db_session, "Source Natural Bourbon", process="natural", variety="Bourbon")
    target = make_bean(db_session, "Target Natural Bourbon", process="natural", variety="Bourbon")
    # Give source bean enough espresso measurements
    for _ in range(5):
        make_espresso_measurement(db_session, source.id)

    campaign_key = campaign_key_for(target)
    campaign = optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    # Campaign should have pre-loaded training measurements
    assert not campaign.measurements.empty


def test_no_transfer_learning_when_target_has_no_metadata(db_session, optimizer_service):
    """Standard fresh campaign when target bean has no process or variety."""
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    for _ in range(5):
        make_espresso_measurement(db_session, source.id)
    target = make_bean(db_session, "Target No Metadata", process=None, variety=None)

    campaign_key = campaign_key_for(target)
    campaign = optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    # No similar beans — fresh campaign with no measurements
    assert campaign.measurements.empty


def test_no_transfer_learning_when_no_similar_beans(db_session, optimizer_service):
    """Standard fresh campaign when no matching beans exist in DB."""
    target = make_bean(db_session, "Unique Washed Geisha", process="washed", variety="Geisha")

    campaign_key = campaign_key_for(target)
    campaign = optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    assert campaign.measurements.empty


def test_transfer_file_written_when_transfer_learning_activates(db_session, optimizer_service):
    """Transfer metadata is stored in DB when transfer learning activates."""
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    for _ in range(4):
        make_espresso_measurement(db_session, source.id)

    campaign_key = campaign_key_for(target)
    optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    metadata = optimizer_service.get_transfer_metadata(campaign_key)
    assert metadata is not None


def test_no_transfer_file_for_standard_campaign(db_session, optimizer_service):
    """No transfer metadata stored in DB when no transfer learning occurs."""
    target = make_bean(db_session, "Unique Bean", process="washed", variety="Geisha")

    campaign_key = campaign_key_for(target)
    optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    metadata = optimizer_service.get_transfer_metadata(campaign_key)
    assert metadata is None


def test_get_transfer_metadata_returns_dict_for_transfer_campaign(db_session, optimizer_service):
    """get_transfer_metadata returns a dict when a .transfer file exists."""
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    for _ in range(5):
        make_espresso_measurement(db_session, source.id)

    campaign_key = campaign_key_for(target)
    optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    metadata = optimizer_service.get_transfer_metadata(campaign_key)
    assert metadata is not None
    assert "contributing_beans" in metadata
    assert "total_training_measurements" in metadata
    assert len(metadata["contributing_beans"]) == 1
    assert metadata["total_training_measurements"] == 5


def test_get_transfer_metadata_returns_none_for_standard_campaign(db_session, optimizer_service):
    """get_transfer_metadata returns None when no .transfer file exists."""
    target = make_bean(db_session, "Standard Bean", process="washed", variety="Geisha")

    campaign_key = campaign_key_for(target)
    optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    metadata = optimizer_service.get_transfer_metadata(campaign_key)
    assert metadata is None


def test_add_measurement_handles_transfer_campaign(db_session, optimizer_service):
    """add_measurement works for transfer learning campaigns (includes bean_task column)."""
    source = make_bean(db_session, "Source", process="natural", variety="Bourbon")
    target = make_bean(db_session, "Target", process="natural", variety="Bourbon")
    for _ in range(5):
        make_espresso_measurement(db_session, source.id)

    campaign_key = campaign_key_for(target)
    # Create the transfer campaign
    campaign = optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    initial_count = len(campaign.measurements)

    # Record a new measurement for the target bean
    optimizer_service.add_measurement(
        campaign_key,
        {
            "grind_setting": 19.0,
            "temperature": 92.0,
            "preinfusion_pressure_pct": 70.0,
            "dose_in": 19.0,
            "target_yield": 40.0,
            "saturation": "yes",
            "taste": 7.5,
        },
        method="espresso",
        target_bean_id=str(target.id),
    )
    updated_campaign = optimizer_service.get_or_create_campaign(campaign_key, method="espresso")
    assert len(updated_campaign.measurements) == initial_count + 1


def test_add_measurement_works_for_standard_campaign(db_session, optimizer_service):
    """add_measurement works for standard (non-transfer) campaigns."""
    target = make_bean(db_session, "Standard Bean", process="washed", variety="SL28")

    campaign_key = campaign_key_for(target)
    optimizer_service.get_or_create_campaign(campaign_key, method="espresso")
    optimizer_service.add_measurement(
        campaign_key,
        {
            "grind_setting": 19.0,
            "temperature": 92.0,
            "preinfusion_pressure_pct": 70.0,
            "dose_in": 19.0,
            "target_yield": 40.0,
            "saturation": "yes",
            "taste": 7.0,
        },
        method="espresso",
        target_bean_id=str(target.id),
    )
    campaign = optimizer_service.get_or_create_campaign(campaign_key, method="espresso")
    assert len(campaign.measurements) == 1


def test_espresso_and_pour_over_dont_cross_seed(db_session, optimizer_service):
    """Beans with same process+variety but different method don't cross-seed."""
    source = make_bean(db_session, "Source Natural Bourbon", process="natural", variety="Bourbon")
    target = make_bean(db_session, "Target Natural Bourbon", process="natural", variety="Bourbon")

    # Give source bean pour-over measurements only
    method = make_brew_method(db_session, "pour-over")
    setup = make_brew_setup(db_session, method.id)
    for _ in range(5):
        make_pour_over_measurement(db_session, source.id, setup.id)

    # Request an ESPRESSO campaign for target — source has no espresso data
    campaign_key = campaign_key_for(target, method="espresso")
    campaign = optimizer_service.get_or_create_campaign(
        campaign_key, method="espresso", target_bean=target, db=db_session
    )
    # No espresso data from source → fresh campaign with no measurements
    assert campaign.measurements.empty
    assert optimizer_service.get_transfer_metadata(campaign_key) is None
