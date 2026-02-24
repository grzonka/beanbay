"""BayBE optimizer service — the core intelligence of BeanBay.

Wraps BayBE in a thread-safe service that can create hybrid campaigns,
generate recommendations, accept measurements, and persist campaign state.

Campaign keys have the format: {bean_id}__{method}__{setup_id}
(or {bean_id}__espresso__none if no setup is selected).
Legacy bare bean_id keys are migrated at startup via migrate_legacy_campaign_files().
"""

import asyncio
import hashlib
import json
import threading
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.bean import Bean

import pandas as pd
from baybe.campaign import Campaign
from baybe.objectives import SingleTargetObjective
from baybe.parameters import CategoricalParameter, NumericalContinuousParameter
from baybe.recommenders import BotorchRecommender, TwoPhaseMetaRecommender
from baybe.recommenders.pure.nonpredictive.sampling import RandomRecommender
from baybe.searchspace import SearchSpace
from baybe.targets import NumericalTarget

# BayBE parameter column names for espresso (the 6 recipe params)
BAYBE_PARAM_COLUMNS = [
    "grind_setting",
    "temperature",
    "preinfusion_pct",
    "dose_in",
    "target_yield",
    "saturation",
]

# Pour-over BayBE parameter columns
POUR_OVER_PARAM_COLUMNS = [
    "grind_setting",
    "temperature",
    "bloom_weight",
    "dose_in",
    "brew_volume",
]

# Default parameter bounds for espresso (used when no overrides specified)
DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "grind_setting": (15.0, 25.0),
    "temperature": (86.0, 96.0),
    "preinfusion_pct": (55.0, 100.0),
    "dose_in": (18.5, 20.0),
    "target_yield": (36.0, 50.0),
}

# Pour-over default parameter bounds
POUR_OVER_DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "grind_setting": (15.0, 40.0),  # coarser grind for pour-over
    "temperature": (88.0, 98.0),
    "bloom_weight": (20.0, 80.0),  # grams of water for bloom
    "dose_in": (12.0, 22.0),  # dose in grams
    "brew_volume": (150.0, 500.0),  # total brew volume in ml
}

# Rounding rules for espresso (practical precision)
ROUNDING_RULES: dict[str, float] = {
    "grind_setting": 0.5,
    "temperature": 1.0,
    "preinfusion_pct": 5.0,
    "dose_in": 0.5,
    "target_yield": 1.0,
}

# Rounding rules for pour-over
POUR_OVER_ROUNDING_RULES: dict[str, float] = {
    "grind_setting": 0.5,
    "temperature": 1.0,
    "bloom_weight": 1.0,
    "dose_in": 0.5,
    "brew_volume": 5.0,
}


def _get_param_columns(method: str) -> list[str]:
    """Return BayBE parameter column names for the given method."""
    if method == "pour-over":
        return POUR_OVER_PARAM_COLUMNS
    return BAYBE_PARAM_COLUMNS  # espresso and all others


def _get_default_bounds(method: str) -> dict[str, tuple[float, float]]:
    """Return default parameter bounds for the given method."""
    if method == "pour-over":
        return dict(POUR_OVER_DEFAULT_BOUNDS)
    return dict(DEFAULT_BOUNDS)


def _get_rounding_rules(method: str) -> dict[str, float]:
    """Return rounding rules for the given method."""
    if method == "pour-over":
        return POUR_OVER_ROUNDING_RULES
    return ROUNDING_RULES


def _round_value(value: float, step: float) -> float:
    """Round a value to the nearest step."""
    return round(round(value / step) * step, 2)


def _resolve_bounds(
    overrides: dict | None,
    method: str = "espresso",
) -> dict[str, tuple[float, float]]:
    """Merge per-bean overrides onto default bounds.

    Args:
        overrides: e.g. {"grind_setting": {"min": 18.0, "max": 22.0}}
                   Only parameters that differ from defaults need to be present.
                   None or {} means "use all defaults".
        method: Brew method name — determines which default bounds to use.

    Returns:
        Complete bounds dict for all continuous parameters of the given method.
    """
    bounds = _get_default_bounds(method)
    if overrides:
        for param, spec in overrides.items():
            if param in bounds and isinstance(spec, dict):
                lo, hi = bounds[param]
                bounds[param] = (spec.get("min", lo), spec.get("max", hi))
    return bounds


