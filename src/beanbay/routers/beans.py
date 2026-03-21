"""CRUD routers for the Bean and Bag models.

Includes nested bag endpoints under ``/beans/{bean_id}/bags`` as well as
top-level ``/bags`` endpoints for cross-bean queries.
"""

import uuid
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.dependencies import SessionDep, validate_sort
from beanbay.models.bean import (
    Bag,
    Bean,
    BeanFlavorTagLink,
    BeanOriginLink,
    BeanProcessLink,
    BeanVarietyLink,
)
from beanbay.models.cupping import Cupping
from beanbay.models.tag import (
    BeanVariety,
    FlavorTag,
    Origin,
    ProcessMethod,
    Roaster,
)
from beanbay.schemas.bean import (
    BagCreate,
    BagRead,
    BagUpdate,
    BeanCreate,
    BeanRead,
    BeanUpdate,
    OriginWithPercentage,
)
from beanbay.schemas.common import PaginatedResponse

BEAN_SORTABLE = ["name", "created_at", "updated_at"]
BAG_SORTABLE = ["created_at", "updated_at", "roast_date", "weight", "price"]

router = APIRouter(tags=["Beans"])




# ======================================================================
# Helper: set M2M relationships via link models
# ======================================================================


def _set_bean_origins(
    session: Session,
    bean: Bean,
    origin_ids: list[uuid.UUID] | None,
    origins: list[OriginWithPercentage] | None,
) -> None:
    """Set origin M2M relationships on a bean.

    Supports both plain ``origin_ids`` (no percentage) and
    ``origins`` (with optional percentage).  If both are provided,
    they are merged.

    Parameters
    ----------
    session : Session
        Database session.
    bean : Bean
        The bean to update.
    origin_ids : list[uuid.UUID] | None
        Plain origin IDs to link (percentage = None).
    origins : list[OriginWithPercentage] | None
        Origin IDs with optional blend percentages.
    """
    if origin_ids is None and origins is None:
        return

    # Delete existing links
    existing = session.exec(
        select(BeanOriginLink).where(BeanOriginLink.bean_id == bean.id)
    ).all()
    for link in existing:
        session.delete(link)
    session.flush()

    # Normalize both sources into (origin_id, percentage) pairs
    pairs: list[tuple[uuid.UUID, float | None]] = []
    if origin_ids is not None:
        for oid in origin_ids:
            pairs.append((oid, None))
    if origins is not None:
        for o in origins:
            pairs.append((o.origin_id, o.percentage))

    for oid, pct in pairs:
        obj = session.get(Origin, oid)
        if obj is None:
            raise HTTPException(
                status_code=404,
                detail=f"Origin with id '{oid}' not found.",
            )
        session.add(
            BeanOriginLink(
                bean_id=bean.id, origin_id=oid, percentage=pct
            )
        )


def _set_bean_m2m(
    session: Session,
    bean: Bean,
    origin_ids: list[uuid.UUID] | None,
    origins: list[OriginWithPercentage] | None,
    process_ids: list[uuid.UUID] | None,
    variety_ids: list[uuid.UUID] | None,
    flavor_tag_ids: list[uuid.UUID] | None,
) -> None:
    """Set M2M relationships on a bean via link models.

    For each M2M list that is not ``None``, delete existing link rows
    and insert new ones.  Validates each ID and raises 404 if missing.

    Parameters
    ----------
    session : Session
        Database session.
    bean : Bean
        The bean to update.
    origin_ids : list[uuid.UUID] | None
        Plain origin IDs to link (no percentage).  ``None`` means don't touch.
    origins : list[OriginWithPercentage] | None
        Origins with optional blend percentages.  ``None`` means don't touch.
    process_ids : list[uuid.UUID] | None
        ProcessMethod IDs to link.  ``None`` means don't touch.
    variety_ids : list[uuid.UUID] | None
        BeanVariety IDs to link.  ``None`` means don't touch.
    flavor_tag_ids : list[uuid.UUID] | None
        FlavorTag IDs to link.  ``None`` means don't touch.
    """
    _set_bean_origins(session, bean, origin_ids, origins)

    if process_ids is not None:
        existing = session.exec(
            select(BeanProcessLink).where(
                BeanProcessLink.bean_id == bean.id
            )
        ).all()
        for link in existing:
            session.delete(link)
        session.flush()
        for pid in process_ids:
            obj = session.get(ProcessMethod, pid)
            if obj is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"ProcessMethod with id '{pid}' not found.",
                )
            session.add(BeanProcessLink(bean_id=bean.id, process_id=pid))

    if variety_ids is not None:
        existing = session.exec(
            select(BeanVarietyLink).where(
                BeanVarietyLink.bean_id == bean.id
            )
        ).all()
        for link in existing:
            session.delete(link)
        session.flush()
        for vid in variety_ids:
            obj = session.get(BeanVariety, vid)
            if obj is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"BeanVariety with id '{vid}' not found.",
                )
            session.add(BeanVarietyLink(bean_id=bean.id, variety_id=vid))

    if flavor_tag_ids is not None:
        existing = session.exec(
            select(BeanFlavorTagLink).where(
                BeanFlavorTagLink.bean_id == bean.id
            )
        ).all()
        for link in existing:
            session.delete(link)
        session.flush()
        for fid in flavor_tag_ids:
            obj = session.get(FlavorTag, fid)
            if obj is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"FlavorTag with id '{fid}' not found.",
                )
            session.add(
                BeanFlavorTagLink(bean_id=bean.id, flavor_tag_id=fid)
            )


