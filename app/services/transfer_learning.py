"""Transfer learning service for BayBE campaign seeding.

When a new bean has known process + variety metadata matching beans already
in history, this service creates a BayBE campaign with a TaskParameter that
incorporates prior measurements as training tasks. The new bean is the active
test task — BayBE uses the training data to produce smarter first recommendations
instead of starting from pure random exploration.

The mechanism:
1. SimilarityService finds similar beans (matching process + variety, ≥3 measurements)
2. TransferLearningService builds a Campaign with TaskParameter including all bean IDs
3. Historical measurements from similar beans are loaded as training tasks
4. The new bean is set as the active_value — BayBE will recommend for it

Reference: https://emdgroup.github.io/baybe/stable/userguide/transfer_learning.html
"""

from dataclasses import dataclass, field

import pandas as pd
from baybe.campaign import Campaign
from baybe.objectives import SingleTargetObjective
from baybe.parameters import TaskParameter
from baybe.recommenders import BotorchRecommender, TwoPhaseMetaRecommender
from baybe.searchspace import SearchSpace
from baybe.targets import NumericalTarget
from sqlalchemy.orm import Session

from app.models.bean import Bean
from app.models.brew_setup import BrewSetup
from app.models.measurement import Measurement
from app.services.parameter_registry import build_parameters_for_setup, get_param_columns
from app.services.similarity import SimilarBean


@dataclass
class TransferMetadata:
    """Metadata about the transfer learning seeding for a campaign."""

    contributing_beans: list[dict] = field(default_factory=list)
    # Each entry: {"bean_id": str, "name": str, "process": str|None, "variety": str|None}
    total_training_measurements: int = 0


def _collect_training_measurements(
    bean_id: str,
    method: str,
    db: Session,
    brewer=None,
) -> pd.DataFrame:
    """Collect BayBE-relevant measurements for a bean + method as a DataFrame.

    Returns DataFrame with param columns + "taste" + "bean_task" = bean_id.
    Empty DataFrame if no measurements found.
    """
    param_cols = get_param_columns(method, brewer)

    # Query measurements for this bean + method
    query = db.query(Measurement).filter(Measurement.bean_id == bean_id)

    if method == "espresso":
        # Legacy (no setup) + espresso-linked setups
        from sqlalchemy import or_

        query = query.filter(
            or_(
                Measurement.brew_setup_id.is_(None),
                Measurement.brew_setup.has(BrewSetup.brew_method.has(name="espresso")),
            )
        )
    else:
        query = query.filter(Measurement.brew_setup.has(BrewSetup.brew_method.has(name=method)))

    measurements = query.all()
    if not measurements:
        return pd.DataFrame()

    rows = []
    for m in measurements:
        row = {"bean_task": bean_id, "taste": m.taste}
        for col in param_cols:
            val = getattr(m, col, None)
            if val is not None:
                row[col] = val
        # Only include row if all param columns are present
        if all(c in row for c in param_cols):
            rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def build_transfer_campaign(
    target_bean: Bean,
    similar_beans: list[SimilarBean],
    method: str,
    overrides: dict | None,
    db: Session,
    brewer=None,
) -> tuple[Campaign, TransferMetadata] | None:
    """Build a BayBE campaign seeded with transfer learning from similar beans.

    Args:
        target_bean: The new bean to create the campaign for.
        similar_beans: List of similar beans from SimilarityService.
        method: Brew method name.
        overrides: Per-bean parameter range overrides.
        db: SQLAlchemy session for querying training measurements.
        brewer: Brewer ORM object for capability-gated parameter selection (optional).

    Returns:
        (Campaign, TransferMetadata) if transfer learning applies, None otherwise.
    """
    if not similar_beans:
        return None

    # Collect training measurements from all similar beans
    training_frames: list[pd.DataFrame] = []
    contributing: list[dict] = []

    for similar in similar_beans:
        df = _collect_training_measurements(similar.bean_id, method, db, brewer=brewer)
        if not df.empty:
            training_frames.append(df)
            contributing.append(
                {
                    "bean_id": similar.bean_id,
                    "name": similar.bean_name,
                    "process": similar.process,
                    "variety": similar.variety,
                }
            )

    if not training_frames:
        return None

    training_df = pd.concat(training_frames, ignore_index=True)
    total_training = len(training_df)

    # Build all task labels: training bean IDs + target bean ID
    all_task_ids = [similar.bean_id for similar in similar_beans] + [target_bean.id]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_task_ids: list[str] = []
    for tid in all_task_ids:
        if tid not in seen:
            unique_task_ids.append(tid)
            seen.add(tid)

    # Build parameters: TaskParameter first, then method-specific params
    recipe_params = build_parameters_for_setup(method, brewer=brewer, overrides=overrides)
    task_param = TaskParameter(
        name="bean_task",
        values=unique_task_ids,
        active_values=[target_bean.id],
    )
    all_params = [task_param] + recipe_params

    # Create campaign
    searchspace = SearchSpace.from_product(parameters=all_params)
    target = NumericalTarget(name="taste")
    objective = SingleTargetObjective(target=target)
    recommender = TwoPhaseMetaRecommender(recommender=BotorchRecommender(), switch_after=5)
    campaign = Campaign(searchspace=searchspace, objective=objective, recommender=recommender)

    # Load training measurements
    param_cols = get_param_columns(method, brewer)
    baybe_cols = ["bean_task"] + param_cols + ["taste"]
    available_cols = [c for c in baybe_cols if c in training_df.columns]
    campaign.add_measurements(training_df[available_cols])

    metadata = TransferMetadata(
        contributing_beans=contributing,
        total_training_measurements=total_training,
    )
    return campaign, metadata
