"""Tests for file-to-DB migration functions (campaign state and pending recommendations).

Migration functions internally call ``session.commit()`` and ``session.close()``
on the session returned by their factory argument.  This conflicts with the
shared ``db_session`` fixture's rollback-based test isolation.

To avoid cross-test leakage, each migration test gets its **own** ephemeral
in-memory SQLite database via the ``migration_engine`` fixture.  The tables are
created fresh and destroyed at the end of each test — no shared state.
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.campaign_state import CampaignState
from app.models.pending_recommendation import PendingRecommendation
from app.services.migration import (
    migrate_campaigns_to_db,
    migrate_legacy_campaign_files,
    migrate_pending_to_db,
)


# ---------------------------------------------------------------------------
# Fixture: per-test isolated database for migration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def migration_engine():
    """Create an ephemeral in-memory SQLite engine + tables for one test."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def migration_session_factory(migration_engine):
    """SessionLocal-style factory for migration functions to use."""
    factory = sessionmaker(bind=migration_engine)
    return factory


@pytest.fixture()
def migration_query_session(migration_engine):
    """A separate session for assertions (avoids closed-session issues)."""
    factory = sessionmaker(bind=migration_engine)
    session = factory()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Campaign file → DB migration
# ---------------------------------------------------------------------------


def test_migrate_campaigns_to_db(migration_session_factory, migration_query_session, tmp_path):
    """migrate_campaigns_to_db inserts CampaignState rows from .json/.bounds files."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    # Create test campaign files
    (campaigns_dir / "bean1__espresso__none.json").write_text('{"campaign": "data1"}')
    (campaigns_dir / "bean1__espresso__none.bounds").write_text("abc123")
    (campaigns_dir / "bean2__pour-over__s1.json").write_text('{"campaign": "data2"}')

    migrated = migrate_campaigns_to_db(migration_session_factory, campaigns_dir)
    assert migrated == 2

    qs = migration_query_session
    row1 = qs.query(CampaignState).filter_by(campaign_key="bean1__espresso__none").first()
    assert row1 is not None
    assert row1.campaign_json == '{"campaign": "data1"}'
    assert row1.bounds_fingerprint == "abc123"

    row2 = qs.query(CampaignState).filter_by(campaign_key="bean2__pour-over__s1").first()
    assert row2 is not None
    assert row2.campaign_json == '{"campaign": "data2"}'
    assert row2.bounds_fingerprint is None  # no .bounds file


def test_migrate_campaigns_idempotent(migration_session_factory, migration_query_session, tmp_path):
    """Running migrate_campaigns_to_db twice produces no duplicates."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    (campaigns_dir / "bean1__espresso__none.json").write_text('{"campaign": "data"}')

    first = migrate_campaigns_to_db(migration_session_factory, campaigns_dir)
    second = migrate_campaigns_to_db(migration_session_factory, campaigns_dir)

    assert first == 1
    assert second == 0

    count = migration_query_session.query(CampaignState).count()
    assert count == 1


def test_migrate_campaigns_skips_existing(
    migration_session_factory, migration_query_session, tmp_path
):
    """Pre-existing DB rows are skipped; only new files are migrated."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    # Pre-insert one campaign via the factory
    pre_session = migration_session_factory()
    pre_session.add(
        CampaignState(
            campaign_key="existing__espresso__none",
            campaign_json='{"pre": "existing"}',
        )
    )
    pre_session.commit()
    pre_session.close()

    # Create files for existing and new campaign
    (campaigns_dir / "existing__espresso__none.json").write_text('{"from": "file"}')
    (campaigns_dir / "new__espresso__none.json").write_text('{"from": "file2"}')

    migrated = migrate_campaigns_to_db(migration_session_factory, campaigns_dir)
    assert migrated == 1  # only the new one

    # Existing row NOT overwritten
    qs = migration_query_session
    existing = qs.query(CampaignState).filter_by(campaign_key="existing__espresso__none").first()
    assert existing.campaign_json == '{"pre": "existing"}'


def test_migrate_campaigns_handles_missing_dir(migration_session_factory, tmp_path):
    """Non-existent campaigns_dir returns 0 without error."""
    missing = tmp_path / "does_not_exist"

    migrated = migrate_campaigns_to_db(migration_session_factory, missing)
    assert migrated == 0


def test_migrate_campaigns_with_transfer_metadata(
    migration_session_factory, migration_query_session, tmp_path
):
    """Transfer metadata sidecar file is read and stored in DB."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    (campaigns_dir / "bean1__espresso__none.json").write_text('{"campaign": "data"}')
    transfer_meta = {"contributing_beans": ["bean2"], "total_training_measurements": 5}
    (campaigns_dir / "bean1__espresso__none.transfer").write_text(json.dumps(transfer_meta))

    migrated = migrate_campaigns_to_db(migration_session_factory, campaigns_dir)
    assert migrated == 1

    row = (
        migration_query_session.query(CampaignState)
        .filter_by(campaign_key="bean1__espresso__none")
        .first()
    )
    assert row.transfer_metadata == transfer_meta


