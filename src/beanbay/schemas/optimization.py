"""Read / write schemas for optimization models.

Schemas for campaigns, recommendations, optimization jobs, bean parameter
overrides, method defaults, campaign progress, and person preferences.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class CampaignCreate(SQLModel):
    """Schema for creating a Campaign.

    Attributes
    ----------
    bean_id : uuid.UUID
        Bean FK.
    brew_setup_id : uuid.UUID
        Brew setup FK.
    """

    bean_id: uuid.UUID
    brew_setup_id: uuid.UUID


class CampaignListRead(SQLModel):
    """Summary schema for listing campaigns.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_name : str | None
        Name of the linked bean.
    brew_setup_name : str | None
        Name of the linked brew setup.
    phase : str
        Current campaign phase.
    measurement_count : int
        Number of measurements recorded.
    best_score : float | None
        Best score achieved so far.
    created_at : datetime
        Creation timestamp.
    """

    id: uuid.UUID
    bean_name: str | None = None
    brew_setup_name: str | None = None
    phase: str
    measurement_count: int
    best_score: float | None = None
    created_at: datetime


class CampaignRead(SQLModel):
    """Schema returned when reading a Campaign.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Bean FK.
    brew_setup_id : uuid.UUID
        Brew setup FK.
    phase : str
        Current campaign phase.
    measurement_count : int
        Number of measurements recorded.
    best_score : float | None
        Best score achieved so far.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    bean_name : str | None
        Name of the linked bean.
    brew_setup_name : str | None
        Name of the linked brew setup.
    """

    id: uuid.UUID
    bean_id: uuid.UUID
    brew_setup_id: uuid.UUID
    phase: str
    measurement_count: int
    best_score: float | None = None
    created_at: datetime
    updated_at: datetime
    bean_name: str | None = None
    brew_setup_name: str | None = None


class EffectiveRange(SQLModel):
    """A resolved parameter range with its source.

    Attributes
    ----------
    parameter_name : str
        Name of the brew parameter.
    min_value : float | None
        Minimum value in the range.
    max_value : float | None
        Maximum value in the range.
    step : float | None
        Step size for discrete parameters.
    allowed_values : str | None
        Comma-separated allowed values for categorical parameters.
    source : str
        Where the range came from: ``method_default``, ``equipment``,
        or ``bean_override``.
    """

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    allowed_values: str | None = None
    source: str


class CampaignDetailRead(CampaignRead):
    """Extended campaign schema with effective parameter ranges and progress.

    Attributes
    ----------
    effective_ranges : list[EffectiveRange]
        Resolved parameter ranges for this campaign.
    convergence : ConvergenceInfo | None
        Convergence status information.
    score_history : list[ScoreHistoryEntry]
        Chronological score history.
    """

    effective_ranges: list[EffectiveRange] = []
    convergence: ConvergenceInfo | None = None
    score_history: list[ScoreHistoryEntry] = []


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


class RecommendationRead(SQLModel):
    """Schema returned when reading a Recommendation.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Parent campaign FK.
    brew_id : uuid.UUID | None
        Linked brew FK (set when recommendation is used).
    phase : str
        Phase the recommendation was generated in.
    predicted_score : float | None
        Model-predicted score.
    predicted_std : float | None
        Model-predicted standard deviation.
    parameter_values : dict
        Recommended parameter values (parsed from JSON).
    status : str
        Recommendation status (pending, accepted, rejected).
    created_at : datetime
        Creation timestamp.
    optimization_mode : str | None
        Optimization mode used (auto, community, personal).
    personal_brew_count : int | None
        Number of personal brews used for optimization.
    """

    id: uuid.UUID
    campaign_id: uuid.UUID
    brew_id: uuid.UUID | None = None
    phase: str
    predicted_score: float | None = None
    predicted_std: float | None = None
    parameter_values: dict
    status: str
    created_at: datetime
    optimization_mode: str | None = None
    personal_brew_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_parameter_values(cls, data: dict | object) -> dict:
        """Parse ``parameter_values`` from JSON string to dict if needed.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with ``parameter_values`` as a Python dict.
        """
        if not isinstance(data, dict):
            d: dict[str, Any] = {}
            for field in (
                "id",
                "campaign_id",
                "brew_id",
                "phase",
                "predicted_score",
                "predicted_std",
                "parameter_values",
                "status",
                "created_at",
                "optimization_mode",
                "personal_brew_count",
            ):
                d[field] = getattr(data, field, None)
            data = d

        pv = data.get("parameter_values")
        if isinstance(pv, str):
            data["parameter_values"] = json.loads(pv)
        elif pv is None:
            data["parameter_values"] = {}
        return data


class RecommendRequest(SQLModel):
    """Optional body for POST /campaigns/{id}/recommend.

    Attributes
    ----------
    person_id : uuid.UUID | None
        Person to optimize for.
    mode : str
        Optimization mode: auto, community, or personal.
    """

    person_id: uuid.UUID | None = None
    mode: str = "auto"


# ---------------------------------------------------------------------------
# Optimization Job
# ---------------------------------------------------------------------------


class OptimizationJobRead(SQLModel):
    """Schema returned when reading an OptimizationJob.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Parent campaign FK.
    job_type : str
        Type of optimization job.
    status : str
        Job status (pending, running, completed, failed).
    result_id : uuid.UUID | None
        FK to the result (recommendation) if completed.
    error_message : str | None
        Error message if the job failed.
    created_at : datetime
        Creation timestamp.
    completed_at : datetime | None
        Completion timestamp.
    """

    id: uuid.UUID
    campaign_id: uuid.UUID
    job_type: str
    status: str
    result_id: uuid.UUID | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Bean Parameter Overrides
# ---------------------------------------------------------------------------


class BeanOverrideItem(SQLModel):
    """A single bean parameter override entry.

    Attributes
    ----------
    parameter_name : str
        Name of the brew parameter to override.
    min_value : float | None
        Minimum value override.
    max_value : float | None
        Maximum value override.
    """

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None


class BeanOverridesPut(SQLModel):
    """Schema for bulk-replacing bean parameter overrides.

    Attributes
    ----------
    overrides : list[BeanOverrideItem]
        List of parameter overrides to set.
    """

    overrides: list[BeanOverrideItem]


class BeanOverrideRead(SQLModel):
    """Schema returned when reading a BeanParameterOverride.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Parent bean FK.
    parameter_name : str
        Name of the brew parameter.
    min_value : float | None
        Minimum value override.
    max_value : float | None
        Maximum value override.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    """

    id: uuid.UUID
    bean_id: uuid.UUID
    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Method Parameter Defaults
# ---------------------------------------------------------------------------


class MethodParameterDefaultRead(SQLModel):
    """Schema returned when reading a MethodParameterDefault.

    Attributes
    ----------
    parameter_name : str
        Name of the brew parameter.
    min_value : float | None
        Default minimum value.
    max_value : float | None
        Default maximum value.
    step : float | None
        Step size for discrete parameters.
    requires : str | None
        Equipment type required for this parameter.
    allowed_values : str | None
        Comma-separated allowed values for categorical parameters.
    """

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    requires: str | None = None
    allowed_values: str | None = None


# ---------------------------------------------------------------------------
# Campaign Progress
# ---------------------------------------------------------------------------


class ConvergenceInfo(SQLModel):
    """Convergence status for a campaign.

    Attributes
    ----------
    status : str
        Convergence status: ``getting_started``, ``exploring``,
        ``learning``, or ``converged``.
    improvement_rate : float | None
        Rate of improvement over recent measurements.
    """

    status: str
    improvement_rate: float | None = None


class ScoreHistoryEntry(SQLModel):
    """A single entry in the campaign score history.

    Attributes
    ----------
    shot_number : int
        Sequential shot number within the campaign.
    score : float | None
        Score achieved (None if not scored).
    is_failed : bool
        Whether the brew was marked as failed.
    phase : str | None
        Campaign phase when this brew was made.
    """

    shot_number: int
    score: float | None = None
    is_failed: bool
    phase: str | None = None


class CampaignProgress(SQLModel):
    """Campaign progress summary with convergence and score history.

    Attributes
    ----------
    phase : str
        Current campaign phase.
    measurement_count : int
        Number of measurements recorded.
    best_score : float | None
        Best score achieved so far.
    convergence : ConvergenceInfo
        Convergence status information.
    score_history : list[ScoreHistoryEntry]
        Chronological score history.
    """

    phase: str
    measurement_count: int
    best_score: float | None = None
    convergence: ConvergenceInfo
    score_history: list[ScoreHistoryEntry] = []


# ---------------------------------------------------------------------------
# Person Preferences
# ---------------------------------------------------------------------------


class TopBean(SQLModel):
    """A person's top-rated bean.

    Attributes
    ----------
    bean_id : uuid.UUID
        Bean primary key.
    name : str
        Bean name.
    avg_score : float
        Average score across brews.
    brew_count : int
        Number of brews with this bean.
    """

    bean_id: uuid.UUID
    name: str
    avg_score: float
    brew_count: int


class FlavorFrequency(SQLModel):
    """A flavor tag with its occurrence frequency.

    Attributes
    ----------
    tag : str
        Flavor tag name.
    frequency : int
        Number of times this tag appeared.
    """

    tag: str
    frequency: int


class OriginPreference(SQLModel):
    """A person's preference for a coffee origin.

    Attributes
    ----------
    origin : str
        Origin name.
    avg_score : float
        Average score for brews with this origin.
    brew_count : int
        Number of brews with this origin.
    """

    origin: str
    avg_score: float
    brew_count: int


class MethodBreakdown(SQLModel):
    """Brew method usage and performance breakdown.

    Attributes
    ----------
    method : str
        Brew method name.
    brew_count : int
        Number of brews with this method.
    avg_score : float
        Average score for brews with this method.
    """

    method: str
    brew_count: int
    avg_score: float


class TasteProfile(SQLModel):
    """Averaged sub-scores from a person's top brews.

    Attributes
    ----------
    acidity : float | None
        Average acidity score.
    sweetness : float | None
        Average sweetness score.
    body : float | None
        Average body score.
    bitterness : float | None
        Average bitterness score.
    balance : float | None
        Average balance score.
    aftertaste : float | None
        Average aftertaste score.
    """

    acidity: float | None = None
    sweetness: float | None = None
    body: float | None = None
    bitterness: float | None = None
    balance: float | None = None
    aftertaste: float | None = None


class PersonPreferences(SQLModel):
    """Aggregated preference data for a person.

    Attributes
    ----------
    person : dict
        Person data (id, name).
    brew_stats : dict
        Overall brew statistics (total_brews, avg_score, etc.).
    top_beans : list[TopBean]
        Top-rated beans.
    flavor_profile : list[FlavorFrequency]
        Most frequent flavor tags.
    roast_preference : dict
        Roast degree preference distribution.
    origin_preferences : list[OriginPreference]
        Preferences by coffee origin.
    method_breakdown : list[MethodBreakdown]
        Usage and scores by brew method.
    taste_profile : TasteProfile | None
        Averaged sub-scores from top brews.
    taste_profile_brew_count : int
        Number of brews used to compute the taste profile.
    """

    person: dict
    brew_stats: dict
    top_beans: list[TopBean] = []
    flavor_profile: list[FlavorFrequency] = []
    roast_preference: dict = {}
    origin_preferences: list[OriginPreference] = []
    method_breakdown: list[MethodBreakdown] = []
    taste_profile: TasteProfile | None = None
    taste_profile_brew_count: int = 0


# ---------------------------------------------------------------------------
# Posterior Predictions
# ---------------------------------------------------------------------------


class MeasurementPoint(SQLModel):
    """A single measurement for overlay on posterior plots.

    Attributes
    ----------
    values : dict
        Parameter values for this measurement.
    score : float
        Observed taste score.
    """

    values: dict
    score: float


class PosteriorResponse(SQLModel):
    """Response from the posterior predictions endpoint.

    Attributes
    ----------
    params : list[str]
        Parameter names that were swept.
    grid : list[list[float]]
        Grid values per parameter (one array per param).
    mean : list
        Predicted mean scores (1D for single param, 2D nested for two).
    std : list
        Predicted std (same shape as mean).
    measurements : list[MeasurementPoint]
        Actual measurements for chart overlay.
    """

    params: list[str]
    grid: list[list[float]]
    mean: list
    std: list
    measurements: list[MeasurementPoint] = []


# ---------------------------------------------------------------------------
# Feature Importance
# ---------------------------------------------------------------------------


class FeatureImportanceResponse(SQLModel):
    """Response from the feature importance endpoint.

    Attributes
    ----------
    parameters : list[str]
        Parameter names sorted by importance descending.
    importance : list[float]
        SHAP importance values (same order as parameters).
    measurement_count : int
        Number of measurements used for the analysis.
    """

    parameters: list[str]
    importance: list[float]
    measurement_count: int
