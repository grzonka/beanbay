"""BayBE optimizer service.

Manages Campaign creation, recommendation generation, measurement
preparation, phase determination, and fingerprinting.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd
from baybe import Campaign as BaybeCampaign
from baybe.objectives import SingleTargetObjective
from baybe.parameters import CategoricalParameter, NumericalContinuousParameter
from baybe.recommenders import (
    BotorchRecommender,
    RandomRecommender,
    TwoPhaseMetaRecommender,
)
from baybe.searchspace import SearchSpace
from baybe.targets import NumericalTarget

from beanbay.services.parameter_ranges import EffectiveRange


class OptimizerService:
    """Manages BayBE campaigns and recommendations.

    All methods are static — no instance state needed.
    """

    @staticmethod
    def build_campaign(effective_ranges: list[EffectiveRange]) -> BaybeCampaign:
        """Build a BayBE Campaign from effective parameter ranges.

        Parameters
        ----------
        effective_ranges : list[EffectiveRange]
            Computed effective ranges from the 3-layer system.

        Returns
        -------
        BaybeCampaign
            A fresh BayBE Campaign ready for recommendations.
        """
        parameters = []
        for r in effective_ranges:
            if r.allowed_values is not None:
                # Categorical parameter
                values = tuple(v.strip() for v in r.allowed_values.split(","))
                parameters.append(
                    CategoricalParameter(name=r.parameter_name, values=values)
                )
            else:
                # Continuous numeric parameter
                parameters.append(
                    NumericalContinuousParameter(
                        name=r.parameter_name,
                        bounds=(r.min_value, r.max_value),
                    )
                )

        searchspace = SearchSpace.from_product(parameters)
        target = NumericalTarget(name="score")
        objective = SingleTargetObjective(target=target)
        recommender = TwoPhaseMetaRecommender(
            initial_recommender=RandomRecommender(),
            recommender=BotorchRecommender(),
        )

        return BaybeCampaign(
            searchspace=searchspace,
            objective=objective,
            recommender=recommender,
        )

    @staticmethod
    def recommend(
        campaign: BaybeCampaign, measurements_df: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """Generate a single recommendation from BayBE.

        Parameters
        ----------
        campaign : BaybeCampaign
            The BayBE campaign (may have prior measurements).
        measurements_df : pd.DataFrame | None
            DataFrame of prior measurements with parameter columns + 'score'.
            If provided, adds to the campaign before recommending.

        Returns
        -------
        dict[str, Any]
            Dict mapping parameter_name to recommended value.
        """
        if measurements_df is not None and not measurements_df.empty:
            campaign.add_measurements(measurements_df)

        rec_df = campaign.recommend(batch_size=1)
        # Convert single-row DataFrame to dict
        return rec_df.iloc[0].to_dict()

    @staticmethod
    def round_recommendation(
        values: dict[str, Any],
        effective_ranges: list[EffectiveRange],
    ) -> dict[str, Any]:
        """Round recommended values to step precision.

        Parameters
        ----------
        values : dict[str, Any]
            Raw recommendation from BayBE.
        effective_ranges : list[EffectiveRange]
            Ranges with step info for rounding.

        Returns
        -------
        dict[str, Any]
            Rounded values.
        """
        range_map = {r.parameter_name: r for r in effective_ranges}
        rounded = {}
        for name, value in values.items():
            r = range_map.get(name)
            if r and r.step and isinstance(value, (int, float)):
                # Round to nearest step
                rounded[name] = round(round(value / r.step) * r.step, 10)
            else:
                rounded[name] = value
        return rounded

    @staticmethod
    def determine_phase(measurement_count: int, initial_points: int = 5) -> str:
        """Determine the current optimization phase.

        Parameters
        ----------
        measurement_count : int
            Number of valid measurements so far.
        initial_points : int
            Number of random exploration points (default 5).

        Returns
        -------
        str
            Phase string: 'random', 'learning', or 'optimizing'.
        """
        if measurement_count < initial_points:
            return "random"
        if measurement_count < initial_points * 3:
            return "learning"
        return "optimizing"

    @staticmethod
    def compute_fingerprints(
        effective_ranges: list[EffectiveRange],
    ) -> tuple[str, str]:
        """Compute fingerprints for change detection.

        Parameters
        ----------
        effective_ranges : list[EffectiveRange]
            Current effective parameter ranges.

        Returns
        -------
        tuple[str, str]
            (bounds_fingerprint, param_fingerprint) — 16-char hex hashes.
        """
        # Param fingerprint: hash of sorted parameter names
        param_names = sorted(r.parameter_name for r in effective_ranges)
        param_hash = hashlib.md5(
            ",".join(param_names).encode()
        ).hexdigest()[:16]

        # Bounds fingerprint: hash of sorted (name, min, max) tuples
        bounds = sorted(
            (r.parameter_name, r.min_value, r.max_value)
            for r in effective_ranges
        )
        bounds_hash = hashlib.md5(
            str(bounds).encode()
        ).hexdigest()[:16]

        return bounds_hash, param_hash
