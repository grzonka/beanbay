"""Generic CRUD router factory for lookup tables and concrete router instances."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.database import get_session
from beanbay.models.tag import (
    BeanVariety,
    BrewMethod,
    FlavorTag,
    Origin,
    ProcessMethod,
    Roaster,
    StopMode,
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
)


def create_lookup_router(
    *,
    model_class: type,
    create_schema: type,
    update_schema: type,
    read_schema: type,
    prefix: str,
    tag: str,
    sortable_fields: list[str] | None = None,
    dependent_models: list[tuple[Any, str]] | None = None,
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
    dependent_models : list[tuple[Any, str]] | None
        Pairs of ``(DependentModel, fk_column_name)`` checked before
        hard-delete.  If any active references exist the endpoint returns
        409 Conflict.

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
        q: str | None = Query(None, description="Case-insensitive name search"),
        include_retired: bool = Query(False, description="Include soft-deleted items"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        sort_by: str = Query("name", description="Field to sort by"),
        sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        """List lookup items with optional search, pagination, and sorting."""
        if sort_by not in sortable_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sort_by field '{sort_by}'. Allowed: {sortable_fields}",
            )
        if sort_dir not in ("asc", "desc"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sort_dir '{sort_dir}'. Must be 'asc' or 'desc'.",
            )

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

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # POST /  — create
    # ------------------------------------------------------------------
    @router.post("", response_model=read_schema, status_code=201)
    def create_item(
        payload: create_schema,  # type: ignore[valid-type]
        session: Session = Depends(get_session),
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
        session: Session = Depends(get_session),
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
        session: Session = Depends(get_session),
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
        session: Session = Depends(get_session),
    ) -> Any:
        """Soft-delete a lookup item by setting ``retired_at``."""
        db_item = session.get(model_class, item_id)
        if db_item is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found.")

        # Check dependent models for active references
        if dependent_models:
            for dep_model, fk_col in dependent_models:
                count = session.exec(
                    select(func.count()).select_from(dep_model).where(
                        getattr(dep_model, fk_col) == item_id
                    )
                ).one()
                if count > 0:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Cannot retire this {tag}: "
                            f"{count} active reference(s) in "
                            f"{dep_model.__tablename__}."
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
)

origin_router = create_lookup_router(
    model_class=Origin,
    create_schema=OriginCreate,
    update_schema=OriginUpdate,
    read_schema=OriginRead,
    prefix="origins",
    tag="Origins",
)

roaster_router = create_lookup_router(
    model_class=Roaster,
    create_schema=RoasterCreate,
    update_schema=RoasterUpdate,
    read_schema=RoasterRead,
    prefix="roasters",
    tag="Roasters",
)

process_method_router = create_lookup_router(
    model_class=ProcessMethod,
    create_schema=ProcessMethodCreate,
    update_schema=ProcessMethodUpdate,
    read_schema=ProcessMethodRead,
    prefix="process-methods",
    tag="Process Methods",
)

bean_variety_router = create_lookup_router(
    model_class=BeanVariety,
    create_schema=BeanVarietyCreate,
    update_schema=BeanVarietyUpdate,
    read_schema=BeanVarietyRead,
    prefix="bean-varieties",
    tag="Bean Varieties",
)

brew_method_router = create_lookup_router(
    model_class=BrewMethod,
    create_schema=BrewMethodCreate,
    update_schema=BrewMethodUpdate,
    read_schema=BrewMethodRead,
    prefix="brew-methods",
    tag="Brew Methods",
)

stop_mode_router = create_lookup_router(
    model_class=StopMode,
    create_schema=StopModeCreate,
    update_schema=StopModeUpdate,
    read_schema=StopModeRead,
    prefix="stop-modes",
    tag="Stop Modes",
)
