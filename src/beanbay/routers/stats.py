"""Read-only stats endpoints for dashboard widgets."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import Integer
from sqlalchemy import func as sa_func
from sqlmodel import select

from beanbay.dependencies import OptionalPersonIdDep, SessionDep
from beanbay.models.bean import Bag, Bean, BeanOriginLink
from beanbay.models.brew import Brew, BrewSetup, BrewTaste, BrewTasteFlavorTagLink
from beanbay.models.cupping import Cupping, CuppingFlavorTagLink
from beanbay.models.equipment import Brewer, Grinder, Paper, Water
from beanbay.models.rating import BeanRating, BeanTaste, BeanTasteFlavorTagLink
from beanbay.models.tag import BrewMethod, FlavorTag, Roaster, Origin
from beanbay.schemas.stats import (
    BeanStatsRead,
    BeanTasteAxisAverages,
    BeanTasteStats,
    BrewStatsRead,
    BrewTasteAxisAverages,
    BrewTasteStats,
    CuppingStatsRead,
    EquipmentStatsRead,
    FlavorTagCount,
    MethodBrewCount,
    NamedUsageCount,
    OriginBeanCount,
    RoasterBeanCount,
    SetupUsage,
    TasteStatsRead,
)

router = APIRouter(tags=["Stats"])


def _r(val: float | None) -> float | None:
    """Round a float to 2 decimal places, or return None.

    Parameters
    ----------
    val : float | None
        Value to round.

    Returns
    -------
    float | None
        Rounded value, or ``None`` if input is ``None``.
    """
    return round(val, 2) if val is not None else None


def _week_start() -> datetime:
    """Return Monday 00:00 UTC of the current week.

    Returns
    -------
    datetime
        Monday midnight UTC of the current week.
    """
    now = datetime.now(timezone.utc)
    monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monday -= timedelta(days=now.weekday())
    return monday


def _month_start() -> datetime:
    """Return 1st of current month 00:00 UTC.

    Returns
    -------
    datetime
        First day of the current month at midnight UTC.
    """
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _base_brew_filter(person_id: uuid.UUID | None):
    """Return base WHERE conditions for non-retired brews, optionally by person.

    Parameters
    ----------
    person_id : uuid.UUID | None
        If provided, filter brews to this person only.

    Returns
    -------
    list
        List of SQLAlchemy filter conditions.
    """
    conditions = [Brew.retired_at.is_(None)]  # type: ignore[union-attr]
    if person_id is not None:
        conditions.append(Brew.person_id == person_id)
    return conditions


@router.get("/stats/brews", response_model=BrewStatsRead)
def get_brew_stats(
    session: SessionDep,
    person_id: OptionalPersonIdDep,
) -> BrewStatsRead:
    """Aggregated brew statistics.

    Parameters
    ----------
    session : Session
        Database session.
    person_id : uuid.UUID | None
        Optional person filter resolved by dependency.

    Returns
    -------
    BrewStatsRead
        Aggregated brew statistics including counts, averages, and per-method breakdown.
    """
    conditions = _base_brew_filter(person_id)

    # Scalar aggregates
    row = session.exec(
        select(
            sa_func.count().label("total"),
            sa_func.sum(Brew.is_failed.cast(Integer)).label("total_failed"),  # type: ignore[union-attr]
            sa_func.avg(Brew.dose).label("avg_dose"),
            sa_func.avg(Brew.yield_amount).label("avg_yield"),
            sa_func.avg(Brew.total_time).label("avg_time"),
            sa_func.max(Brew.brewed_at).label("last_brewed"),
        ).where(*conditions)
    ).one()

    total = row.total or 0
    total_failed = int(row.total_failed or 0)

    # This week / this month
    week_start = _week_start()
    month_start = _month_start()

    this_week = session.exec(
        select(sa_func.count()).where(
            *conditions, Brew.brewed_at >= week_start
        )
    ).one()

    this_month = session.exec(
        select(sa_func.count()).where(
            *conditions, Brew.brewed_at >= month_start
        )
    ).one()

    # By method
    method_rows = session.exec(
        select(
            BrewMethod.id,
            BrewMethod.name,
            sa_func.count().label("cnt"),
        )
        .join(BrewSetup, BrewSetup.brew_method_id == BrewMethod.id)
        .join(Brew, Brew.brew_setup_id == BrewSetup.id)
        .where(*conditions)
        .group_by(BrewMethod.id, BrewMethod.name)
        .order_by(sa_func.count().desc())
    ).all()

    return BrewStatsRead(
        total=total,
        this_week=this_week,
        this_month=this_month,
        total_failed=total_failed,
        fail_rate=round(total_failed / total, 4) if total > 0 else None,
        avg_dose_g=round(row.avg_dose, 2) if row.avg_dose is not None else None,
        avg_yield_g=round(row.avg_yield, 2) if row.avg_yield is not None else None,
        avg_brew_time_s=round(row.avg_time, 2) if row.avg_time is not None else None,
        last_brewed_at=row.last_brewed,
        by_method=[
            MethodBrewCount(
                brew_method_id=r[0], brew_method_name=r[1], count=r[2]
            )
            for r in method_rows
        ],
    )


@router.get("/stats/beans", response_model=BeanStatsRead)
def get_bean_stats(session: SessionDep) -> BeanStatsRead:
    """Aggregated bean and bag statistics.

    Parameters
    ----------
    session : Session
        Database session.

    Returns
    -------
    BeanStatsRead
        Aggregated bean and bag statistics including counts, breakdowns, and averages.
    """
    not_retired = Bean.retired_at.is_(None)  # type: ignore[union-attr]
    bag_not_retired = Bag.retired_at.is_(None)  # type: ignore[union-attr]

    # Bean counts
    total_beans = session.exec(
        select(sa_func.count()).where(not_retired).select_from(Bean)
    ).one()

    # beans_active: non-retired beans with >= 1 non-retired bag
    beans_active = session.exec(
        select(sa_func.count(sa_func.distinct(Bean.id)))
        .join(Bag, Bag.bean_id == Bean.id)
        .where(not_retired, bag_not_retired)
    ).one()

    # Mix type breakdown
    mix_rows = session.exec(
        select(Bean.bean_mix_type, sa_func.count())
        .where(not_retired)
        .group_by(Bean.bean_mix_type)
    ).all()
    mix_type_breakdown = {str(r[0].value) if r[0] else "unknown": r[1] for r in mix_rows}

    # Use type breakdown (exclude None)
    use_rows = session.exec(
        select(Bean.bean_use_type, sa_func.count())
        .where(not_retired, Bean.bean_use_type.is_not(None))  # type: ignore[union-attr]
        .group_by(Bean.bean_use_type)
    ).all()
    use_type_breakdown = {str(r[0].value): r[1] for r in use_rows}

    # Top roasters
    roaster_rows = session.exec(
        select(Roaster.id, Roaster.name, sa_func.count().label("cnt"))
        .join(Bean, Bean.roaster_id == Roaster.id)
        .where(not_retired)
        .group_by(Roaster.id, Roaster.name)
        .order_by(sa_func.count().desc())
    ).all()

    # Top origins
    origin_rows = session.exec(
        select(Origin.id, Origin.name, sa_func.count().label("cnt"))
        .join(BeanOriginLink, BeanOriginLink.origin_id == Origin.id)
        .join(Bean, Bean.id == BeanOriginLink.bean_id)
        .where(not_retired)
        .group_by(Origin.id, Origin.name)
        .order_by(sa_func.count().desc())
    ).all()

    # Bag stats
    total_bags = session.exec(
        select(sa_func.count()).where(bag_not_retired).select_from(Bag)
    ).one()
    bags_active = total_bags  # same as total non-retired

    bags_unopened = session.exec(
        select(sa_func.count()).where(
            bag_not_retired, Bag.opened_at.is_(None)  # type: ignore[union-attr]
        ).select_from(Bag)
    ).one()

    bag_agg = session.exec(
        select(
            sa_func.avg(Bag.weight).label("avg_w"),
            sa_func.avg(Bag.price).label("avg_p"),
        ).where(bag_not_retired)
    ).one()

    return BeanStatsRead(
        total_beans=total_beans,
        beans_active=beans_active,
        mix_type_breakdown=mix_type_breakdown,
        use_type_breakdown=use_type_breakdown,
        top_roasters=[
            RoasterBeanCount(roaster_id=r[0], roaster_name=r[1], count=r[2])
            for r in roaster_rows
        ],
        top_origins=[
            OriginBeanCount(origin_id=r[0], origin_name=r[1], count=r[2])
            for r in origin_rows
        ],
        total_bags=total_bags,
        bags_active=bags_active,
        bags_unopened=bags_unopened,
        avg_bag_weight_g=round(bag_agg.avg_w, 2) if bag_agg.avg_w is not None else None,
        avg_bag_price=round(bag_agg.avg_p, 2) if bag_agg.avg_p is not None else None,
    )


def _flavor_tag_counts(session, link_model, entity_conditions):
    """Query top flavor tags through a M2M link table.

    Parameters
    ----------
    session : Session
        DB session.
    link_model : type
        The M2M link model (e.g. BrewTasteFlavorTagLink).
    entity_conditions : list
        WHERE conditions filtering which link table rows to include.

    Returns
    -------
    list[FlavorTagCount]
    """
    rows = session.exec(
        select(
            FlavorTag.id,
            FlavorTag.name,
            sa_func.count().label("cnt"),
        )
        .join(link_model, link_model.flavor_tag_id == FlavorTag.id)
        .where(*entity_conditions)
        .group_by(FlavorTag.id, FlavorTag.name)
        .order_by(sa_func.count().desc())
    ).all()
    return [
        FlavorTagCount(flavor_tag_id=r[0], flavor_tag_name=r[1], count=r[2])
        for r in rows
    ]


@router.get("/stats/taste", response_model=TasteStatsRead)
def get_taste_stats(
    session: SessionDep,
    person_id: OptionalPersonIdDep,
) -> TasteStatsRead:
    """Aggregated sensory statistics.

    Parameters
    ----------
    session : Session
        Database session.
    person_id : uuid.UUID | None
        Optional person filter resolved by dependency.

    Returns
    -------
    TasteStatsRead
        Aggregated taste statistics for both brews and beans.
    """
    # --- Brew Taste ---
    brew_conditions = [Brew.retired_at.is_(None)]  # type: ignore[union-attr]
    if person_id is not None:
        brew_conditions.append(Brew.person_id == person_id)

    bt_agg = session.exec(
        select(
            sa_func.count().label("total"),
            sa_func.avg(BrewTaste.score),
            sa_func.avg(BrewTaste.acidity),
            sa_func.avg(BrewTaste.sweetness),
            sa_func.avg(BrewTaste.body),
            sa_func.avg(BrewTaste.bitterness),
            sa_func.avg(BrewTaste.balance),
            sa_func.avg(BrewTaste.aftertaste),
        )
        .join(Brew, Brew.id == BrewTaste.brew_id)
        .where(*brew_conditions)
    ).one()

    # Best brew taste score
    best_bt = session.exec(
        select(BrewTaste.score, BrewTaste.brew_id)
        .join(Brew, Brew.id == BrewTaste.brew_id)
        .where(*brew_conditions, BrewTaste.score.is_not(None))  # type: ignore[union-attr]
        .order_by(BrewTaste.score.desc())  # type: ignore[union-attr]
        .limit(1)
    ).first()

    # Brew taste flavor tags
    bt_link_conditions = [
        BrewTasteFlavorTagLink.brew_taste_id.in_(  # type: ignore[union-attr]
            select(BrewTaste.id)
            .join(Brew, Brew.id == BrewTaste.brew_id)
            .where(*brew_conditions)
        )
    ]
    bt_tags = _flavor_tag_counts(session, BrewTasteFlavorTagLink, bt_link_conditions)

    brew_taste = BrewTasteStats(
        total_rated=bt_agg[0] or 0,
        avg_axes=BrewTasteAxisAverages(
            score=_r(bt_agg[1]),
            acidity=_r(bt_agg[2]),
            sweetness=_r(bt_agg[3]),
            body=_r(bt_agg[4]),
            bitterness=_r(bt_agg[5]),
            balance=_r(bt_agg[6]),
            aftertaste=_r(bt_agg[7]),
        ),
        best_score=best_bt[0] if best_bt else None,
        best_brew_id=best_bt[1] if best_bt else None,
        top_flavor_tags=bt_tags,
    )

    # --- Bean Taste ---
    bean_conditions = [Bean.retired_at.is_(None)]  # type: ignore[union-attr]
    rating_conditions = [BeanRating.retired_at.is_(None)]  # type: ignore[union-attr]
    if person_id is not None:
        rating_conditions.append(BeanRating.person_id == person_id)

    bnt_agg = session.exec(
        select(
            sa_func.count().label("total"),
            sa_func.avg(BeanTaste.score),
            sa_func.avg(BeanTaste.acidity),
            sa_func.avg(BeanTaste.sweetness),
            sa_func.avg(BeanTaste.body),
            sa_func.avg(BeanTaste.complexity),
            sa_func.avg(BeanTaste.aroma),
            sa_func.avg(BeanTaste.clean_cup),
        )
        .join(BeanRating, BeanRating.id == BeanTaste.bean_rating_id)
        .join(Bean, Bean.id == BeanRating.bean_id)
        .where(*bean_conditions, *rating_conditions)
    ).one()

    # Best bean taste score → resolve bean_id through bean_rating
    best_bnt = session.exec(
        select(BeanTaste.score, BeanRating.bean_id)
        .join(BeanRating, BeanRating.id == BeanTaste.bean_rating_id)
        .join(Bean, Bean.id == BeanRating.bean_id)
        .where(*bean_conditions, *rating_conditions, BeanTaste.score.is_not(None))  # type: ignore[union-attr]
        .order_by(BeanTaste.score.desc())  # type: ignore[union-attr]
        .limit(1)
    ).first()

    # Bean taste flavor tags
    bnt_link_conditions = [
        BeanTasteFlavorTagLink.bean_taste_id.in_(  # type: ignore[union-attr]
            select(BeanTaste.id)
            .join(BeanRating, BeanRating.id == BeanTaste.bean_rating_id)
            .join(Bean, Bean.id == BeanRating.bean_id)
            .where(*bean_conditions, *rating_conditions)
        )
    ]
    bnt_tags = _flavor_tag_counts(session, BeanTasteFlavorTagLink, bnt_link_conditions)

    bean_taste = BeanTasteStats(
        total_rated=bnt_agg[0] or 0,
        avg_axes=BeanTasteAxisAverages(
            score=_r(bnt_agg[1]),
            acidity=_r(bnt_agg[2]),
            sweetness=_r(bnt_agg[3]),
            body=_r(bnt_agg[4]),
            complexity=_r(bnt_agg[5]),
            aroma=_r(bnt_agg[6]),
            clean_cup=_r(bnt_agg[7]),
        ),
        best_score=best_bnt[0] if best_bnt else None,
        best_bean_id=best_bnt[1] if best_bnt else None,
        top_flavor_tags=bnt_tags,
    )

    return TasteStatsRead(brew_taste=brew_taste, bean_taste=bean_taste)