# ======================================================================
# Bean CRUD
# ======================================================================


# ------------------------------------------------------------------
# GET /beans  — list with filtering, pagination, sorting
# ------------------------------------------------------------------
@router.get("/beans", response_model=PaginatedResponse[BeanRead])
def list_beans(
    *,
    q: str | None = Query(None, description="Case-insensitive name search"),
    roaster_id: uuid.UUID | None = Query(None, description="Filter by roaster"),
    origin_id: uuid.UUID | None = Query(None, description="Filter by origin"),
    process_id: uuid.UUID | None = Query(
        None, description="Filter by process method"
    ),
    variety_id: uuid.UUID | None = Query(
        None, description="Filter by bean variety"
    ),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: SessionDep,
) -> PaginatedResponse[BeanRead]:
    """List beans with optional filtering, pagination, and sorting.

    Parameters
    ----------
    q : str | None
        Case-insensitive substring match on ``name``.
    roaster_id : uuid.UUID | None
        Filter by roaster FK.
    origin_id : uuid.UUID | None
        Filter by origin (via M2M).
    process_id : uuid.UUID | None
        Filter by process method (via M2M).
    variety_id : uuid.UUID | None
        Filter by bean variety (via M2M).
    include_retired : bool
        When ``True``, include soft-deleted beans.
    limit : int
        Maximum items per page (1--200).
    offset : int
        Number of items to skip.
    sort_by : str
        Column to sort by.
    sort_dir : str
        ``"asc"`` or ``"desc"``.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PaginatedResponse[BeanRead]
        Paginated response with ``items``, ``total``, ``limit``, ``offset``.
    """
    validate_sort(sort_by, sort_dir, BEAN_SORTABLE)

    stmt = select(Bean)
    count_stmt = select(func.count()).select_from(Bean)

    if not include_retired:
        stmt = stmt.where(Bean.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Bean.retired_at.is_(None))  # type: ignore[union-attr]

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Bean.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Bean.name.ilike(pattern))  # type: ignore[union-attr]

    if roaster_id:
        stmt = stmt.where(Bean.roaster_id == roaster_id)
        count_stmt = count_stmt.where(Bean.roaster_id == roaster_id)

    if origin_id:
        stmt = stmt.join(BeanOriginLink).where(
            BeanOriginLink.origin_id == origin_id
        )
        count_stmt = count_stmt.join(BeanOriginLink).where(
            BeanOriginLink.origin_id == origin_id
        )

    if process_id:
        stmt = stmt.join(BeanProcessLink).where(
            BeanProcessLink.process_id == process_id
        )
        count_stmt = count_stmt.join(BeanProcessLink).where(
            BeanProcessLink.process_id == process_id
        )

    if variety_id:
        stmt = stmt.join(BeanVarietyLink).where(
            BeanVarietyLink.variety_id == variety_id
        )
        count_stmt = count_stmt.join(BeanVarietyLink).where(
            BeanVarietyLink.variety_id == variety_id
        )

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Bean, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)

    stmt = stmt.offset(offset).limit(limit)
    items = session.exec(stmt).all()

    return PaginatedResponse(  # type: ignore[return-value]
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# POST /beans  — create
# ------------------------------------------------------------------
@router.post("/beans", response_model=BeanRead, status_code=201)
def create_bean(
    payload: BeanCreate,
    session: SessionDep,
) -> BeanRead:
    """Create a new bean with optional M2M relationships.

    Parameters
    ----------
    payload : BeanCreate
        Bean data including optional M2M IDs.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BeanRead
        The created bean.
    """
    # Validate roaster if provided
    if payload.roaster_id is not None:
        roaster = session.get(Roaster, payload.roaster_id)
        if roaster is None:
            raise HTTPException(
                status_code=404, detail="Roaster not found."
            )

    db_bean = Bean(
        name=payload.name,
        roaster_id=payload.roaster_id,
        notes=payload.notes,
        roast_degree=payload.roast_degree,
        bean_mix_type=payload.bean_mix_type,
        bean_use_type=payload.bean_use_type,
        decaf=payload.decaf,
        url=payload.url,
        ean=payload.ean,
    )
    session.add(db_bean)
    session.flush()  # Get the ID

    _set_bean_m2m(
        session,
        db_bean,
        payload.origin_ids,
        payload.origins if payload.origins else None,
        payload.process_ids,
        payload.variety_ids,
        payload.flavor_tag_ids,
    )

    session.commit()
    session.refresh(db_bean)
    return db_bean  # type: ignore[return-value]


# ------------------------------------------------------------------
# GET /beans/{bean_id}  — detail
# ------------------------------------------------------------------
@router.get("/beans/{bean_id}", response_model=BeanRead)
def get_bean(
    bean_id: uuid.UUID,
    session: SessionDep,
) -> BeanRead:
    """Get a single bean by ID with nested relationships.

    Parameters
    ----------
    bean_id : uuid.UUID
        The bean's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BeanRead
        The bean with nested relationships.
    """
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")
    return db_bean  # type: ignore[return-value]


# ------------------------------------------------------------------
# PATCH /beans/{bean_id}  — partial update
# ------------------------------------------------------------------
@router.patch("/beans/{bean_id}", response_model=BeanRead)
def update_bean(
    bean_id: uuid.UUID,
    payload: BeanUpdate,
    session: SessionDep,
) -> BeanRead:
    """Partially update a bean, including M2M lists.

    Parameters
    ----------
    bean_id : uuid.UUID
        The bean's primary key.
    payload : BeanUpdate
        Fields to update.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BeanRead
        The updated bean.
    """
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Handle roaster_id validation
    if "roaster_id" in update_data and update_data["roaster_id"] is not None:
        roaster = session.get(Roaster, update_data["roaster_id"])
        if roaster is None:
            raise HTTPException(
                status_code=404, detail="Roaster not found."
            )

    # Extract M2M IDs (don't pass them to sqlmodel_update)
    origin_ids = update_data.pop("origin_ids", None)
    origins_raw = update_data.pop("origins", None)
    process_ids = update_data.pop("process_ids", None)
    variety_ids = update_data.pop("variety_ids", None)
    flavor_tag_ids = update_data.pop("flavor_tag_ids", None)

    # Apply scalar updates
    db_bean.sqlmodel_update(update_data)
    session.add(db_bean)
    session.flush()

    # Handle M2M only if provided (exclude_unset semantics)
    raw_unset = payload.model_dump(exclude_unset=True)

    # Convert raw origins dicts back to OriginWithPercentage objects
    origins_typed: list[OriginWithPercentage] | None = None
    if "origins" in raw_unset and origins_raw is not None:
        origins_typed = [
            OriginWithPercentage(**o) if isinstance(o, dict) else o
            for o in origins_raw
        ]

    _set_bean_m2m(
        session,
        db_bean,
        origin_ids if "origin_ids" in raw_unset else None,
        origins_typed,
        process_ids if "process_ids" in raw_unset else None,
        variety_ids if "variety_ids" in raw_unset else None,
        flavor_tag_ids if "flavor_tag_ids" in raw_unset else None,
    )

    session.commit()
    session.refresh(db_bean)
    return db_bean  # type: ignore[return-value]


# ------------------------------------------------------------------
# DELETE /beans/{bean_id}  — soft-delete
# ------------------------------------------------------------------
@router.delete("/beans/{bean_id}", response_model=BeanRead)
def delete_bean(
    bean_id: uuid.UUID,
    session: SessionDep,
) -> BeanRead:
    """Soft-delete a bean.

    Blocked with 409 Conflict if the bean has active (non-retired) bags.

    Parameters
    ----------
    bean_id : uuid.UUID
        The bean's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BeanRead
        The soft-deleted bean.
    """
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    # Block if active bags exist
    active_bag_count: int = session.exec(
        select(func.count())
        .select_from(Bag)
        .where(Bag.bean_id == bean_id, Bag.retired_at.is_(None))  # type: ignore[union-attr]
    ).one()  # type: ignore[arg-type]

    if active_bag_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot retire this bean: {active_bag_count} active "
                f"bag(s) still reference it. Retire them first."
            ),
        )

    db_bean.retired_at = datetime.now(timezone.utc)
    session.add(db_bean)
    session.commit()
    session.refresh(db_bean)
    return db_bean  # type: ignore[return-value]


