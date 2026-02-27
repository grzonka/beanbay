"""Tests for multi-method brewing: campaign key derivation, pour-over params, legacy migration."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.bean import Bean
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.services.optimizer_key import is_legacy_key, make_campaign_key, parse_campaign_key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    """Create a sample bean for brew tests."""
    bean = Bean(name="Multi-Method Bean", roaster="Test Roaster", origin="Ethiopia")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


@pytest.fixture()
def active_client(client, sample_bean):
    """Client with active bean cookie set."""
    client.cookies.set("active_bean_id", sample_bean.id)
    return client


@pytest.fixture()
def sample_brew_method(db_session):
    """Create (or reuse) the Espresso brew method for setup tests."""
    from app.models.brew_method import BrewMethod

    method = db_session.query(BrewMethod).filter(BrewMethod.name == "Espresso").first()
    if not method:
        method = BrewMethod(name="Espresso")
        db_session.add(method)
        db_session.commit()
        db_session.refresh(method)
    return method


@pytest.fixture()
def sample_setup(db_session, sample_brew_method):
    """Create a brew setup linked to the sample brew method."""
    setup = BrewSetup(name="My Espresso Setup", brew_method_id=sample_brew_method.id)
    db_session.add(setup)
    db_session.commit()
    db_session.refresh(setup)
    return setup


# ---------------------------------------------------------------------------
# Campaign key unit tests
# ---------------------------------------------------------------------------


def test_campaign_key_espresso_no_setup():
    """make_campaign_key with espresso and no setup → uses 'none' sentinel."""
    key = make_campaign_key("b1", "espresso", None)
    assert key == "b1__espresso__none"


def test_campaign_key_espresso_with_setup():
    """make_campaign_key with espresso and a setup ID → includes setup ID."""
    key = make_campaign_key("b1", "espresso", "s1")
    assert key == "b1__espresso__s1"


def test_campaign_key_pour_over():
    """make_campaign_key with pour-over method → hyphen preserved in key."""
    key = make_campaign_key("b1", "pour-over", "s1")
    assert key == "b1__pour-over__s1"


def test_parse_campaign_key_roundtrip():
    """parse_campaign_key on a new-format key → returns original components."""
    original_key = make_campaign_key("b1", "espresso", "s1")
    bean_id, method, setup_id = parse_campaign_key(original_key)
    assert bean_id == "b1"
    assert method == "espresso"
    assert setup_id == "s1"


def test_parse_campaign_key_none_sentinel():
    """parse_campaign_key with 'none' setup → returns None for setup_id."""
    key = make_campaign_key("b1", "espresso", None)
    bean_id, method, setup_id = parse_campaign_key(key)
    assert bean_id == "b1"
    assert method == "espresso"
    assert setup_id is None


def test_parse_legacy_key():
    """parse_campaign_key on a legacy bare UUID → defaults to espresso/None."""
    legacy_uuid = str(uuid.uuid4())
    bean_id, method, setup_id = parse_campaign_key(legacy_uuid)
    assert bean_id == legacy_uuid
    assert method == "espresso"
    assert setup_id is None


def test_is_legacy_key_old_format():
    """is_legacy_key on bare UUID → True."""
    assert is_legacy_key(str(uuid.uuid4())) is True


def test_is_legacy_key_new_format():
    """is_legacy_key on new compound key → False."""
    assert is_legacy_key("b1__espresso__none") is False


# ---------------------------------------------------------------------------
# Legacy migration tests
# ---------------------------------------------------------------------------


def test_legacy_migration_renames_file(tmp_path):
    """migrate_legacy_campaign_files renames {uuid}.json to {uuid}__espresso__none.json."""
    from app.services.migration import migrate_legacy_campaign_files

    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    # Create a legacy campaign file
    old_uuid = str(uuid.uuid4())
    old_json = campaigns_dir / f"{old_uuid}.json"

    # Write minimal valid BayBE campaign JSON for migration (just needs to exist + be renamed)
    # We don't actually load it, just rename it — write a placeholder
    old_json.write_text("{}")

    count = migrate_legacy_campaign_files(campaigns_dir)

    assert count == 1
    # New file exists
    new_json = campaigns_dir / f"{old_uuid}__espresso__none.json"
    assert new_json.exists()
    # Old file gone
    assert not old_json.exists()


def test_legacy_migration_skips_existing(tmp_path):
    """migrate_legacy_campaign_files does not overwrite if new key file already exists."""
    from app.services.migration import migrate_legacy_campaign_files

    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    old_uuid = str(uuid.uuid4())
    old_json = campaigns_dir / f"{old_uuid}.json"
    new_json = campaigns_dir / f"{old_uuid}__espresso__none.json"

    old_json.write_text('{"old": true}')
    new_json.write_text('{"new": true}')

    count = migrate_legacy_campaign_files(campaigns_dir)

    # Should skip (new already exists)
    assert count == 0
    # Both files still present, new file content unchanged
    assert new_json.read_text() == '{"new": true}'
    assert old_json.exists()


# ---------------------------------------------------------------------------
# OptimizerService parameter set tests
# ---------------------------------------------------------------------------


def test_optimizer_pour_over_campaign_has_bloom_param(db_session):
    """OptimizerService pour-over campaign includes bloom_weight parameter."""
    from app.services.optimizer import OptimizerService

    def _factory():
        return db_session

    optimizer = OptimizerService(_factory)
    campaign_key = make_campaign_key("bean1", "pour-over", "setup1")
    campaign = optimizer.get_or_create_campaign(campaign_key, method="pour-over")

    param_names = [p.name for p in campaign.searchspace.parameters]
    assert "bloom_weight" in param_names
    assert "brew_volume" in param_names
    # Pour-over should NOT have espresso-only params
    assert "saturation" not in param_names
    assert "preinfusion_pressure_pct" not in param_names


def test_optimizer_espresso_campaign_phase20_tier1(db_session):
    """Phase 20: New espresso campaigns use Tier 1 params only (no legacy preinfusion_pressure_pct/saturation)."""
    from app.services.optimizer import OptimizerService

    def _factory():
        return db_session

    optimizer = OptimizerService(_factory)
    campaign_key = make_campaign_key("bean1", "espresso", None)
    campaign = optimizer.get_or_create_campaign(campaign_key, method="espresso")

    param_names = [p.name for p in campaign.searchspace.parameters]
    # Phase 20: legacy params excluded from new campaigns
    assert "saturation" not in param_names, "Legacy saturation must not appear in new campaigns"
    assert "preinfusion_pressure_pct" not in param_names, (
        "Legacy preinfusion_pressure_pct must not appear in new campaigns"
    )
    # Tier 1 core params must be present
    assert "grind_setting" in param_names
    assert "temperature" in param_names
    assert "dose_in" in param_names
    assert "target_yield" in param_names
    # Espresso should NOT have pour-over-only params
    assert "bloom_weight" not in param_names
    assert "brew_volume" not in param_names


# ---------------------------------------------------------------------------
# Integration tests: brew_setup_id stored on Measurement
# ---------------------------------------------------------------------------


def _mock_optimizer():
    """Return a mock optimizer that won't call BayBE."""
    mock = MagicMock()
    mock.recommend = AsyncMock()
    return mock


