"""Taskiq broker for async BayBE optimization tasks."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select
from taskiq import InMemoryBroker

from beanbay.database import engine

broker = InMemoryBroker()
logger = logging.getLogger(__name__)


@broker.task
async def generate_recommendation(job_id: str) -> None:
    """Generate a BayBE recommendation for the given optimization job.

    Parameters
    ----------
    job_id : str
        UUID string of the OptimizationJob to process.
    """
    import uuid

    import pandas as pd
    from baybe import Campaign as BaybeCampaign

    from beanbay.models.bean import Bag
    from beanbay.models.brew import Brew, BrewSetup, BrewTaste
    from beanbay.models.equipment import Brewer, Grinder
    from beanbay.models.optimization import (
        BeanParameterOverride,
        Campaign,
        MethodParameterDefault,
        OptimizationJob,
        Recommendation,
    )
    from beanbay.services.optimizer import OptimizerService
    from beanbay.services.parameter_ranges import compute_effective_ranges

    with Session(engine) as session:
        try:
            # 1. Load job
            job = session.get(OptimizationJob, uuid.UUID(job_id))
            if job is None:
                logger.error("Job %s not found", job_id)
                return
            job.status = "running"
            session.add(job)
            session.commit()

            # 2. Load campaign
            campaign_row = session.get(Campaign, job.campaign_id)
            if campaign_row is None:
                job.status = "failed"
                job.error_message = "Campaign not found"
                job.completed_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
                return

            # 3. Load setup, brewer, grinder
            setup = session.get(BrewSetup, campaign_row.brew_setup_id)
            brewer = session.get(Brewer, setup.brewer_id) if setup.brewer_id else None
            grinder = (
                session.get(Grinder, setup.grinder_id) if setup.grinder_id else None
            )

            # 4. Load method defaults
            defaults = session.exec(
                select(MethodParameterDefault).where(
                    MethodParameterDefault.brew_method_id == setup.brew_method_id
                )
            ).all()

            # 5. Load bean overrides
            overrides = session.exec(
                select(BeanParameterOverride).where(
                    BeanParameterOverride.bean_id == campaign_row.bean_id
                )
            ).all()

            # 6. Compute effective ranges
            effective_ranges = compute_effective_ranges(
                list(defaults), brewer, grinder, list(overrides)
            )

            # 7. Check fingerprints — rebuild if changed
            bounds_fp, param_fp = OptimizerService.compute_fingerprints(
                effective_ranges
            )

            if (
                campaign_row.campaign_json
                and campaign_row.bounds_fingerprint == bounds_fp
                and campaign_row.param_fingerprint == param_fp
            ):
                # Restore existing campaign
                baybe_campaign = BaybeCampaign.from_json(campaign_row.campaign_json)
            else:
                # Build fresh campaign
                baybe_campaign = OptimizerService.build_campaign(effective_ranges)

            # 8. Query valid measurements (not failed, has score)
            stmt = (
                select(Brew)
                .join(Bag, Brew.bag_id == Bag.id)
                .join(BrewTaste, Brew.id == BrewTaste.brew_id)
                .where(
                    Bag.bean_id == campaign_row.bean_id,
                    Brew.brew_setup_id == campaign_row.brew_setup_id,
                    Brew.is_failed == False,  # noqa: E712
                    Brew.retired_at.is_(None),  # type: ignore[union-attr]
                    BrewTaste.score.is_not(None),  # type: ignore[union-attr]
                )
            )
            brews = session.exec(stmt).all()

            # 9. Build measurements DataFrame
            param_names = [r.parameter_name for r in effective_ranges]
            if brews:
                rows = []
                for brew in brews:
                    row = {}
                    for pname in param_names:
                        row[pname] = getattr(brew, pname, None)
                    row["score"] = brew.taste.score
                    rows.append(row)
                measurements_df = pd.DataFrame(rows)
                # Drop rows with None values in any parameter column
                measurements_df = measurements_df.dropna(subset=param_names)
            else:
                measurements_df = None

            # 10. Get recommendation
            raw_values = OptimizerService.recommend(baybe_campaign, measurements_df)

            # 11. Round values
            rounded_values = OptimizerService.round_recommendation(
                raw_values, effective_ranges
            )

            # Remove 'score' key if present (it's the target, not a parameter)
            rounded_values.pop("score", None)

            # 12. Determine phase and stats
            valid_count = len(measurements_df) if measurements_df is not None else 0
            phase = OptimizerService.determine_phase(valid_count)
            best_score = (
                float(measurements_df["score"].max())
                if measurements_df is not None and not measurements_df.empty
                else None
            )

            # 13. Create Recommendation row
            rec = Recommendation(
                campaign_id=campaign_row.id,
                phase=phase,
                parameter_values=json.dumps(rounded_values),
                status="pending",
            )
            session.add(rec)
            session.flush()

            # 14. Update campaign state
            campaign_row.campaign_json = baybe_campaign.to_json()
            campaign_row.phase = phase
            campaign_row.measurement_count = valid_count
            campaign_row.best_score = best_score
            campaign_row.bounds_fingerprint = bounds_fp
            campaign_row.param_fingerprint = param_fp
            session.add(campaign_row)

            # 15. Complete job
            job.status = "completed"
            job.result_id = rec.id
            job.completed_at = datetime.now(timezone.utc)
            session.add(job)

            session.commit()
            logger.info(
                "Recommendation %s generated for campaign %s",
                rec.id,
                campaign_row.id,
            )

        except Exception as e:
            logger.exception(
                "Failed to generate recommendation for job %s", job_id
            )
            # Try to mark job as failed
            try:
                job = session.get(OptimizationJob, uuid.UUID(job_id))
                if job:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    job.completed_at = datetime.now(timezone.utc)
                    session.add(job)
                    session.commit()
            except Exception:
                logger.exception("Failed to update job status")
