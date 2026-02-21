"""BayBE optimizer service — the core intelligence of BrewFlow.

Wraps BayBE in a thread-safe service that can create hybrid campaigns,
generate recommendations, accept measurements, and persist campaign state.
"""

import asyncio
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


class OptimizerService:
    """Thread-safe BayBE campaign manager with disk persistence."""

    def __init__(self, campaigns_dir: Path):
        self._campaigns_dir = campaigns_dir
        self._campaigns_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Campaign] = {}
        self._lock = threading.Lock()

    def _campaign_path(self, bean_id: str) -> Path:
        return self._campaigns_dir / f"{bean_id}.json"

    @staticmethod
    def _create_fresh_campaign() -> Campaign:
        """Create a hybrid BayBE campaign (continuous + categorical)."""
        parameters = [
            NumericalContinuousParameter(name="grind_setting", bounds=(15.0, 25.0)),
            NumericalContinuousParameter(name="temperature", bounds=(86.0, 96.0)),
            NumericalContinuousParameter(name="preinfusion_pct", bounds=(55.0, 100.0)),
            NumericalContinuousParameter(name="dose_in", bounds=(18.5, 20.0)),
            NumericalContinuousParameter(name="target_yield", bounds=(36.0, 50.0)),
            CategoricalParameter(name="saturation", values=["yes", "no"], encoding="OHE"),
        ]
        searchspace = SearchSpace.from_product(parameters=parameters)
        target = NumericalTarget(name="taste")
        objective = SingleTargetObjective(target=target)
        recommender = TwoPhaseMetaRecommender(recommender=BotorchRecommender())
        return Campaign(searchspace=searchspace, objective=objective, recommender=recommender)

    def get_or_create_campaign(self, bean_id: str) -> Campaign:
        """Get campaign from cache, disk, or create fresh. Thread-safe."""
        with self._lock:
            if bean_id not in self._cache:
                path = self._campaign_path(bean_id)
                if path.exists():
                    self._cache[bean_id] = Campaign.from_json(path.read_text())
                else:
                    self._cache[bean_id] = self._create_fresh_campaign()
                    self._save_campaign_unlocked(bean_id)
            return self._cache[bean_id]

    async def recommend(self, bean_id: str) -> dict:
        """Generate a recommendation. Runs in thread pool (BayBE blocks 3-10s)."""

        def _recommend():
            campaign = self.get_or_create_campaign(bean_id)
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

    def add_measurement(self, bean_id: str, measurement: dict) -> None:
        """Record a measurement. Runs synchronously (fast).

        Args:
            measurement: dict with 6 BayBE param keys + "taste".
                         Extra keys (recommendation_id, etc.) are filtered out.
        """
        campaign = self.get_or_create_campaign(bean_id)
        # Only include BayBE columns + taste
        baybe_data = {k: measurement[k] for k in BAYBE_PARAM_COLUMNS + ["taste"]}
        df = pd.DataFrame([baybe_data])
        with self._lock:
            campaign.add_measurements(df)
            self._save_campaign_unlocked(bean_id)

    def rebuild_campaign(self, bean_id: str, measurements_df: pd.DataFrame) -> Campaign:
        """Disaster recovery: rebuild campaign from measurement data."""
        campaign = self._create_fresh_campaign()
        if not measurements_df.empty:
            baybe_cols = BAYBE_PARAM_COLUMNS + ["taste"]
            campaign.add_measurements(measurements_df[baybe_cols])
        with self._lock:
            self._cache[bean_id] = campaign
            self._save_campaign_unlocked(bean_id)
        return campaign

    def _save_campaign_unlocked(self, bean_id: str) -> None:
        """Save campaign JSON to disk. Must be called with lock held."""
        campaign = self._cache[bean_id]
        self._campaign_path(bean_id).write_text(campaign.to_json())