def _record_payload(rec_id: str, taste: float = 8.0, **kwargs) -> dict:
    """Build a minimal /brew/record form payload."""
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "preinfusion_pressure_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": str(taste),
    }
    payload.update(kwargs)
    return payload


def test_brew_setup_id_stored_on_measurement(active_client, sample_bean, sample_setup, db_session):
    """POST /brew/record with brew_setup_id saves it on the Measurement row."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = _record_payload(rec_id, brew_setup_id=sample_setup.id)
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.brew_setup_id == sample_setup.id


def test_brew_setup_id_null_when_not_provided(active_client, sample_bean, db_session):
    """POST /brew/record without brew_setup_id → Measurement.brew_setup_id is None."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = _record_payload(rec_id)
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.brew_setup_id is None


# ---------------------------------------------------------------------------
# Integration test: history page shows setup name
# ---------------------------------------------------------------------------


def test_method_context_in_history(active_client, sample_bean, sample_setup, db_session):
    """GET /history shows setup name for measurement that has brew_setup_id."""
    # Create a measurement linked to the setup
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=8.0,
        is_failed=False,
        brew_setup_id=sample_setup.id,
    )
    db_session.add(m)
    db_session.commit()

    response = active_client.get("/history")
    assert response.status_code == 200
    assert sample_setup.name in response.text


# ---------------------------------------------------------------------------
# Unit test: _get_method_from_setup helper
# ---------------------------------------------------------------------------


def test_method_defaults_to_espresso_no_setup():
    """_get_method_from_setup(None) returns 'espresso'."""
    from app.routers.brew import _get_method_from_setup

    assert _get_method_from_setup(None) == "espresso"


def test_method_from_setup_with_brew_method(sample_setup):
    """_get_method_from_setup with setup that has a brew_method returns lowercased method name."""
    from app.routers.brew import _get_method_from_setup

    # sample_setup has brew_method with name "Espresso"
    result = _get_method_from_setup(sample_setup)
    assert result == "espresso"
