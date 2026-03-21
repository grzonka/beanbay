"""CRUD router for BrewSetup.

Endpoints for listing, creating, reading, updating, and retiring brew setups
with filtering by brew_method_id, grinder_id, brewer_id, and has_grinder.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.database import get_session
from beanbay.models.brew import BrewSetup
from beanbay.models.equipment import Brewer, Grinder, Paper, Water
from beanbay.models.tag import BrewMethod
from beanbay.schemas.brew import BrewSetupCreate, BrewSetupRead, BrewSetupUpdate
from beanbay.schemas.common import PaginatedResponse

router = APIRouter(tags=["Brew Setups"])

BREW_SETUP_SORT_FIELDS = ["name", "created_at"]


# ======================================================================
# Helpers
# ======================================================================


def _validate_sort(sort_by: str, sort_dir: str, allowed: list[str]) -> None:
    """Validate sort_by and sort_dir parameters.

    Parameters
    ----------
    sort_by : str
        Field to sort by.
    sort_dir : str
        Sort direction: ``"asc"`` or ``"desc"``.
    allowed : list[str]
        Allowed sort fields.

    Raises
    ------
    HTTPException
        If sort_by or sort_dir is invalid.
    """
    if sort_by not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_by field '{sort_by}'. Allowed: {allowed}",
        )
    if sort_dir not in ("asc", "desc"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_dir '{sort_dir}'. Must be 'asc' or 'desc'.",
        )


def _validate_fk_exists(
    session: Session,
    model: type,
    pk: uuid.UUID,
    label: str,
) -> None:
    """Ensure a foreign key target exists.

    Parameters
    ----------
    session : Session
        Database session.
    model : type
        The SQLModel class to look up.
    pk : uuid.UUID
        Primary key to check.
    label : str
        Human-readable label for error messages.

    Raises
    ------
    HTTPException
        If the referenced entity is not found.
    """
    if session.get(model, pk) is None:
        raise HTTPException(
            status_code=404,
            detail=f"{label} with id '{pk}' not found.",
        )


def _validate_brew_setup_fks(
    session: Session,
    brew_method_id: uuid.UUID | None,
    grinder_id: uuid.UUID | None,
    brewer_id: uuid.UUID | None,
    paper_id: uuid.UUID | None,
    water_id: uuid.UUID | None,
) -> None:
    """Validate all foreign keys for a brew setup.

    Parameters
    ----------
    session : Session
        Database session.
    brew_method_id : uuid.UUID | None
        Brew method FK to validate.
    grinder_id : uuid.UUID | None
        Grinder FK to validate.
    brewer_id : uuid.UUID | None
        Brewer FK to validate.
    paper_id : uuid.UUID | None
        Paper FK to validate.
    water_id : uuid.UUID | None
        Water FK to validate.
    """
    if brew_method_id is not None:
        _validate_fk_exists(session, BrewMethod, brew_method_id, "BrewMethod")
    if grinder_id is not None:
        _validate_fk_exists(session, Grinder, grinder_id, "Grinder")
    if brewer_id is not None:
        _validate_fk_exists(session, Brewer, brewer_id, "Brewer")
    if paper_id is not None:
        _validate_fk_exists(session, Paper, paper_id, "Paper")
    if water_id is not None:
        _validate_fk_exists(session, Water, water_id, "Water")


# ======================================================================
# Brew Setup CRUD
# ======================================================================


@router.get("/brew-setups", response_model=PaginatedResponse[BrewSetupRead])
def list_brew_setups(
    brew_method_id: uuid.UUID | None = Query(None, description="Filter by brew method"),
    grinder_id: uuid.UUID | None = Query(None, description="Filter by grinder"),
    brewer_id: uuid.UUID | None = Query(None, description="Filter by brewer"),
    has_grinder: bool | None = Query(None, description="Filter by grinder presence"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List brew setups with filtering, pagination, and sorting."""
    _validate_sort(sort_by, sort_dir, BREW_SETUP_SORT_FIELDS)

    stmt = select(BrewSetup)
    count_stmt = select(func.count()).select_from(BrewSetup)

    if not include_retired:
        stmt = stmt.where(BrewSetup.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(BrewSetup.retired_at.is_(None))  # type: ignore[union-attr]

    if brew_method_id is not None:
        stmt = stmt.where(BrewSetup.brew_method_id == brew_method_id)
        count_stmt = count_stmt.where(BrewSetup.brew_method_id == brew_method_id)

    if grinder_id is not None:
        stmt = stmt.where(BrewSetup.grinder_id == grinder_id)
        count_stmt = count_stmt.where(BrewSetup.grinder_id == grinder_id)

    if brewer_id is not None:
        stmt = stmt.where(BrewSetup.brewer_id == brewer_id)
        count_stmt = count_stmt.where(BrewSetup.brewer_id == brewer_id)

    if has_grinder is True:
        stmt = stmt.where(BrewSetup.grinder_id.is_not(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(BrewSetup.grinder_id.is_not(None))  # type: ignore[union-attr]
    elif has_grinder is False:
        stmt = stmt.where(BrewSetup.grinder_id.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(BrewSetup.grinder_id.is_(None))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(BrewSetup, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    items = session.exec(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/brew-setups", response_model=BrewSetupRead, status_code=201)
def create_brew_setup(
    payload: BrewSetupCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new brew setup."""
    _validate_brew_setup_fks(
        session,
        payload.brew_method_id,
        payload.grinder_id,
        payload.brewer_id,
        payload.paper_id,
        payload.water_id,
    )

    db_setup = BrewSetup(
        name=payload.name,
        brew_method_id=payload.brew_method_id,
        grinder_id=payload.grinder_id,
        brewer_id=payload.brewer_id,
        paper_id=payload.paper_id,
        water_id=payload.water_id,
    )
    session.add(db_setup)
    session.commit()
    session.refresh(db_setup)
    return db_setup


@router.get("/brew-setups/{setup_id}", response_model=BrewSetupRead)
def get_brew_setup(
    setup_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single brew setup by ID."""
    db_setup = session.get(BrewSetup, setup_id)
    if db_setup is None:
        raise HTTPException(status_code=404, detail="BrewSetup not found.")
    return db_setup


@router.patch("/brew-setups/{setup_id}", response_model=BrewSetupRead)
def update_brew_setup(
    setup_id: uuid.UUID,
    payload: BrewSetupUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update a brew setup."""
    db_setup = session.get(BrewSetup, setup_id)
    if db_setup is None:
        raise HTTPException(status_code=404, detail="BrewSetup not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Validate any FK changes
    _validate_brew_setup_fks(
        session,
        update_data.get("brew_method_id"),
        update_data.get("grinder_id"),
        update_data.get("brewer_id"),
        update_data.get("paper_id"),
        update_data.get("water_id"),
    )

    db_setup.sqlmodel_update(update_data)
    session.add(db_setup)
    session.commit()
    session.refresh(db_setup)
    return db_setup


@router.delete("/brew-setups/{setup_id}", response_model=BrewSetupRead)
def delete_brew_setup(
    setup_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a brew setup."""
    db_setup = session.get(BrewSetup, setup_id)
    if db_setup is None:
        raise HTTPException(status_code=404, detail="BrewSetup not found.")

    db_setup.retired_at = datetime.now(timezone.utc)
    session.add(db_setup)
    session.commit()
    session.refresh(db_setup)
    return db_setup