def _bounds_fingerprint(bounds: dict[str, tuple[float, float]]) -> str:
    """Stable hash of the resolved bounds, used to detect override changes."""
    canonical = json.dumps(sorted(bounds.items()), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _build_parameters(
    bounds: dict[str, tuple[float, float]],
    method: str = "espresso",
) -> list:
    """Build BayBE parameter list for the given method and resolved bounds.

    Extracted so both OptimizerService and TransferLearningService can share
    the parameter-building logic without code duplication.

    Args:
        bounds: Resolved parameter bounds (from _resolve_bounds).
        method: Brew method — determines parameter set.

    Returns:
        List of BayBE parameter objects.
    """
    if method == "pour-over":
        return [
            NumericalContinuousParameter(name="grind_setting", bounds=bounds["grind_setting"]),
            NumericalContinuousParameter(name="temperature", bounds=bounds["temperature"]),
            NumericalContinuousParameter(name="bloom_weight", bounds=bounds["bloom_weight"]),
            NumericalContinuousParameter(name="dose_in", bounds=bounds["dose_in"]),
            NumericalContinuousParameter(name="brew_volume", bounds=bounds["brew_volume"]),
        ]
    else:
        # espresso and all other methods — 5 continuous + 1 categorical
        return [
            NumericalContinuousParameter(name="grind_setting", bounds=bounds["grind_setting"]),
            NumericalContinuousParameter(name="temperature", bounds=bounds["temperature"]),
            NumericalContinuousParameter(name="preinfusion_pct", bounds=bounds["preinfusion_pct"]),
            NumericalContinuousParameter(name="dose_in", bounds=bounds["dose_in"]),
            NumericalContinuousParameter(name="target_yield", bounds=bounds["target_yield"]),
            CategoricalParameter(name="saturation", values=["yes", "no"], encoding="OHE"),
        ]


class OptimizerService:
    """Thread-safe BayBE campaign manager with DB persistence.

    Campaigns are keyed by: {bean_id}__{method}__{setup_id}
    Legacy bare-UUID campaign files are migrated at startup via
    migrate_legacy_campaign_files().
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._cache: dict[str, Campaign] = {}
        self._fingerprints: dict[str, str] = {}
        self._transfer_metadata: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _load_from_db(self, campaign_key: str) -> tuple[str | None, str | None]:
        """Load campaign JSON and bounds fingerprint from DB.

        Returns:
            (campaign_json, fingerprint) tuple. Both None if campaign not found.
        """
        from app.models.campaign_state import CampaignState

        session = self._session_factory()
        try:
            row = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if row is None:
                return None, None
            # Also populate transfer metadata cache if present
            if row.transfer_metadata:
                self._transfer_metadata[campaign_key] = row.transfer_metadata
            return row.campaign_json, row.bounds_fingerprint
        finally:
            session.close()

    def _save_to_db(self, campaign_key: str) -> None:
        """Upsert campaign JSON + fingerprint to DB. Must be called with lock held."""
        from app.models.campaign_state import CampaignState

        campaign = self._cache[campaign_key]
        campaign_json = campaign.to_json()
        fingerprint = self._fingerprints.get(campaign_key, "")
        transfer_meta = self._transfer_metadata.get(campaign_key)

        session = self._session_factory()
        try:
            row = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if row is None:
                row = CampaignState(
                    campaign_key=campaign_key,
                    campaign_json=campaign_json,
                    bounds_fingerprint=fingerprint or None,
                    transfer_metadata=transfer_meta,
                )
                session.add(row)
            else:
                row.campaign_json = campaign_json
                row.bounds_fingerprint = fingerprint or None
                if transfer_meta is not None:
                    row.transfer_metadata = transfer_meta
            session.commit()
        finally:
            session.close()

    @staticmethod
    def _create_fresh_campaign(
        overrides: dict | None = None,
        method: str = "espresso",
    ) -> Campaign:
        """Create a hybrid BayBE campaign for the given method.

        Args:
            overrides: Per-bean parameter range overrides.
                       e.g. {"grind_setting": {"min": 18.0, "max": 22.0}}
            method: Brew method — determines parameter set (espresso vs pour-over).
        """
        bounds = _resolve_bounds(overrides, method)
        parameters = _build_parameters(bounds, method)
        searchspace = SearchSpace.from_product(parameters=parameters)
        target = NumericalTarget(name="taste")
        objective = SingleTargetObjective(target=target)
        recommender = TwoPhaseMetaRecommender(recommender=BotorchRecommender(), switch_after=5)
        return Campaign(searchspace=searchspace, objective=objective, recommender=recommender)

    def get_or_create_campaign(
        self,
        campaign_key: str,
        overrides: dict | None = None,
        method: str = "espresso",
        target_bean: "Bean | None" = None,
        db: "Session | None" = None,
    ) -> Campaign:
        """Get campaign from cache, DB, or create fresh. Thread-safe.

        If the resolved bounds fingerprint differs from the stored one
        (i.e. the user changed parameter overrides), the campaign is
        rebuilt from its existing measurements with the new bounds.

        When creating a fresh campaign and target_bean + db are provided,
        attempts to use transfer learning if similar beans exist.

        Args:
            campaign_key: Compound key "{bean_id}__{method}__{setup_id}".
            overrides: Per-bean parameter range overrides (from Bean.parameter_overrides).
            method: Brew method for parameter set selection.
            target_bean: Bean ORM object for transfer learning lookup (optional).
            db: SQLAlchemy Session for similarity queries (optional).
        """
        # Import here to avoid circular imports at module load time
        from app.services.similarity import SimilarityService
        from app.services.transfer_learning import build_transfer_campaign

        current_fp = _bounds_fingerprint(_resolve_bounds(overrides, method))

        with self._lock:
            # Load from DB if not cached
            if campaign_key not in self._cache:
                campaign_json, stored_fp = self._load_from_db(campaign_key)
                if campaign_json is not None:
                    self._cache[campaign_key] = Campaign.from_json(campaign_json)
                    self._fingerprints[campaign_key] = stored_fp or ""
                else:
                    # Try transfer learning for new campaigns when bean+db provided
                    campaign = None
                    if target_bean is not None and db is not None:
                        similar_beans = SimilarityService().find_similar_beans(
                            target_bean, method, db
                        )
                        if similar_beans:
                            result = build_transfer_campaign(
                                target_bean, similar_beans, method, overrides, db
                            )
                            if result is not None:
                                campaign, metadata = result
                                # Store transfer metadata in DB via cache
                                self._transfer_metadata[campaign_key] = {
                                    "contributing_beans": metadata.contributing_beans,
                                    "total_training_measurements": metadata.total_training_measurements,
                                }

                    if campaign is None:
                        campaign = self._create_fresh_campaign(overrides, method)

                    self._cache[campaign_key] = campaign
                    self._fingerprints[campaign_key] = current_fp
                    self._save_to_db(campaign_key)

            # Check if overrides changed → rebuild with new bounds
            stored_fp = self._fingerprints.get(campaign_key, "")
            if stored_fp and stored_fp != current_fp:
                old_campaign = self._cache[campaign_key]
                measurements_df = old_campaign.measurements
                new_campaign = self._create_fresh_campaign(overrides, method)
                if not measurements_df.empty:
                    param_cols = _get_param_columns(method)
                    # For transfer campaigns the measurements include bean_task — filter to
                    # only the standard BayBE columns so we can add them to a fresh campaign.
                    available_cols = [
                        c for c in param_cols + ["taste"] if c in measurements_df.columns
                    ]
                    # Allow out-of-range measurements: historical data from the
                    # old bounds is still informative for the surrogate model.
                    new_campaign.add_measurements(
                        measurements_df[available_cols],
                        numerical_measurements_must_be_within_tolerance=False,
                    )
                self._cache[campaign_key] = new_campaign
                self._fingerprints[campaign_key] = current_fp
                self._save_to_db(campaign_key)

            return self._cache[campaign_key]

    def get_transfer_metadata(self, campaign_key: str) -> dict | None:
        """Return transfer metadata dict if this campaign was seeded via transfer learning."""
        # Check in-memory cache first
        if campaign_key in self._transfer_metadata:
            return self._transfer_metadata[campaign_key]
        # Fall back to DB query
        from app.models.campaign_state import CampaignState

        session = self._session_factory()
        try:
            row = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if row is not None and row.transfer_metadata:
                self._transfer_metadata[campaign_key] = row.transfer_metadata
                return row.transfer_metadata
        finally:
            session.close()
        return None

    async def recommend(
        self,
        campaign_key: str,
        overrides: dict | None = None,
        method: str = "espresso",
        target_bean: "Bean | None" = None,
        db: "Session | None" = None,
    ) -> dict:
        """Generate a recommendation. Runs in thread pool (BayBE blocks 3-10s).

        Args:
            campaign_key: Compound key "{bean_id}__{method}__{setup_id}".
            overrides: Per-bean parameter range overrides.
            method: Brew method for parameter set selection.
            target_bean: Bean ORM object for transfer learning lookup (optional).
            db: SQLAlchemy Session for similarity queries (optional).
        """

        def _recommend():
            campaign = self.get_or_create_campaign(
                campaign_key, overrides, method, target_bean=target_bean, db=db
            )
            with self._lock:
                campaign.clear_cache()
                rec_df = campaign.recommend(batch_size=1)
                self._save_to_db(campaign_key)
            rec = rec_df.iloc[0].to_dict()

            # Round to practical precision
            rounding = _get_rounding_rules(method)
            for param, step in rounding.items():
                if param in rec:
                    rec[param] = _round_value(float(rec[param]), step)

            # Generate idempotency token
            rec["recommendation_id"] = str(uuid.uuid4())
            return rec

        return await asyncio.to_thread(_recommend)

    def add_measurement(
        self,
        campaign_key: str,
        measurement: dict,
        overrides: dict | None = None,
        method: str = "espresso",
        target_bean_id: str | None = None,
    ) -> None:
        """Record a measurement. Runs synchronously (fast).

        Args:
            campaign_key: Compound key "{bean_id}__{method}__{setup_id}".
            measurement: dict with method-specific BayBE param keys + "taste".
                         Extra keys (recommendation_id, etc.) are filtered out.
            overrides: Per-bean parameter range overrides.
            method: Brew method for parameter set selection.
            target_bean_id: Bean ID to set as bean_task for transfer learning campaigns.
        """
        campaign = self.get_or_create_campaign(campaign_key, overrides, method)
        # Only include method-appropriate BayBE columns + taste
        param_cols = _get_param_columns(method)
        baybe_data = {k: measurement[k] for k in param_cols + ["taste"] if k in measurement}
        # For transfer learning campaigns, include the bean_task column
        if target_bean_id is not None and self.get_transfer_metadata(campaign_key) is not None:
            baybe_data["bean_task"] = target_bean_id
        df = pd.DataFrame([baybe_data])
        with self._lock:
            campaign.add_measurements(df)
            self._save_to_db(campaign_key)

    def rebuild_campaign(
        self,
        campaign_key: str,
        measurements_df: pd.DataFrame,
        overrides: dict | None = None,
        method: str = "espresso",
    ) -> Campaign:
        """Disaster recovery: rebuild campaign from measurement data.

        Args:
            campaign_key: Compound key "{bean_id}__{method}__{setup_id}".
            measurements_df: DataFrame with BayBE columns + taste.
            overrides: Per-bean parameter range overrides.
            method: Brew method for parameter set selection.
        """
        campaign = self._create_fresh_campaign(overrides, method)
        if not measurements_df.empty:
            param_cols = _get_param_columns(method)
            baybe_cols = param_cols + ["taste"]
            campaign.add_measurements(
                measurements_df[baybe_cols],
                numerical_measurements_must_be_within_tolerance=False,
            )
        current_fp = _bounds_fingerprint(_resolve_bounds(overrides, method))
        with self._lock:
            self._cache[campaign_key] = campaign
            self._fingerprints[campaign_key] = current_fp
            self._save_to_db(campaign_key)
        return campaign

    def get_recommendation_insights(
        self,
        campaign_key: str,
        rec_dict: dict,
        overrides: dict | None = None,
        method: str = "espresso",
    ) -> dict:
        """Compute insight metadata for a recommendation.

        Returns dict with:
          - phase: "random" | "bayesian_early" | "bayesian"
          - phase_label: str (human-readable)
          - explanation: str (contextual explanation)
          - predicted_mean: float | None
          - predicted_std: float | None
          - predicted_range: str | None (e.g. "4.5 – 8.5")
          - shot_count: int

        Must be called *after* recommend() completes (they both use _lock separately).
        """
        campaign = self.get_or_create_campaign(campaign_key, overrides, method)

        with self._lock:
            meta_rec = campaign.recommender
            selected = meta_rec.select_recommender(
                batch_size=1,
                searchspace=campaign.searchspace,
                objective=campaign.objective,
                measurements=campaign.measurements,
            )
            is_random = isinstance(selected, RandomRecommender)

            measurements_df = campaign.measurements
            shot_count = len(measurements_df) if not measurements_df.empty else 0

            # Determine phase and explanation
            if is_random:
                phase = "random"
                phase_label = "Random exploration"
                explanation = (
                    "Exploring randomly — building initial understanding of the parameter space."
                )
            else:
                if shot_count < 8:
                    phase = "bayesian_early"
                    phase_label = "Learning"
                    explanation = (
                        "The model is learning your preferences — "
                        "building a map of the flavor space with each shot."
                    )
                else:
                    phase = "bayesian"
                    phase_label = "Bayesian optimization"
                    # Check if recent shots improved over previous best
                    taste_values = measurements_df["taste"].tolist()
                    previous_best = max(taste_values[:-3]) if len(taste_values) > 3 else None
                    recent_best = max(taste_values[-3:])
                    if previous_best is not None and recent_best > previous_best:
                        explanation = (
                            "Zeroing in — recent shots are improving. "
                            "The model is finding promising regions."
                        )
                    else:
                        explanation = (
                            "Exploring new territory — "
                            "looking for something better than the current best."
                        )

            # Compute predicted taste (only if Bayesian and enough data)
            predicted_mean = None
            predicted_std = None
            predicted_range = None

            if not is_random and shot_count >= 2:
                try:
                    param_cols = _get_param_columns(method)
                    rec_df = pd.DataFrame([{k: rec_dict[k] for k in param_cols if k in rec_dict}])
                    stats = campaign.posterior_stats(rec_df)
                    predicted_mean = round(float(stats["taste_mean"].iloc[0]), 1)
                    predicted_std = round(float(stats["taste_std"].iloc[0]), 1)
                    lo = round(max(1.0, predicted_mean - predicted_std), 1)
                    hi = round(min(10.0, predicted_mean + predicted_std), 1)
                    predicted_range = f"{lo} \u2013 {hi}"
                except Exception:
                    predicted_mean = None
                    predicted_std = None
                    predicted_range = None

        return {
            "phase": phase,
            "phase_label": phase_label,
            "explanation": explanation,
            "predicted_mean": predicted_mean,
            "predicted_std": predicted_std,
            "predicted_range": predicted_range,
            "shot_count": shot_count,
        }
