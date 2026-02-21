"""BayBE optimizer service — the core intelligence of BrewFlow.

Wraps BayBE in a thread-safe service that can create hybrid campaigns,
generate recommendations, accept measurements, and persist campaign state.
"""

import asyncio
import hashlib
import json
import threading
import uuid
from pathlib import Path

import pandas as pd
from baybe.campaign import Campaign
from baybe.objectives import SingleTargetObjective
from baybe.parameters import CategoricalParameter, NumericalContinuousParameter
from baybe.recommenders import BotorchRecommender, TwoPhaseMetaRecommender
from baybe.searchspace import SearchSpace
from baybe.targets import NumericalTarget

# BayBE parameter column names (the 6 recipe params)
BAYBE_PARAM_COLUMNS = [
    "grind_setting",
    "temperature",
    "preinfusion_pct",
    "dose_in",
    "target_yield",
    "saturation",
]

# Default parameter bounds (used when no overrides specified)
DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "grind_setting": (15.0, 25.0),
    "temperature": (86.0, 96.0),
    "preinfusion_pct": (55.0, 100.0),
    "dose_in": (18.5, 20.0),
    "target_yield": (36.0, 50.0),
}

# Rounding rules for practical precision
ROUNDING_RULES: dict[str, float] = {
    "grind_setting": 0.5,
    "temperature": 1.0,
    "preinfusion_pct": 5.0,
    "dose_in": 0.5,
    "target_yield": 1.0,
}


def _round_value(value: float, step: float) -> float:
    """Round a value to the nearest step."""
    return round(round(value / step) * step, 2)


def _resolve_bounds(
    overrides: dict | None,
) -> dict[str, tuple[float, float]]:
    """Merge per-bean overrides onto default bounds.

    Args:
        overrides: e.g. {"grind_setting": {"min": 18.0, "max": 22.0}}
                   Only parameters that differ from defaults need to be present.
                   None or {} means "use all defaults".

    Returns:
        Complete bounds dict for all 5 continuous parameters.
    """
    bounds = dict(DEFAULT_BOUNDS)
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


