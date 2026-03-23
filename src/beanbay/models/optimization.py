"""Optimization-related models for BeanBay.

Campaign tracks a BayBE optimization campaign for a (bean, brew_setup) pair.
MethodParameterDefault and BeanParameterOverride define parameter search spaces.
Recommendation stores suggested brew parameters from the optimizer.
OptimizationJob tracks background optimization tasks.
"""

import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint, func
from sqlmodel import Field, SQLModel

from beanbay.models.base import uuid4_default


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class Campaign(SQLModel, table=True):
    """A BayBE optimization campaign for a bean + brew-setup pair.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the bean being optimized.
    brew_setup_id : uuid.UUID
        Foreign key to the brew setup used.
    campaign_json : str | None
        Serialized BayBE campaign state.
    phase : str
        Current optimization phase (random, sequential, etc.).
    measurement_count : int
        Number of measurements recorded so far.
    best_score : float | None
        Best score achieved in this campaign.
    bounds_fingerprint : str | None
        Hash of parameter bounds for cache invalidation.
    param_fingerprint : str | None
        Hash of parameter definitions for cache invalidation.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    """

    __tablename__ = "campaigns"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "bean_id", "brew_setup_id", name="uq_campaign_bean_setup"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id", index=True)
    brew_setup_id: uuid.UUID = Field(foreign_key="brew_setups.id", index=True)

    campaign_json: str | None = None
    phase: str = Field(default="random")
    measurement_count: int = Field(default=0)
    best_score: float | None = None
    bounds_fingerprint: str | None = None
    param_fingerprint: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


# ---------------------------------------------------------------------------
# MethodParameterDefault
# ---------------------------------------------------------------------------


class MethodParameterDefault(SQLModel, table=True):
    """Default parameter search-space bounds for a brew method.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    brew_method_id : uuid.UUID
        Foreign key to the brew method.
    parameter_name : str
        Name of the parameter (e.g. ``"grind_setting"``).
    min_value : float | None
        Minimum value for the parameter range.
    max_value : float | None
        Maximum value for the parameter range.
    step : float | None
        Step size for discrete parameters.
    allowed_values : str | None
        JSON list of allowed categorical values.
    requires : str | None
        Equipment capability required (e.g. ``"has_pressure"``).
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    """

    __tablename__ = "method_parameter_defaults"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "brew_method_id",
            "parameter_name",
            name="uq_method_param_default",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    brew_method_id: uuid.UUID = Field(
        foreign_key="brew_methods.id", index=True
    )

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    allowed_values: str | None = None
    requires: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


# ---------------------------------------------------------------------------
# BeanParameterOverride
# ---------------------------------------------------------------------------


class BeanParameterOverride(SQLModel, table=True):
    """Bean-specific override for parameter search-space bounds.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the bean.
    parameter_name : str
        Name of the parameter being overridden.
    min_value : float | None
        Overridden minimum value.
    max_value : float | None
        Overridden maximum value.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    """

    __tablename__ = "bean_parameter_overrides"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "bean_id", "parameter_name", name="uq_bean_param_override"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id", index=True)

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


class Recommendation(SQLModel, table=True):
    """A recommended set of brew parameters from the optimizer.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Foreign key to the parent campaign.
    brew_id : uuid.UUID | None
        Foreign key to the brew that executed this recommendation.
    phase : str
        Optimization phase when this recommendation was generated.
    predicted_score : float | None
        Model-predicted score for this parameter set.
    predicted_std : float | None
        Standard deviation of the predicted score.
    parameter_values : str
        JSON-serialized parameter values.
    status : str
        Status of the recommendation (pending, accepted, rejected, etc.).
    created_at : datetime
        Row creation timestamp (server default).
    """

    __tablename__ = "recommendations"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)
    brew_id: uuid.UUID | None = Field(
        default=None, foreign_key="brews.id", index=True
    )

    phase: str
    predicted_score: float | None = None
    predicted_std: float | None = None
    parameter_values: str
    status: str = Field(default="pending")

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )


# ---------------------------------------------------------------------------
# OptimizationJob
# ---------------------------------------------------------------------------


class OptimizationJob(SQLModel, table=True):
    """A background optimization job (e.g. re-fitting, recommending).

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Foreign key to the parent campaign.
    job_type : str
        Type of job (e.g. ``"recommend"``, ``"refit"``).
    status : str
        Current status (pending, running, completed, failed).
    result_id : uuid.UUID | None
        ID of the resulting object (e.g. recommendation id).
    error_message : str | None
        Error message if the job failed.
    created_at : datetime
        Row creation timestamp (server default).
    completed_at : datetime | None
        When the job finished.
    """

    __tablename__ = "optimization_jobs"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)

    job_type: str
    status: str = Field(default="pending", index=True)
    result_id: uuid.UUID | None = None
    error_message: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    completed_at: datetime | None = None
