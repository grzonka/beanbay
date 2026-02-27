"""File-to-DB migration functions for campaign state and pending recommendations.

These functions run at startup to migrate existing filesystem-based campaign
storage into SQLite. They are idempotent — running twice produces no duplicates.
"""

import json
import logging
from pathlib import Path

from app.models.campaign_state import CampaignState
from app.models.pending_recommendation import PendingRecommendation
from app.services.optimizer_key import is_legacy_key, make_campaign_key

logger = logging.getLogger(__name__)


def migrate_legacy_campaign_files(campaigns_dir: Path) -> int:
    """Rename legacy bare-UUID campaign files to the new compound-key format.

    Old format: {bean_id}.json / {bean_id}.bounds / {bean_id}.transfer
    New format: {bean_id}__espresso__none.json / ...

    This is a filesystem rename that must run *before* migrate_campaigns_to_db()
    so that the DB migration picks up the correctly-named files.

    Args:
        campaigns_dir: Directory containing campaign files.

    Returns:
        Number of campaign files migrated (renamed) in this run.
    """
    if not campaigns_dir.exists():
        return 0

    migrated = 0
    for json_file in sorted(campaigns_dir.glob("*.json")):
        stem = json_file.stem
        if is_legacy_key(stem):
            new_key = make_campaign_key(stem, "espresso", None)
            new_json = campaigns_dir / f"{new_key}.json"
            new_bounds = campaigns_dir / f"{new_key}.bounds"
            new_transfer = campaigns_dir / f"{new_key}.transfer"
            # Only migrate if target doesn't already exist
            if not new_json.exists():
                json_file.rename(new_json)
                old_bounds = campaigns_dir / f"{stem}.bounds"
                if old_bounds.exists() and not new_bounds.exists():
                    old_bounds.rename(new_bounds)
                old_transfer = campaigns_dir / f"{stem}.transfer"
                if old_transfer.exists() and not new_transfer.exists():
                    old_transfer.rename(new_transfer)
                migrated += 1
                logger.info("Renamed legacy campaign %r to %r", stem, new_key)

    return migrated


def migrate_campaigns_to_db(session_factory, campaigns_dir: Path) -> int:
    """Migrate campaign files from disk into the campaign_states DB table.

    Reads {key}.json, {key}.bounds, and {key}.transfer files from campaigns_dir
    and inserts corresponding CampaignState rows. Skips campaigns already present
    in the DB (idempotent). Leaves original files in place as backup.

    Args:
        session_factory: Callable that returns a new SQLAlchemy Session
                         (e.g. SessionLocal — a plain sessionmaker, NOT a context manager).
        campaigns_dir: Directory containing campaign .json/.bounds/.transfer files.

    Returns:
        Number of campaigns migrated in this run (0 if all already migrated).
    """
    if not campaigns_dir.exists():
        logger.info("campaigns_dir %s does not exist, skipping migration", campaigns_dir)
        return 0

    migrated = 0
    session = session_factory()
    try:
        for json_file in sorted(campaigns_dir.glob("*.json")):
            campaign_key = json_file.stem

            # Idempotency check — skip if row already exists
            exists = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if exists:
                logger.debug("Campaign %r already in DB, skipping", campaign_key)
                continue

            # Read campaign JSON (required)
            try:
                campaign_json = json_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Could not read campaign file %s: %s — skipping", json_file, exc)
                continue

            # Read bounds fingerprint (optional sidecar)
            fingerprint: str | None = None
            bounds_file = campaigns_dir / f"{campaign_key}.bounds"
            if bounds_file.exists():
                try:
                    fingerprint = bounds_file.read_text(encoding="utf-8").strip()
                except OSError as exc:
                    logger.warning(
                        "Could not read bounds file %s: %s — using None", bounds_file, exc
                    )

            # Read transfer metadata (optional sidecar)
            transfer_meta: dict | None = None
            transfer_file = campaigns_dir / f"{campaign_key}.transfer"
            if transfer_file.exists():
                try:
                    transfer_meta = json.loads(transfer_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning(
                        "Could not read/parse transfer file %s: %s — using None",
                        transfer_file,
                        exc,
                    )

            state = CampaignState(
                campaign_key=campaign_key,
                campaign_json=campaign_json,
                bounds_fingerprint=fingerprint,
                transfer_metadata=transfer_meta,
            )
            session.add(state)
            migrated += 1
            logger.info("Migrating campaign %r to DB", campaign_key)

        if migrated:
            session.commit()
    finally:
        session.close()

    logger.info("Campaign migration complete: %d campaign(s) migrated", migrated)
    return migrated


def migrate_pending_to_db(session_factory, data_dir: Path) -> int:
    """Migrate pending_recommendations.json into the pending_recommendations DB table.

    Reads data_dir/pending_recommendations.json (dict of {rec_id: rec_data}) and
    inserts PendingRecommendation rows. Skips recommendations already present in
    the DB (idempotent).

    Args:
        session_factory: Callable that returns a new SQLAlchemy Session
                         (e.g. SessionLocal — a plain sessionmaker, NOT a context manager).
        data_dir: Directory containing pending_recommendations.json.

    Returns:
        Number of pending recommendations migrated in this run.
    """
    pending_file = data_dir / "pending_recommendations.json"
    if not pending_file.exists():
        logger.info("pending_recommendations.json not found at %s, skipping", pending_file)
        return 0

    try:
        data: dict = json.loads(pending_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "Could not read/parse %s: %s — skipping pending migration", pending_file, exc
        )
        return 0

    migrated = 0
    session = session_factory()
    try:
        for rec_id, rec_data in data.items():
            # Idempotency check — skip if row already exists
            exists = (
                session.query(PendingRecommendation).filter_by(recommendation_id=rec_id).first()
            )
            if exists:
                logger.debug("Pending recommendation %r already in DB, skipping", rec_id)
                continue

            session.add(
                PendingRecommendation(
                    recommendation_id=rec_id,
                    recommendation_data=rec_data,
                )
            )
            migrated += 1
            logger.info("Migrating pending recommendation %r to DB", rec_id)

        if migrated:
            session.commit()
    finally:
        session.close()

    logger.info("Pending recommendation migration complete: %d record(s) migrated", migrated)
    return migrated