# ---------------------------------------------------------------------------
# Pending recommendation file → DB migration
# ---------------------------------------------------------------------------


def test_migrate_pending_to_db(migration_session_factory, migration_query_session, tmp_path):
    """migrate_pending_to_db inserts PendingRecommendation rows from JSON file."""
    pending_data = {
        "rec-1": {"grind_setting": 20.0, "temperature": 93.0},
        "rec-2": {"grind_setting": 21.0, "temperature": 94.0},
    }
    (tmp_path / "pending_recommendations.json").write_text(json.dumps(pending_data))

    migrated = migrate_pending_to_db(migration_session_factory, tmp_path)
    assert migrated == 2

    qs = migration_query_session
    row1 = qs.query(PendingRecommendation).filter_by(recommendation_id="rec-1").first()
    assert row1 is not None
    assert row1.recommendation_data == {"grind_setting": 20.0, "temperature": 93.0}

    row2 = qs.query(PendingRecommendation).filter_by(recommendation_id="rec-2").first()
    assert row2 is not None


def test_migrate_pending_idempotent(migration_session_factory, migration_query_session, tmp_path):
    """Running migrate_pending_to_db twice produces no duplicates."""
    pending_data = {"rec-1": {"grind_setting": 20.0}}
    (tmp_path / "pending_recommendations.json").write_text(json.dumps(pending_data))

    first = migrate_pending_to_db(migration_session_factory, tmp_path)
    second = migrate_pending_to_db(migration_session_factory, tmp_path)

    assert first == 1
    assert second == 0

    count = migration_query_session.query(PendingRecommendation).count()
    assert count == 1


def test_migrate_pending_handles_missing_file(migration_session_factory, tmp_path):
    """Directory without pending_recommendations.json returns 0."""

    migrated = migrate_pending_to_db(migration_session_factory, tmp_path)
    assert migrated == 0


def test_migrate_pending_handles_corrupt_json(
    migration_session_factory, migration_query_session, tmp_path
):
    """Corrupt JSON file returns 0 without crashing."""
    (tmp_path / "pending_recommendations.json").write_text("{not valid json!!!")

    migrated = migrate_pending_to_db(migration_session_factory, tmp_path)
    assert migrated == 0

    count = migration_query_session.query(PendingRecommendation).count()
    assert count == 0


# ---------------------------------------------------------------------------
# Legacy campaign file rename (filesystem only)
# ---------------------------------------------------------------------------


def test_migrate_legacy_campaign_files_renames(tmp_path):
    """migrate_legacy_campaign_files renames UUID-named files to compound key format."""
    import uuid

    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    old_uuid = str(uuid.uuid4())
    old_json = campaigns_dir / f"{old_uuid}.json"
    old_bounds = campaigns_dir / f"{old_uuid}.bounds"
    old_json.write_text("{}")
    old_bounds.write_text("fingerprint")

    count = migrate_legacy_campaign_files(campaigns_dir)
    assert count == 1

    new_json = campaigns_dir / f"{old_uuid}__espresso__none.json"
    new_bounds = campaigns_dir / f"{old_uuid}__espresso__none.bounds"
    assert new_json.exists()
    assert new_bounds.exists()
    assert not old_json.exists()
    assert not old_bounds.exists()


def test_migrate_legacy_campaign_files_missing_dir(tmp_path):
    """Non-existent directory returns 0."""
    count = migrate_legacy_campaign_files(tmp_path / "nope")
    assert count == 0
