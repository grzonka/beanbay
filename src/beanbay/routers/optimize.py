"""Router for optimization endpoints.

Provides bean parameter override management, campaign CRUD,
method parameter default queries, and recommendation/job endpoints.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import case, func
from sqlmodel import SQLModel, select

from beanbay.dependencies import SessionDep
from beanbay.models.bean import Bag, Bean, BeanOriginLink
from beanbay.models.brew import Brew, BrewSetup, BrewTaste, BrewTasteFlavorTagLink
from beanbay.models.equipment import Brewer, Grinder
from beanbay.models.optimization import (
    BeanParameterOverride,
    Campaign,
    MethodParameterDefault,
    OptimizationJob,
    Recommendation,
)
from beanbay.models.person import Person
from beanbay.models.tag import BrewMethod, FlavorTag, Origin
from beanbay.schemas.optimization import (
    BeanOverrideRead,
    BeanOverridesPut,
    CampaignCreate,
    CampaignDetailRead,
    CampaignListRead,
    CampaignProgress,
    ConvergenceInfo,
    EffectiveRange,
    FeatureImportanceResponse,
    FlavorFrequency,
    MeasurementPoint,
    MethodBreakdown,
    MethodParameterDefaultRead,
    OptimizationJobRead,
    OriginPreference,
    PersonPreferences,
    PosteriorResponse,
    RecommendationRead,
    ScoreHistoryEntry,
    TopBean,
)
from beanbay.services.parameter_ranges import compute_effective_ranges
from beanbay.services.taskiq_broker import generate_recommendation

router = APIRouter(tags=["Optimization"])


@router.get(
    "/optimize/beans/{bean_id}/overrides",
    response_model=list[BeanOverrideRead],
)
def list_bean_overrides(
    bean_id: uuid.UUID,
    session: SessionDep,
) -> list[BeanOverrideRead]:
    """List parameter overrides for a bean.

    Parameters
    ----------
    bean_id : uuid.UUID
        Primary key of the bean.
    session : SessionDep
        Database session.

    Returns
    -------
    list[BeanOverrideRead]
        All parameter overrides for the given bean.

    Raises
    ------
    HTTPException
        404 if the bean does not exist.
    """
    bean = session.get(Bean, bean_id)
    if bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")
    overrides = session.exec(
        select(BeanParameterOverride).where(
            BeanParameterOverride.bean_id == bean_id
        )
    ).all()
    return overrides  # type: ignore[return-value]


@router.put(
    "/optimize/beans/{bean_id}/overrides",
    response_model=list[BeanOverrideRead],
)
def put_bean_overrides(
    bean_id: uuid.UUID,
    payload: BeanOverridesPut,
    session: SessionDep,
) -> list[BeanOverrideRead]:
    """Set/replace all parameter overrides for a bean.

    Deletes any existing overrides for the bean and inserts the new set.
    Passing an empty list clears all overrides.

    Parameters
    ----------
    bean_id : uuid.UUID
        Primary key of the bean.
    payload : BeanOverridesPut
        The override items to set.
    session : SessionDep
        Database session.

    Returns
    -------
    list[BeanOverrideRead]
        The newly created overrides.

    Raises
    ------
    HTTPException
        404 if the bean does not exist.
    """
    bean = session.get(Bean, bean_id)
    if bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    # Delete existing overrides
    existing = session.exec(
        select(BeanParameterOverride).where(
            BeanParameterOverride.bean_id == bean_id
        )
    ).all()
    for override in existing:
        session.delete(override)
    session.flush()

    # Insert new overrides
    new_overrides = []
    for item in payload.overrides:
        db_override = BeanParameterOverride(
            bean_id=bean_id,
            parameter_name=item.parameter_name,
            min_value=item.min_value,
            max_value=item.max_value,
        )
        session.add(db_override)
        new_overrides.append(db_override)

    session.commit()
    for o in new_overrides:
        session.refresh(o)
    return new_overrides  # type: ignore[return-value]


# ======================================================================
# Campaign CRUD
# ======================================================================


def _compute_campaign_ranges(
    session,
    campaign: Campaign,
) -> list[EffectiveRange]:
    """Compute effective parameter ranges for a campaign.

    Parameters
    ----------
    session : Session
        Database session.
    campaign : Campaign
        The campaign to compute ranges for.

    Returns
    -------
    list[EffectiveRange]
        Effective ranges converted to schema objects.
    """
    setup = session.get(BrewSetup, campaign.brew_setup_id)

    # Load method defaults
    defaults = session.exec(
        select(MethodParameterDefault).where(
            MethodParameterDefault.brew_method_id == setup.brew_method_id
        )
    ).all()

    # Load equipment (may be None)
    brewer = session.get(Brewer, setup.brewer_id) if setup.brewer_id else None
    grinder = (
        session.get(Grinder, setup.grinder_id) if setup.grinder_id else None
    )

    # Load bean overrides
    overrides = session.exec(
        select(BeanParameterOverride).where(
            BeanParameterOverride.bean_id == campaign.bean_id
        )
    ).all()

    service_ranges = compute_effective_ranges(
        defaults, brewer, grinder, overrides
    )

    # Convert dataclasses to schema objects
    return [
        EffectiveRange(
            parameter_name=r.parameter_name,
            min_value=r.min_value,
            max_value=r.max_value,
            step=r.step,
            allowed_values=r.allowed_values,
            source=r.source,
        )
        for r in service_ranges
    ]


def _campaign_to_detail(
    session,
    campaign: Campaign,
) -> CampaignDetailRead:
    """Build a CampaignDetailRead from a Campaign model.

    Parameters
    ----------
    session : Session
        Database session.
    campaign : Campaign
        The campaign model.

    Returns
    -------
    CampaignDetailRead
        Full detail schema with effective ranges.
    """
    bean = session.get(Bean, campaign.bean_id)
    setup = session.get(BrewSetup, campaign.brew_setup_id)

    ranges = _compute_campaign_ranges(session, campaign)

    return CampaignDetailRead(
        id=campaign.id,
        bean_id=campaign.bean_id,
        brew_setup_id=campaign.brew_setup_id,
        phase=campaign.phase,
        measurement_count=campaign.measurement_count,
        best_score=campaign.best_score,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        bean_name=bean.name if bean else None,
        brew_setup_name=setup.name if setup else None,
        effective_ranges=ranges,
    )


@router.post(
    "/optimize/campaigns",
    response_model=CampaignDetailRead,
    status_code=201,
)
def create_or_get_campaign(
    payload: CampaignCreate,
    response: Response,
    session: SessionDep,
) -> CampaignDetailRead:
    """Create a campaign or return existing one for this bean+setup.

    If a campaign already exists for the given bean and brew setup
    combination, the existing campaign is returned with status 200
    instead of 201.

    Parameters
    ----------
    payload : CampaignCreate
        Bean and brew setup IDs.
    response : Response
        FastAPI response object for status code override.
    session : SessionDep
        Database session.

    Returns
    -------
    CampaignDetailRead
        The created or existing campaign with effective ranges.

    Raises
    ------
    HTTPException
        404 if bean or brew setup does not exist.
    """
    # Validate bean_id
    bean = session.get(Bean, payload.bean_id)
    if bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    # Validate brew_setup_id
    setup = session.get(BrewSetup, payload.brew_setup_id)
    if setup is None:
        raise HTTPException(status_code=404, detail="BrewSetup not found.")

    # Check for existing campaign
    existing = session.exec(
        select(Campaign).where(
            Campaign.bean_id == payload.bean_id,
            Campaign.brew_setup_id == payload.brew_setup_id,
        )
    ).first()

    if existing is not None:
        response.status_code = 200
        return _campaign_to_detail(session, existing)

    # Create new campaign
    campaign = Campaign(
        bean_id=payload.bean_id,
        brew_setup_id=payload.brew_setup_id,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    return _campaign_to_detail(session, campaign)


@router.get(
    "/optimize/campaigns",
    response_model=list[CampaignListRead],
)
def list_campaigns(
    bean_id: uuid.UUID | None = Query(None),
    brew_setup_id: uuid.UUID | None = Query(None),
    *,
    session: SessionDep,
) -> list[CampaignListRead]:
    """List campaigns with optional filters.

    Parameters
    ----------
    bean_id : uuid.UUID | None
        Filter by bean ID.
    brew_setup_id : uuid.UUID | None
        Filter by brew setup ID.
    session : SessionDep
        Database session.

    Returns
    -------
    list[CampaignListRead]
        Summary list of matching campaigns.
    """
    stmt = select(Campaign)

    if bean_id is not None:
        stmt = stmt.where(Campaign.bean_id == bean_id)
    if brew_setup_id is not None:
        stmt = stmt.where(Campaign.brew_setup_id == brew_setup_id)

    campaigns = session.exec(stmt).all()

    results = []
    for campaign in campaigns:
        bean = session.get(Bean, campaign.bean_id)
        setup = session.get(BrewSetup, campaign.brew_setup_id)
        results.append(
            CampaignListRead(
                id=campaign.id,
                bean_name=bean.name if bean else None,
                brew_setup_name=setup.name if setup else None,
                phase=campaign.phase,
                measurement_count=campaign.measurement_count,
                best_score=campaign.best_score,
                created_at=campaign.created_at,
            )
        )

    return results


@router.get(
    "/optimize/campaigns/{campaign_id}",
    response_model=CampaignDetailRead,
)
def get_campaign(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> CampaignDetailRead:
    """Get campaign detail with effective parameter ranges.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    CampaignDetailRead
        Campaign with effective ranges.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
    """
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    return _campaign_to_detail(session, campaign)


@router.delete("/optimize/campaigns/{campaign_id}")
def reset_campaign(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> dict:
    """Reset campaign: clear BayBE state, keep brew records.

    Sets ``campaign_json`` to None, ``phase`` to ``"random"``,
    ``measurement_count`` to 0, ``best_score`` to None. Deletes
    related recommendations and clears fingerprints.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    dict
        Confirmation message.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
    """
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Reset campaign state
    campaign.campaign_json = None
    campaign.phase = "random"
    campaign.measurement_count = 0
    campaign.best_score = None
    campaign.bounds_fingerprint = None
    campaign.param_fingerprint = None

    # Delete related recommendations
    recommendations = session.exec(
        select(Recommendation).where(
            Recommendation.campaign_id == campaign_id
        )
    ).all()
    for rec in recommendations:
        session.delete(rec)

    session.add(campaign)
    session.commit()

    return {"detail": "Campaign reset."}


# ======================================================================
# Campaign Progress
# ======================================================================


@router.get(
    "/optimize/campaigns/{campaign_id}/progress",
    response_model=CampaignProgress,
)
def get_campaign_progress(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> CampaignProgress:
    """Get optimization progress and convergence data.

    Queries brews for the campaign's bean+setup combination, builds a
    chronological score history, and computes convergence status.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    CampaignProgress
        Progress summary with convergence info and score history.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
    """
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Query brews for this bean+setup combination, ordered by brewed_at
    stmt = (
        select(Brew)
        .join(Bag, Brew.bag_id == Bag.id)
        .where(
            Bag.bean_id == campaign.bean_id,
            Brew.brew_setup_id == campaign.brew_setup_id,
            Brew.retired_at.is_(None),
        )
        .order_by(Brew.brewed_at.asc())
    )
    brews = session.exec(stmt).all()

    # Build score history
    score_history = []
    for i, brew in enumerate(brews, 1):
        taste = brew.taste
        score_history.append(
            ScoreHistoryEntry(
                shot_number=i,
                score=taste.score if taste else None,
                is_failed=brew.is_failed,
                phase=None,
            )
        )

    # Compute convergence status
    valid_scores = [
        e.score
        for e in score_history
        if not e.is_failed and e.score is not None
    ]
    valid_count = len(valid_scores)

    if valid_count < 3:
        convergence_status = "getting_started"
    elif campaign.phase == "random":
        convergence_status = "exploring"
    elif campaign.phase == "learning":
        convergence_status = "learning"
    elif campaign.phase == "optimizing":
        convergence_status = "converged"
    else:
        convergence_status = "exploring"

    # Compute improvement rate: compare best of last 3 valid vs previous 3
    improvement_rate = None
    if valid_count >= 6:
        recent_best = max(valid_scores[-3:])
        previous_best = max(valid_scores[-6:-3])
        if previous_best > 0:
            improvement_rate = round(
                (recent_best - previous_best) / previous_best, 4
            )

    return CampaignProgress(
        phase=campaign.phase,
        measurement_count=campaign.measurement_count,
        best_score=campaign.best_score,
        convergence=ConvergenceInfo(
            status=convergence_status,
            improvement_rate=improvement_rate,
        ),
        score_history=score_history,
    )


# ======================================================================
# Posterior Predictions
# ======================================================================


@router.get(
    "/optimize/campaigns/{campaign_id}/posterior",
    response_model=PosteriorResponse,
)
def get_posterior_predictions(
    campaign_id: uuid.UUID,
    session: SessionDep,
    params: str = Query(..., description="Comma-separated 1-2 parameter names"),
    points: int = Query(30, ge=5, le=100, description="Grid resolution per axis"),
) -> PosteriorResponse:
    """Compute posterior mean and std over a parameter grid.

    Sweeps 1 or 2 parameters while holding all others at their
    best-known values. Returns the surrogate model predictions
    and actual measurements for chart overlay.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.
    params : str
        Comma-separated list of 1 or 2 parameter names to sweep.
    points : int
        Number of grid points per swept axis (5-100, default 30).

    Returns
    -------
    PosteriorResponse
        Grid values, predicted mean/std, and measurement overlay.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
        422 if campaign has no trained model, <2 measurements,
        invalid parameter names, or categorical parameters requested.
    """
    import numpy as np
    import pandas as pd
    from baybe import Campaign as BaybeCampaign

    # 1. Load campaign
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not campaign.campaign_json:
        raise HTTPException(
            status_code=422,
            detail="Campaign has no trained model. Request a recommendation first.",
        )

    # 2. Parse param names
    param_names = [p.strip() for p in params.split(",") if p.strip()]
    if not 1 <= len(param_names) <= 2:
        raise HTTPException(
            status_code=422,
            detail="Provide 1 or 2 comma-separated parameter names.",
        )

    # 3. Compute effective ranges
    ranges = _compute_campaign_ranges(session, campaign)
    range_map = {r.parameter_name: r for r in ranges}

    # 4. Validate requested params exist and are continuous
    for pname in param_names:
        if pname not in range_map:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown parameter: '{pname}'.",
            )
        if range_map[pname].allowed_values is not None:
            raise HTTPException(
                status_code=422,
                detail=f"Parameter '{pname}' is categorical; only continuous parameters are supported.",
            )

    # 5. Load measurements (same query pattern as taskiq worker)
    stmt = (
        select(Brew)
        .join(Bag, Brew.bag_id == Bag.id)
        .join(BrewTaste, Brew.id == BrewTaste.brew_id)
        .where(
            Bag.bean_id == campaign.bean_id,
            Brew.brew_setup_id == campaign.brew_setup_id,
            Brew.is_failed == False,  # noqa: E712
            Brew.retired_at.is_(None),  # type: ignore[union-attr]
            BrewTaste.score.is_not(None),  # type: ignore[union-attr]
        )
    )
    brews = session.exec(stmt).all()

    # 6. Build measurement points for overlay
    all_param_names = [r.parameter_name for r in ranges]
    measurement_points: list[MeasurementPoint] = []
    for brew in brews:
        values = {}
        has_all = True
        for pname in all_param_names:
            val = getattr(brew, pname, None)
            if val is None:
                has_all = False
                break
            values[pname] = val
        if has_all and brew.taste and brew.taste.score is not None:
            measurement_points.append(
                MeasurementPoint(values=values, score=brew.taste.score)
            )

    # 7. Validate >= 2 valid measurements
    if len(measurement_points) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 valid measurements, found {len(measurement_points)}.",
        )

    # 8. Find best-known values from highest-scoring measurement
    best_measurement = max(measurement_points, key=lambda m: m.score)
    best_values = best_measurement.values

    # 9. Build grid DataFrame
    grid_arrays: list[list[float]] = []
    for pname in param_names:
        r = range_map[pname]
        grid_arrays.append(
            np.linspace(r.min_value, r.max_value, points).tolist()
        )

    if len(param_names) == 1:
        # 1D: single column swept, others held constant
        grid_df_rows = []
        for val in grid_arrays[0]:
            row: dict = {}
            for r in ranges:
                if r.parameter_name == param_names[0]:
                    row[r.parameter_name] = val
                elif r.parameter_name in best_values:
                    row[r.parameter_name] = best_values[r.parameter_name]
                elif r.allowed_values is not None:
                    # Categorical: use first allowed value
                    row[r.parameter_name] = r.allowed_values.split(",")[0].strip()
                else:
                    # Numeric: use midpoint
                    row[r.parameter_name] = (r.min_value + r.max_value) / 2
            grid_df_rows.append(row)
        grid_df = pd.DataFrame(grid_df_rows)
    else:
        # 2D: meshgrid for two swept params
        mesh_0, mesh_1 = np.meshgrid(grid_arrays[0], grid_arrays[1])
        grid_df_rows = []
        for i in range(points):
            for j in range(points):
                row = {}
                for r in ranges:
                    if r.parameter_name == param_names[0]:
                        row[r.parameter_name] = float(mesh_0[i, j])
                    elif r.parameter_name == param_names[1]:
                        row[r.parameter_name] = float(mesh_1[i, j])
                    elif r.parameter_name in best_values:
                        row[r.parameter_name] = best_values[r.parameter_name]
                    elif r.allowed_values is not None:
                        row[r.parameter_name] = r.allowed_values.split(",")[0].strip()
                    else:
                        row[r.parameter_name] = (r.min_value + r.max_value) / 2
                grid_df_rows.append(row)
        grid_df = pd.DataFrame(grid_df_rows)

    # 10. Call posterior_stats
    baybe_campaign = BaybeCampaign.from_json(campaign.campaign_json)
    stats_df = baybe_campaign.posterior_stats(grid_df)

    mean_vals = stats_df["score_mean"].tolist()
    std_vals = stats_df["score_std"].tolist()

    # 11. Reshape for 2D case
    if len(param_names) == 2:
        mean_2d = []
        std_2d = []
        for i in range(points):
            row_start = i * points
            row_end = row_start + points
            mean_2d.append(mean_vals[row_start:row_end])
            std_2d.append(std_vals[row_start:row_end])
        mean_vals = mean_2d
        std_vals = std_2d

    # 12. Return response
    return PosteriorResponse(
        params=param_names,
        grid=grid_arrays,
        mean=mean_vals,
        std=std_vals,
        measurements=measurement_points,
    )


# ======================================================================
# Feature Importance (SHAP)
# ======================================================================


@router.get(
    "/optimize/campaigns/{campaign_id}/feature-importance",
    response_model=FeatureImportanceResponse,
)
def get_feature_importance(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> FeatureImportanceResponse:
    """Compute per-parameter feature importance via SHAP.

    Uses the BayBE campaign's trained surrogate model and SHAP
    KernelExplainer to estimate how much each parameter contributes
    to the predicted score. Requires at least 3 measurements.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    FeatureImportanceResponse
        Parameter names and importance values sorted descending.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
        422 if campaign has no trained model or < 3 measurements.
    """
    import numpy as np
    from baybe import Campaign as BaybeCampaign
    from baybe.insights.shap import SHAPInsight

    # 1. Load campaign
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not campaign.campaign_json:
        raise HTTPException(
            status_code=422,
            detail="Campaign has no trained model. Request a recommendation first.",
        )

    # 2. Validate minimum measurement count
    if campaign.measurement_count < 3:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 3 measurements for SHAP analysis, found {campaign.measurement_count}.",
        )

    # 3. Restore BayBE campaign and compute SHAP insight
    baybe_campaign = BaybeCampaign.from_json(campaign.campaign_json)
    insight = SHAPInsight.from_campaign(baybe_campaign)

    # 4. Extract per-feature importance from the SHAP explanation
    #    explain() returns a tuple of shap.Explanation (one per target);
    #    we use target 0 (single-objective).
    explanation = insight.explain_target(0)
    feature_names = list(explanation.feature_names)
    importance_values = np.abs(explanation.values).mean(axis=0).tolist()

    # 5. Sort by importance descending
    paired = sorted(
        zip(feature_names, importance_values),
        key=lambda x: x[1],
        reverse=True,
    )
    sorted_names = [p[0] for p in paired]
    sorted_importance = [round(p[1], 6) for p in paired]

    return FeatureImportanceResponse(
        parameters=sorted_names,
        importance=sorted_importance,
        measurement_count=campaign.measurement_count,
    )


# ======================================================================
# Method Parameter Defaults
# ======================================================================


@router.get(
    "/optimize/defaults/{brew_method_id}",
    response_model=list[MethodParameterDefaultRead],
)
def get_method_defaults(
    brew_method_id: uuid.UUID,
    session: SessionDep,
) -> list[MethodParameterDefaultRead]:
    """Get parameter defaults for a brew method.

    Parameters
    ----------
    brew_method_id : uuid.UUID
        Primary key of the brew method.
    session : SessionDep
        Database session.

    Returns
    -------
    list[MethodParameterDefaultRead]
        All parameter defaults for the given brew method.

    Raises
    ------
    HTTPException
        404 if the brew method does not exist.
    """
    method = session.get(BrewMethod, brew_method_id)
    if method is None:
        raise HTTPException(status_code=404, detail="BrewMethod not found.")

    defaults = session.exec(
        select(MethodParameterDefault).where(
            MethodParameterDefault.brew_method_id == brew_method_id
        )
    ).all()

    return defaults  # type: ignore[return-value]


# ======================================================================
# Recommendation & Job Endpoints
# ======================================================================


class RecommendationLinkPayload(SQLModel):
    """Payload for linking a brew to a recommendation.

    Attributes
    ----------
    brew_id : uuid.UUID
        ID of the brew to link.
    """

    brew_id: uuid.UUID


@router.post(
    "/optimize/campaigns/{campaign_id}/recommend",
    status_code=202,
)
async def request_recommendation(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> dict:
    """Kick off an async BayBE recommendation.

    Creates an :class:`OptimizationJob` and dispatches the
    ``generate_recommendation`` taskiq task.  With ``InMemoryBroker``
    the task runs inline/synchronously.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    dict
        ``{"job_id": "<uuid>", "status": "pending"}``.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
    """
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    job = OptimizationJob(
        campaign_id=campaign_id,
        job_type="recommend",
        status="pending",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Kick the taskiq task (InMemoryBroker may run it inline)
    await generate_recommendation.kiq(str(job.id))

    return {"job_id": str(job.id), "status": "pending"}


@router.get(
    "/optimize/jobs/{job_id}",
    response_model=OptimizationJobRead,
)
def get_job(
    job_id: uuid.UUID,
    session: SessionDep,
) -> OptimizationJobRead:
    """Poll job status.

    Parameters
    ----------
    job_id : uuid.UUID
        Primary key of the optimization job.
    session : SessionDep
        Database session.

    Returns
    -------
    OptimizationJobRead
        Current job state.

    Raises
    ------
    HTTPException
        404 if the job does not exist.
    """
    job = session.get(OptimizationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job  # type: ignore[return-value]


@router.get(
    "/optimize/campaigns/{campaign_id}/recommendations",
    response_model=list[RecommendationRead],
)
def list_recommendations(
    campaign_id: uuid.UUID,
    session: SessionDep,
) -> list[RecommendationRead]:
    """List recommendations for a campaign.

    Parameters
    ----------
    campaign_id : uuid.UUID
        Primary key of the campaign.
    session : SessionDep
        Database session.

    Returns
    -------
    list[RecommendationRead]
        All recommendations for the given campaign.

    Raises
    ------
    HTTPException
        404 if the campaign does not exist.
    """
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    recs = session.exec(
        select(Recommendation).where(
            Recommendation.campaign_id == campaign_id
        )
    ).all()
    return [RecommendationRead.model_validate(r) for r in recs]


@router.get(
    "/optimize/recommendations/{recommendation_id}",
    response_model=RecommendationRead,
)
def get_recommendation(
    recommendation_id: uuid.UUID,
    session: SessionDep,
) -> RecommendationRead:
    """Get recommendation detail.

    Parameters
    ----------
    recommendation_id : uuid.UUID
        Primary key of the recommendation.
    session : SessionDep
        Database session.

    Returns
    -------
    RecommendationRead
        Recommendation with ``parameter_values`` parsed as dict.

    Raises
    ------
    HTTPException
        404 if the recommendation does not exist.
    """
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail="Recommendation not found."
        )
    return RecommendationRead.model_validate(rec)


@router.post(
    "/optimize/recommendations/{recommendation_id}/skip",
    response_model=RecommendationRead,
)
def skip_recommendation(
    recommendation_id: uuid.UUID,
    session: SessionDep,
) -> RecommendationRead:
    """Mark a recommendation as skipped.

    Parameters
    ----------
    recommendation_id : uuid.UUID
        Primary key of the recommendation.
    session : SessionDep
        Database session.

    Returns
    -------
    RecommendationRead
        Updated recommendation with ``status='skipped'``.

    Raises
    ------
    HTTPException
        404 if the recommendation does not exist.
    """
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail="Recommendation not found."
        )
    rec.status = "skipped"
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return RecommendationRead.model_validate(rec)


@router.post(
    "/optimize/recommendations/{recommendation_id}/link",
    response_model=RecommendationRead,
)
def link_recommendation(
    recommendation_id: uuid.UUID,
    payload: RecommendationLinkPayload,
    session: SessionDep,
) -> RecommendationRead:
    """Link a brew to a recommendation.

    Sets the recommendation status to ``"brewed"`` and associates
    the given brew.

    Parameters
    ----------
    recommendation_id : uuid.UUID
        Primary key of the recommendation.
    payload : RecommendationLinkPayload
        Contains ``brew_id`` to link.
    session : SessionDep
        Database session.

    Returns
    -------
    RecommendationRead
        Updated recommendation with ``status='brewed'`` and ``brew_id`` set.

    Raises
    ------
    HTTPException
        404 if the recommendation or brew does not exist.
    """
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail="Recommendation not found."
        )

    brew = session.get(Brew, payload.brew_id)
    if brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    rec.brew_id = payload.brew_id
    rec.status = "brewed"
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return RecommendationRead.model_validate(rec)


# ======================================================================
# Person Preferences
# ======================================================================


@router.get(
    "/optimize/people/{person_id}/preferences",
    response_model=PersonPreferences,
)
def get_person_preferences(
    person_id: uuid.UUID,
    session: SessionDep,
) -> PersonPreferences:
    """Get per-person bean preference analytics.

    Aggregates a person's brewing history into top beans, flavor profile,
    roast preference distribution, origin preferences, and method breakdown.

    Parameters
    ----------
    person_id : uuid.UUID
        Primary key of the person.
    session : SessionDep
        Database session.

    Returns
    -------
    PersonPreferences
        Aggregated preference data.

    Raises
    ------
    HTTPException
        404 if the person does not exist.
    """
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    # 1. Brew stats: total brew count and average taste score
    brew_stats_stmt = (
        select(func.count(Brew.id), func.avg(BrewTaste.score))
        .outerjoin(BrewTaste, Brew.id == BrewTaste.brew_id)
        .where(Brew.person_id == person_id, Brew.retired_at.is_(None))
    )
    total_brews, avg_score = session.exec(brew_stats_stmt).one()  # type: ignore[misc]

    # 2. Top beans: GROUP BY bean, ORDER BY AVG(score) DESC, LIMIT 10
    top_beans_stmt = (
        select(
            Bean.id,
            Bean.name,
            func.avg(BrewTaste.score),
            func.count(Brew.id),
        )
        .join(Bag, Brew.bag_id == Bag.id)
        .join(Bean, Bag.bean_id == Bean.id)
        .join(BrewTaste, Brew.id == BrewTaste.brew_id)
        .where(
            Brew.person_id == person_id,
            Brew.retired_at.is_(None),
            BrewTaste.score.is_not(None),
        )
        .group_by(Bean.id, Bean.name)
        .order_by(func.avg(BrewTaste.score).desc())
        .limit(10)
    )
    top_beans_rows = session.exec(top_beans_stmt).all()  # type: ignore[call-overload]
    top_beans = [
        TopBean(
            bean_id=row[0],
            name=row[1],
            avg_score=round(float(row[2]), 2),
            brew_count=row[3],
        )
        for row in top_beans_rows
    ]

    # 3. Flavor profile: COUNT flavor_tag occurrences
    flavor_stmt = (
        select(FlavorTag.name, func.count(FlavorTag.id))
        .select_from(Brew)
        .join(BrewTaste, Brew.id == BrewTaste.brew_id)
        .join(
            BrewTasteFlavorTagLink,
            BrewTaste.id == BrewTasteFlavorTagLink.brew_taste_id,
        )
        .join(
            FlavorTag,
            BrewTasteFlavorTagLink.flavor_tag_id == FlavorTag.id,
        )
        .where(Brew.person_id == person_id, Brew.retired_at.is_(None))
        .group_by(FlavorTag.name)
        .order_by(func.count(FlavorTag.id).desc())
    )
    flavor_rows = session.exec(flavor_stmt).all()  # type: ignore[call-overload]
    flavor_profile = [
        FlavorFrequency(tag=row[0], frequency=row[1]) for row in flavor_rows
    ]

    # 4. Roast preference: AVG(roast_degree) and distribution
    roast_preference: dict = {}
    roast_stmt = (
        select(Bean.roast_degree)
        .select_from(Brew)
        .join(Bag, Brew.bag_id == Bag.id)
        .join(Bean, Bag.bean_id == Bean.id)
        .where(
            Brew.person_id == person_id,
            Brew.retired_at.is_(None),
            Bean.roast_degree.is_not(None),
        )
    )
    roast_values = session.exec(roast_stmt).all()  # type: ignore[call-overload]
    if roast_values:
        avg_degree = sum(roast_values) / len(roast_values)
        light = sum(1 for v in roast_values if v <= 3)
        medium = sum(1 for v in roast_values if 4 <= v <= 6)
        dark = sum(1 for v in roast_values if v >= 7)
        roast_preference = {
            "avg_degree": round(float(avg_degree), 2),
            "distribution": {
                "light": light,
                "medium": medium,
                "dark": dark,
            },
        }

    # 5. Origin preferences: GROUP BY origin name, AVG score, count
    origin_display = case(
        (Origin.country.is_not(None), Origin.country),  # type: ignore[union-attr]
        else_=Origin.name,
    )
    origin_stmt = (
        select(
            origin_display,
            func.avg(BrewTaste.score),
            func.count(Brew.id),
        )
        .select_from(Brew)
        .join(Bag, Brew.bag_id == Bag.id)
        .join(Bean, Bag.bean_id == Bean.id)
        .join(BeanOriginLink, Bean.id == BeanOriginLink.bean_id)
        .join(Origin, BeanOriginLink.origin_id == Origin.id)
        .join(BrewTaste, Brew.id == BrewTaste.brew_id)
        .where(
            Brew.person_id == person_id,
            Brew.retired_at.is_(None),
            BrewTaste.score.is_not(None),
        )
        .group_by(origin_display)
        .order_by(func.avg(BrewTaste.score).desc())
    )
    origin_rows = session.exec(origin_stmt).all()  # type: ignore[call-overload]
    origin_preferences = [
        OriginPreference(
            origin=row[0],
            avg_score=round(float(row[1]), 2),
            brew_count=row[2],
        )
        for row in origin_rows
    ]

    # 6. Method breakdown: GROUP BY brew_method, COUNT + AVG(score)
    method_stmt = (
        select(
            BrewMethod.name,
            func.count(Brew.id),
            func.avg(BrewTaste.score),
        )
        .select_from(Brew)
        .join(BrewSetup, Brew.brew_setup_id == BrewSetup.id)
        .join(BrewMethod, BrewSetup.brew_method_id == BrewMethod.id)
        .join(BrewTaste, Brew.id == BrewTaste.brew_id)
        .where(
            Brew.person_id == person_id,
            Brew.retired_at.is_(None),
            BrewTaste.score.is_not(None),
        )
        .group_by(BrewMethod.name)
        .order_by(func.count(Brew.id).desc())
    )
    method_rows = session.exec(method_stmt).all()  # type: ignore[call-overload]
    method_breakdown = [
        MethodBreakdown(
            method=row[0],
            brew_count=row[1],
            avg_score=round(float(row[2]), 2),
        )
        for row in method_rows
    ]

    return PersonPreferences(
        person={"id": str(person.id), "name": person.name},
        brew_stats={
            "total_brews": total_brews,
            "avg_score": round(float(avg_score), 2) if avg_score is not None else None,
        },
        top_beans=top_beans,
        flavor_profile=flavor_profile,
        roast_preference=roast_preference,
        origin_preferences=origin_preferences,
        method_breakdown=method_breakdown,
    )
