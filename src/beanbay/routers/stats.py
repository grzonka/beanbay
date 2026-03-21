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
