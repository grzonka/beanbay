"""Generic CRUD router factory for lookup tables and concrete router instances."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.dependencies import SessionDep, validate_sort
from beanbay.models.bean import (
    Bean,
    BeanOriginLink,
    BeanProcessLink,
    BeanVarietyLink,
)
from beanbay.models.brew import Brew, BrewSetup, BrewTaste, BrewTasteFlavorTagLink
from beanbay.models.equipment import Brewer, BrewerStopModeLink
from beanbay.models.rating import BeanRating, BeanTaste, BeanTasteFlavorTagLink
from beanbay.models.tag import (
    BeanVariety,
    BrewMethod,
    FlavorTag,
    Origin,
    ProcessMethod,
    Roaster,
    StopMode,
    StorageType,
    Vendor,
)
from beanbay.schemas.common import PaginatedResponse
from beanbay.schemas.tag import (
    BeanVarietyCreate,
    BeanVarietyRead,
    BeanVarietyUpdate,
    BrewMethodCreate,
    BrewMethodRead,
    BrewMethodUpdate,
    FlavorTagCreate,
    FlavorTagRead,
    FlavorTagUpdate,
    OriginCreate,
    OriginRead,
    OriginUpdate,
    ProcessMethodCreate,
    ProcessMethodRead,
    ProcessMethodUpdate,
    RoasterCreate,
    RoasterRead,
    RoasterUpdate,
    StopModeCreate,
    StopModeRead,
    StopModeUpdate,
    StorageTypeCreate,
    StorageTypeRead,
    StorageTypeUpdate,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)

# Type alias for dependency-check callables used by the router factory.
# Each callable receives (session, item_id) and returns the count of active
# references that would prevent soft-deletion.
DependencyCheck = Callable[[Session, uuid.UUID], int]


# ---------------------------------------------------------------------------
# Reusable dependency-check helpers
# ---------------------------------------------------------------------------


def _fk_active_count(
    model: type, fk_col: str
) -> DependencyCheck:
    """Return a checker for a direct FK on a model that has ``retired_at``.

    Parameters
    ----------
    model : type
        The SQLModel class that holds the foreign key.
    fk_col : str
        Column name on *model* that references the lookup entity's PK.

    Returns
    -------
    DependencyCheck
        Callable ``(session, item_id) -> int``.
    """

    def _check(session: Session, item_id: uuid.UUID) -> int:
        return session.exec(  # type: ignore[return-value]
            select(func.count())
            .select_from(model)
            .where(
                getattr(model, fk_col) == item_id,
                model.retired_at.is_(None),  # type: ignore[union-attr]
            )
        ).one()

    return _check


def _m2m_active_count(
    link_model: type,
    link_fk_col: str,
    parent_model: type,
    link_parent_col: str,
) -> DependencyCheck:
    """Return a checker for an M2M link where the parent has ``retired_at``.

    Parameters
    ----------
    link_model : type
        The junction/link SQLModel table.
    link_fk_col : str
        Column on the link table that references the lookup entity's PK.
    parent_model : type
        The parent model on the other side of the M2M.
    link_parent_col : str
        Column on the link table that references the parent model's PK.

    Returns
    -------
    DependencyCheck
        Callable ``(session, item_id) -> int``.
    """

    def _check(session: Session, item_id: uuid.UUID) -> int:
        return session.exec(  # type: ignore[return-value]
            select(func.count())
            .select_from(link_model)
            .join(
                parent_model,
                getattr(link_model, link_parent_col) == parent_model.id,  # type: ignore[union-attr]
            )
            .where(
                getattr(link_model, link_fk_col) == item_id,
                parent_model.retired_at.is_(None),  # type: ignore[union-attr]
            )
        ).one()

    return _check


def _m2m_grandparent_active_count(
    link_model: type,
    link_fk_col: str,
    parent_model: type,
    link_parent_col: str,
    grandparent_model: type,
    parent_gp_col: str,
) -> DependencyCheck:
    """Return a checker for an M2M link through a parent without ``retired_at``.

    Used when the intermediate model (e.g. BrewTaste) has no ``retired_at``
    but its grandparent (e.g. Brew) does.

    Parameters
    ----------
    link_model : type
        The junction/link SQLModel table.
    link_fk_col : str
        Column on the link table referencing the lookup entity's PK.
    parent_model : type
        The intermediate model (no ``retired_at``).
    link_parent_col : str
        Column on the link table referencing the parent model's PK.
    grandparent_model : type
        The model with ``retired_at`` that owns the parent.
    parent_gp_col : str
        Column on the parent model referencing the grandparent's PK.

    Returns
    -------
    DependencyCheck
        Callable ``(session, item_id) -> int``.
    """

    def _check(session: Session, item_id: uuid.UUID) -> int:
        return session.exec(  # type: ignore[return-value]
            select(func.count())
            .select_from(link_model)
            .join(
                parent_model,
                getattr(link_model, link_parent_col) == parent_model.id,  # type: ignore[union-attr]
            )
            .join(
                grandparent_model,
                getattr(parent_model, parent_gp_col) == grandparent_model.id,  # type: ignore[union-attr]
            )
            .where(
                getattr(link_model, link_fk_col) == item_id,
                grandparent_model.retired_at.is_(None),  # type: ignore[union-attr]
            )
        ).one()

    return _check


def create_lookup_router(
    *,
    model_class: type,
    create_schema: type,
    update_schema: type,
    read_schema: type,
    prefix: str,
    tag: str,
    sortable_fields: list[str] | None = None,
    dependency_checks: list[tuple[str, DependencyCheck]] | None = None,
) -> APIRouter:
    """Build a generic CRUD router for a lookup table.

    Parameters
    ----------
    model_class : type
        The SQLModel table class.
    create_schema : type
        Pydantic schema for creation payloads.
    update_schema : type
        Pydantic schema for partial-update payloads.
    read_schema : type
        Pydantic schema for response serialisation.
    prefix : str
        URL prefix (e.g. ``"flavor-tags"``).
    tag : str
        OpenAPI tag for grouping endpoints.
    sortable_fields : list[str] | None
        Columns allowed in ``sort_by``. Defaults to ``["name", "created_at"]``.
    dependency_checks : list[tuple[str, DependencyCheck]] | None
        Pairs of ``(table_label, check_callable)`` evaluated before
        soft-delete.  Each callable receives ``(session, item_id)`` and
        returns the count of active references.  If any count is > 0 the
        endpoint returns **409 Conflict**.

    Returns
    -------
    APIRouter
        A fully configured FastAPI router.
    """
    if sortable_fields is None:
        sortable_fields = ["name", "created_at"]

    router = APIRouter(prefix=f"/{prefix}", tags=[tag])

    # ------------------------------------------------------------------
    # GET /  — list with filtering, pagination, sorting
    # ------------------------------------------------------------------
    @router.get("", response_model=PaginatedResponse[read_schema])
    def list_items(
        *,
        q: str | None = Query(None, description="Case-insensitive name search"),
        include_retired: bool = Query(False, description="Include soft-deleted items"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        sort_by: str = Query("name", description="Field to sort by"),
        sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
        session: SessionDep,
    ) -> PaginatedResponse:  # type: ignore[type-arg]
        """List lookup items with optional search, pagination, and sorting."""
        validate_sort(sort_by, sort_dir, sortable_fields)

        # Base query
        stmt = select(model_class)
        count_stmt = select(func.count()).select_from(model_class)

        # Filter retired
        if not include_retired:
            stmt = stmt.where(model_class.retired_at.is_(None))  # type: ignore[union-attr]
            count_stmt = count_stmt.where(model_class.retired_at.is_(None))  # type: ignore[union-attr]

        # Text search
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(model_class.name.ilike(pattern))  # type: ignore[union-attr]
            count_stmt = count_stmt.where(model_class.name.ilike(pattern))  # type: ignore[union-attr]

        # Total count
        total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

        # Sorting
        sort_column = getattr(model_class, sort_by)
        if sort_dir == "desc":
            sort_column = sort_column.desc()
        stmt = stmt.order_by(sort_column)

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        items = session.exec(stmt).all()

        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ------------------------------------------------------------------
    # POST /  — create
    # ------------------------------------------------------------------
    @router.post("", response_model=read_schema, status_code=201)
    def create_item(
        payload: create_schema,  # type: ignore[valid-type]
        session: SessionDep,
    ) -> Any:
        """Create a new lookup item."""
        # Check uniqueness
        existing = session.exec(
            select(model_class).where(model_class.name == payload.name)  # type: ignore[union-attr]
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A {tag} with name '{payload.name}' already exists.",
            )

        db_item = model_class.model_validate(payload)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item

    # ------------------------------------------------------------------
    # GET /{id}  — get by ID
    # ------------------------------------------------------------------
    @router.get("/{item_id}", response_model=read_schema)
    def get_item(
        item_id: uuid.UUID,
        session: SessionDep,
    ) -> Any:
        """Get a single lookup item by ID."""
        db_item = session.get(model_class, item_id)
        if db_item is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found.")
        return db_item

    # ------------------------------------------------------------------
    # PATCH /{id}  — partial update
    # ------------------------------------------------------------------
    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(
        item_id: uuid.UUID,
        payload: update_schema,  # type: ignore[valid-type]
        session: SessionDep,
    ) -> Any:
        """Partially update a lookup item."""
        db_item = session.get(model_class, item_id)
        if db_item is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found.")

        update_data = payload.model_dump(exclude_unset=True)

        # If name is being updated, check uniqueness
        if "name" in update_data:
            existing = session.exec(
                select(model_class).where(
                    model_class.name == update_data["name"],  # type: ignore[union-attr]
                    model_class.id != item_id,  # type: ignore[union-attr]
                )
            ).first()
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"A {tag} with name '{update_data['name']}' already exists.",
                )

        db_item.sqlmodel_update(update_data)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item

    # ------------------------------------------------------------------
    # DELETE /{id}  — soft-delete
    # ------------------------------------------------------------------
    @router.delete("/{item_id}", response_model=read_schema)
    def delete_item(
        item_id: uuid.UUID,
        session: SessionDep,
    ) -> Any:
        """Soft-delete a lookup item by setting ``retired_at``."""
        db_item = session.get(model_class, item_id)
        if db_item is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found.")

        # Check dependent models for active references
        if dependency_checks:
            for table_label, check_fn in dependency_checks:
                count = check_fn(session, item_id)
                if count > 0:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Cannot retire this {tag}: "
                            f"{count} active reference(s) in "
                            f"{table_label}."
                        ),
                    )

        db_item.retired_at = datetime.now(timezone.utc)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item

    return router


# ======================================================================
# Concrete router instances
# ======================================================================

flavor_tag_router = create_lookup_router(
    model_class=FlavorTag,
    create_schema=FlavorTagCreate,
    update_schema=FlavorTagUpdate,
    read_schema=FlavorTagRead,
    prefix="flavor-tags",
    tag="Flavor Tags",
    dependency_checks=[
        (
            "brew_taste_flavor_tags",
            _m2m_grandparent_active_count(
                BrewTasteFlavorTagLink,
                "flavor_tag_id",
                BrewTaste,
                "brew_taste_id",
                Brew,
                "brew_id",
            ),
        ),
        (
            "bean_taste_flavor_tags",
            _m2m_grandparent_active_count(
                BeanTasteFlavorTagLink,
                "flavor_tag_id",
                BeanTaste,
                "bean_taste_id",
                BeanRating,
                "bean_rating_id",
            ),
        ),
    ],
)

origin_router = create_lookup_router(
    model_class=Origin,
    create_schema=OriginCreate,
    update_schema=OriginUpdate,
    read_schema=OriginRead,
    prefix="origins",
    tag="Origins",
    sortable_fields=["name", "country", "created_at"],
    dependency_checks=[
        (
            "beans",
            _m2m_active_count(
                BeanOriginLink, "origin_id", Bean, "bean_id"
            ),
        ),
    ],
)

roaster_router = create_lookup_router(
    model_class=Roaster,
    create_schema=RoasterCreate,
    update_schema=RoasterUpdate,
    read_schema=RoasterRead,
    prefix="roasters",
    tag="Roasters",
    dependency_checks=[
        ("beans", _fk_active_count(Bean, "roaster_id")),
    ],
)

process_method_router = create_lookup_router(
    model_class=ProcessMethod,
    create_schema=ProcessMethodCreate,
    update_schema=ProcessMethodUpdate,
    read_schema=ProcessMethodRead,
    prefix="process-methods",
    tag="Process Methods",
    dependency_checks=[
        (
            "beans",
            _m2m_active_count(
                BeanProcessLink, "process_id", Bean, "bean_id"
            ),
        ),
    ],
)

bean_variety_router = create_lookup_router(
    model_class=BeanVariety,
    create_schema=BeanVarietyCreate,
    update_schema=BeanVarietyUpdate,
    read_schema=BeanVarietyRead,
    prefix="bean-varieties",
    tag="Bean Varieties",
    dependency_checks=[
        (
            "beans",
            _m2m_active_count(
                BeanVarietyLink, "variety_id", Bean, "bean_id"
            ),
        ),
    ],
)

brew_method_router = create_lookup_router(
    model_class=BrewMethod,
    create_schema=BrewMethodCreate,
    update_schema=BrewMethodUpdate,
    read_schema=BrewMethodRead,
    prefix="brew-methods",
    tag="Brew Methods",
    dependency_checks=[
        ("brew_setups", _fk_active_count(BrewSetup, "brew_method_id")),
    ],
)

stop_mode_router = create_lookup_router(
    model_class=StopMode,
    create_schema=StopModeCreate,
    update_schema=StopModeUpdate,
    read_schema=StopModeRead,
    prefix="stop-modes",
    tag="Stop Modes",
    dependency_checks=[
        (
            "brewers",
            _m2m_active_count(
                BrewerStopModeLink, "stop_mode_id", Brewer, "brewer_id"
            ),
        ),
        ("brews", _fk_active_count(Brew, "stop_mode_id")),
    ],
)

vendor_router = create_lookup_router(
    model_class=Vendor,
    create_schema=VendorCreate,
    update_schema=VendorUpdate,
    read_schema=VendorRead,
    prefix="vendors",
    tag="Vendors",
    sortable_fields=["name", "location", "created_at"],
    dependency_checks=[],  # Will add bag check in later task
)

storage_type_router = create_lookup_router(
    model_class=StorageType,
    create_schema=StorageTypeCreate,
    update_schema=StorageTypeUpdate,
    read_schema=StorageTypeRead,
    prefix="storage-types",
    tag="Storage Types",
    dependency_checks=[],  # Will add bag check in later task
)