# ======================================================================
# Nested Bag endpoints: /beans/{bean_id}/bags
# ======================================================================


# ------------------------------------------------------------------
# GET /beans/{bean_id}/bags  — list bags for a bean
# ------------------------------------------------------------------
@router.get(
    "/beans/{bean_id}/bags", response_model=PaginatedResponse[BagRead]
)
def list_bean_bags(
    bean_id: uuid.UUID,
    *,
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: SessionDep,
) -> PaginatedResponse[BagRead]:
    """List bags belonging to a specific bean.

    Parameters
    ----------
    bean_id : uuid.UUID
        The parent bean's primary key.
    include_retired : bool
        When ``True``, include soft-deleted bags.
    limit : int
        Maximum items per page (1--200).
    offset : int
        Number of items to skip.
    sort_by : str
        Column to sort by.
    sort_dir : str
        ``"asc"`` or ``"desc"``.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PaginatedResponse[BagRead]
        Paginated response with ``items``, ``total``, ``limit``, ``offset``.
    """
    validate_sort(sort_by, sort_dir, BAG_SORTABLE)

    # Verify bean exists
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    stmt = select(Bag).where(Bag.bean_id == bean_id)
    count_stmt = (
        select(func.count()).select_from(Bag).where(Bag.bean_id == bean_id)
    )

    if not include_retired:
        stmt = stmt.where(Bag.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Bag.retired_at.is_(None))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Bag, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)

    stmt = stmt.offset(offset).limit(limit)
    items = session.exec(stmt).all()

    return PaginatedResponse(  # type: ignore[return-value]
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# POST /beans/{bean_id}/bags  — create bag
# ------------------------------------------------------------------
@router.post(
    "/beans/{bean_id}/bags", response_model=BagRead, status_code=201
)
def create_bag_for_bean(
    bean_id: uuid.UUID,
    payload: BagCreate,
    session: SessionDep,
) -> BagRead:
    """Create a new bag under the given bean.

    Parameters
    ----------
    bean_id : uuid.UUID
        The parent bean's primary key.
    payload : BagCreate
        Bag data.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BagRead
        The created bag.
    """
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    db_bag = Bag(
        bean_id=bean_id,
        roast_date=payload.roast_date,
        opened_at=payload.opened_at,
        weight=payload.weight,
        price=payload.price,
        is_preground=payload.is_preground,
        notes=payload.notes,
        bought_at=payload.bought_at,
        vendor_id=payload.vendor_id,
        frozen_at=payload.frozen_at,
        thawed_at=payload.thawed_at,
        storage_type_id=payload.storage_type_id,
        best_date=payload.best_date,
    )
    session.add(db_bag)
    session.commit()
    session.refresh(db_bag)
    return db_bag  # type: ignore[return-value]


# ======================================================================
# Top-level Bag endpoints: /bags
# ======================================================================


# ------------------------------------------------------------------
# GET /bags  — list all bags with filtering
# ------------------------------------------------------------------
@router.get("/bags", response_model=PaginatedResponse[BagRead])
def list_bags(
    *,
    bean_id: uuid.UUID | None = Query(None, description="Filter by bean"),
    is_preground: bool | None = Query(
        None, description="Filter by pre-ground status"
    ),
    opened_after: date | None = Query(
        None, description="Filter bags opened after this date"
    ),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: SessionDep,
) -> PaginatedResponse[BagRead]:
    """List all bags with optional filtering, pagination, and sorting.

    Parameters
    ----------
    bean_id : uuid.UUID | None
        Filter by parent bean.
    is_preground : bool | None
        Filter by pre-ground status.
    opened_after : date | None
        Only return bags opened after this date.
    include_retired : bool
        When ``True``, include soft-deleted bags.
    limit : int
        Maximum items per page (1--200).
    offset : int
        Number of items to skip.
    sort_by : str
        Column to sort by.
    sort_dir : str
        ``"asc"`` or ``"desc"``.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PaginatedResponse[BagRead]
        Paginated response with ``items``, ``total``, ``limit``, ``offset``.
    """
    validate_sort(sort_by, sort_dir, BAG_SORTABLE)

    stmt = select(Bag)
    count_stmt = select(func.count()).select_from(Bag)

    if not include_retired:
        stmt = stmt.where(Bag.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Bag.retired_at.is_(None))  # type: ignore[union-attr]

    if bean_id is not None:
        stmt = stmt.where(Bag.bean_id == bean_id)
        count_stmt = count_stmt.where(Bag.bean_id == bean_id)

    if is_preground is not None:
        stmt = stmt.where(Bag.is_preground == is_preground)
        count_stmt = count_stmt.where(Bag.is_preground == is_preground)

    if opened_after is not None:
        stmt = stmt.where(Bag.opened_at > opened_after)  # type: ignore[operator]
        count_stmt = count_stmt.where(Bag.opened_at > opened_after)  # type: ignore[operator]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Bag, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)

    stmt = stmt.offset(offset).limit(limit)
    items = session.exec(stmt).all()

    return PaginatedResponse(  # type: ignore[return-value]
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# GET /bags/{bag_id}  — detail
# ------------------------------------------------------------------
@router.get("/bags/{bag_id}", response_model=BagRead)
def get_bag(
    bag_id: uuid.UUID,
    session: SessionDep,
) -> BagRead:
    """Get a single bag by ID.

    Parameters
    ----------
    bag_id : uuid.UUID
        The bag's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BagRead
        The bag.
    """
    db_bag = session.get(Bag, bag_id)
    if db_bag is None:
        raise HTTPException(status_code=404, detail="Bag not found.")
    return db_bag  # type: ignore[return-value]


# ------------------------------------------------------------------
# PATCH /bags/{bag_id}  — partial update
# ------------------------------------------------------------------
@router.patch("/bags/{bag_id}", response_model=BagRead)
def update_bag(
    bag_id: uuid.UUID,
    payload: BagUpdate,
    session: SessionDep,
) -> BagRead:
    """Partially update a bag.

    Parameters
    ----------
    bag_id : uuid.UUID
        The bag's primary key.
    payload : BagUpdate
        Fields to update.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BagRead
        The updated bag.
    """
    db_bag = session.get(Bag, bag_id)
    if db_bag is None:
        raise HTTPException(status_code=404, detail="Bag not found.")

    update_data = payload.model_dump(exclude_unset=True)
    db_bag.sqlmodel_update(update_data)
    session.add(db_bag)
    session.commit()
    session.refresh(db_bag)
    return db_bag  # type: ignore[return-value]


# ------------------------------------------------------------------
# DELETE /bags/{bag_id}  — soft-delete
# ------------------------------------------------------------------
@router.delete("/bags/{bag_id}", response_model=BagRead)
def delete_bag(
    bag_id: uuid.UUID,
    session: SessionDep,
) -> BagRead:
    """Soft-delete a bag by setting ``retired_at``.

    Parameters
    ----------
    bag_id : uuid.UUID
        The bag's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    BagRead
        The soft-deleted bag.
    """
    db_bag = session.get(Bag, bag_id)
    if db_bag is None:
        raise HTTPException(status_code=404, detail="Bag not found.")

    # Block if active cuppings exist
    cupping_count: int = session.exec(
        select(func.count())
        .select_from(Cupping)
        .where(Cupping.bag_id == bag_id, Cupping.retired_at.is_(None))  # type: ignore[union-attr]
    ).one()  # type: ignore[arg-type]
    if cupping_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retire this bag: {cupping_count} active cupping(s).",
        )

    db_bag.retired_at = datetime.now(timezone.utc)
    session.add(db_bag)
    session.commit()
    session.refresh(db_bag)
    return db_bag  # type: ignore[return-value]