class OptimizerService:
    """Thread-safe BayBE campaign manager with disk persistence."""

    def __init__(self, campaigns_dir: Path):
        self._campaigns_dir = campaigns_dir
        self._campaigns_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Campaign] = {}
        self._fingerprints: dict[str, str] = {}
        self._lock = threading.Lock()

    def _campaign_path(self, bean_id: str) -> Path:
        return self._campaigns_dir / f"{bean_id}.json"

    def _fingerprint_path(self, bean_id: str) -> Path:
        return self._campaigns_dir / f"{bean_id}.bounds"

    @staticmethod
    def _create_fresh_campaign(
        overrides: dict | None = None,
    ) -> Campaign:
        """Create a hybrid BayBE campaign (continuous + categorical).

        Args:
            overrides: Per-bean parameter range overrides.
                       e.g. {"grind_setting": {"min": 18.0, "max": 22.0}}
        """
        bounds = _resolve_bounds(overrides)
        parameters = [
            NumericalContinuousParameter(name="grind_setting", bounds=bounds["grind_setting"]),
            NumericalContinuousParameter(name="temperature", bounds=bounds["temperature"]),
            NumericalContinuousParameter(name="preinfusion_pct", bounds=bounds["preinfusion_pct"]),
            NumericalContinuousParameter(name="dose_in", bounds=bounds["dose_in"]),
            NumericalContinuousParameter(name="target_yield", bounds=bounds["target_yield"]),
            CategoricalParameter(name="saturation", values=["yes", "no"], encoding="OHE"),
        ]
        searchspace = SearchSpace.from_product(parameters=parameters)
        target = NumericalTarget(name="taste")
        objective = SingleTargetObjective(target=target)
        recommender = TwoPhaseMetaRecommender(recommender=BotorchRecommender())
        return Campaign(searchspace=searchspace, objective=objective, recommender=recommender)

    def get_or_create_campaign(
        self,
        bean_id: str,
        overrides: dict | None = None,
    ) -> Campaign:
        """Get campaign from cache, disk, or create fresh. Thread-safe.

        If the resolved bounds fingerprint differs from the stored one
        (i.e. the user changed parameter overrides), the campaign is
        rebuilt from its existing measurements with the new bounds.

        Args:
            bean_id: UUID of the bean.
            overrides: Per-bean parameter range overrides (from Bean.parameter_overrides).
        """
        current_fp = _bounds_fingerprint(_resolve_bounds(overrides))

        with self._lock:
            # Load from disk if not cached
            if bean_id not in self._cache:
                path = self._campaign_path(bean_id)
                fp_path = self._fingerprint_path(bean_id)
                if path.exists():
                    self._cache[bean_id] = Campaign.from_json(path.read_text())
                    self._fingerprints[bean_id] = (
                        fp_path.read_text().strip() if fp_path.exists() else ""
                    )
                else:
                    self._cache[bean_id] = self._create_fresh_campaign(overrides)
                    self._fingerprints[bean_id] = current_fp
                    self._save_campaign_unlocked(bean_id)

            # Check if overrides changed → rebuild with new bounds
            stored_fp = self._fingerprints.get(bean_id, "")
            if stored_fp and stored_fp != current_fp:
                old_campaign = self._cache[bean_id]
                measurements_df = old_campaign.measurements
                new_campaign = self._create_fresh_campaign(overrides)
                if not measurements_df.empty:
                    baybe_cols = BAYBE_PARAM_COLUMNS + ["taste"]
                    # Allow out-of-range measurements: historical data from the
                    # old bounds is still informative for the surrogate model.
                    new_campaign.add_measurements(
                        measurements_df[baybe_cols],
                        numerical_measurements_must_be_within_tolerance=False,
                    )
                self._cache[bean_id] = new_campaign
                self._fingerprints[bean_id] = current_fp
                self._save_campaign_unlocked(bean_id)

            return self._cache[bean_id]

    async def recommend(
        self,
        bean_id: str,
        overrides: dict | None = None,
    ) -> dict:
        """Generate a recommendation. Runs in thread pool (BayBE blocks 3-10s).

        Args:
            bean_id: UUID of the bean.
            overrides: Per-bean parameter range overrides.
        """

        def _recommend():
            campaign = self.get_or_create_campaign(bean_id, overrides)
            with self._lock:
                rec_df = campaign.recommend(batch_size=1)
                self._save_campaign_unlocked(bean_id)
            rec = rec_df.iloc[0].to_dict()

            # Round to practical precision
            for param, step in ROUNDING_RULES.items():
                if param in rec:
                    rec[param] = _round_value(float(rec[param]), step)

            # Generate idempotency token
            rec["recommendation_id"] = str(uuid.uuid4())
            return rec

        return await asyncio.to_thread(_recommend)

    def add_measurement(
        self,
        bean_id: str,
        measurement: dict,
        overrides: dict | None = None,
    ) -> None:
        """Record a measurement. Runs synchronously (fast).

        Args:
            bean_id: UUID of the bean.
            measurement: dict with 6 BayBE param keys + "taste".
                         Extra keys (recommendation_id, etc.) are filtered out.
            overrides: Per-bean parameter range overrides.
        """
        campaign = self.get_or_create_campaign(bean_id, overrides)
        # Only include BayBE columns + taste
        baybe_data = {k: measurement[k] for k in BAYBE_PARAM_COLUMNS + ["taste"]}
        df = pd.DataFrame([baybe_data])
        with self._lock:
            campaign.add_measurements(df)
            self._save_campaign_unlocked(bean_id)

    def rebuild_campaign(
        self,
        bean_id: str,
        measurements_df: pd.DataFrame,
        overrides: dict | None = None,
    ) -> Campaign:
        """Disaster recovery: rebuild campaign from measurement data.

        Args:
            bean_id: UUID of the bean.
            measurements_df: DataFrame with BayBE columns + taste.
            overrides: Per-bean parameter range overrides.
        """
        campaign = self._create_fresh_campaign(overrides)
        if not measurements_df.empty:
            baybe_cols = BAYBE_PARAM_COLUMNS + ["taste"]
            campaign.add_measurements(
                measurements_df[baybe_cols],
                numerical_measurements_must_be_within_tolerance=False,
            )
        current_fp = _bounds_fingerprint(_resolve_bounds(overrides))
        with self._lock:
            self._cache[bean_id] = campaign
            self._fingerprints[bean_id] = current_fp
            self._save_campaign_unlocked(bean_id)
        return campaign

    def _save_campaign_unlocked(self, bean_id: str) -> None:
        """Save campaign JSON + bounds fingerprint to disk. Must be called with lock held."""
        campaign = self._cache[bean_id]
        self._campaign_path(bean_id).write_text(campaign.to_json())
        fp = self._fingerprints.get(bean_id, "")
        if fp:
            self._fingerprint_path(bean_id).write_text(fp)
