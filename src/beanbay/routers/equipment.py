"""CRUD routers for equipment models.

Sub-routers for Grinder, Brewer, Paper, and Water, each with full CRUD,
pagination, sorting, include_retired filtering, and soft-delete.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.database import get_session
from beanbay.models.equipment import (
    Brewer,
    BrewerMethodLink,
    BrewerStopModeLink,
    Grinder,
    Paper,
    Water,
    WaterMineral,
)
from beanbay.models.tag import BrewMethod, StopMode
from beanbay.schemas.common import PaginatedResponse
from beanbay.schemas.equipment import (
    BrewerCreate,
    BrewerRead,
    BrewerUpdate,
    GrinderCreate,
    GrinderRead,
    GrinderUpdate,
    PaperCreate,
    PaperRead,
    PaperUpdate,
    WaterCreate,
    WaterRead,
    WaterUpdate,
)

router = APIRouter(tags=["Equipment"])


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


def _rings_to_json(rings: list[Any] | None) -> str | None:
    """Serialize a list of RingConfig objects to JSON string.

    Parameters
    ----------
    rings : list[Any] | None
        Ring config objects with ``min``, ``max``, ``step`` attributes.

    Returns
    -------
    str | None
        JSON string of ``[[min, max, step], ...]`` or ``None``.
    """
    if not rings:
        return None
    return json.dumps([[r.min, r.max, r.step] for r in rings])


# ======================================================================
# Grinder CRUD
# ======================================================================

GRINDER_SORT_FIELDS = ["name", "created_at", "updated_at"]


@router.get("/grinders", response_model=PaginatedResponse[GrinderRead])
def list_grinders(
    q: str | None = Query(None, description="Case-insensitive name search"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List grinders with optional search, pagination, and sorting."""
    _validate_sort(sort_by, sort_dir, GRINDER_SORT_FIELDS)

    stmt = select(Grinder)
    count_stmt = select(func.count()).select_from(Grinder)

    if not include_retired:
        stmt = stmt.where(Grinder.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Grinder.retired_at.is_(None))  # type: ignore[union-attr]
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Grinder.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Grinder.name.ilike(pattern))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Grinder, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    items = session.exec(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/grinders", response_model=GrinderRead, status_code=201)
def create_grinder(
    payload: GrinderCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new grinder."""
    existing = session.exec(
        select(Grinder).where(Grinder.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A grinder with name '{payload.name}' already exists.",
        )

    ring_json = _rings_to_json(payload.rings)
    db_grinder = Grinder(
        name=payload.name,
        dial_type=payload.dial_type,
        display_format=payload.display_format,
        ring_sizes_json=ring_json,
    )
    session.add(db_grinder)
    session.commit()
    session.refresh(db_grinder)
    return db_grinder


@router.get("/grinders/{grinder_id}", response_model=GrinderRead)
def get_grinder(
    grinder_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single grinder by ID."""
    db_grinder = session.get(Grinder, grinder_id)
    if db_grinder is None:
        raise HTTPException(status_code=404, detail="Grinder not found.")
    return db_grinder


@router.patch("/grinders/{grinder_id}", response_model=GrinderRead)
def update_grinder(
    grinder_id: uuid.UUID,
    payload: GrinderUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update a grinder."""
    db_grinder = session.get(Grinder, grinder_id)
    if db_grinder is None:
        raise HTTPException(status_code=404, detail="Grinder not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Check uniqueness if name changes
    if "name" in update_data:
        existing = session.exec(
            select(Grinder).where(
                Grinder.name == update_data["name"],
                Grinder.id != grinder_id,  # type: ignore[union-attr]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A grinder with name '{update_data['name']}' already exists.",
            )

    # Handle rings separately
    if "rings" in update_data:
        rings = update_data.pop("rings")
        if rings is not None:
            db_grinder.ring_sizes_json = json.dumps(
                [[r["min"], r["max"], r["step"]] for r in rings]
            )
        else:
            db_grinder.ring_sizes_json = None

    db_grinder.sqlmodel_update(update_data)
    session.add(db_grinder)
    session.commit()
    session.refresh(db_grinder)
    return db_grinder


@router.delete("/grinders/{grinder_id}", response_model=GrinderRead)
def delete_grinder(
    grinder_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a grinder."""
    db_grinder = session.get(Grinder, grinder_id)
    if db_grinder is None:
        raise HTTPException(status_code=404, detail="Grinder not found.")

    db_grinder.retired_at = datetime.now(timezone.utc)
    session.add(db_grinder)
    session.commit()
    session.refresh(db_grinder)
    return db_grinder


# ======================================================================
# Brewer CRUD
# ======================================================================

BREWER_SORT_FIELDS = ["name", "created_at", "updated_at"]


def _set_brewer_m2m(
    session: Session,
    brewer: Brewer,
    method_ids: list[uuid.UUID] | None,
    stop_mode_ids: list[uuid.UUID] | None,
) -> None:
    """Set M2M relationships on a brewer.

    Parameters
    ----------
    session : Session
        Database session.
    brewer : Brewer
        The brewer to update.
    method_ids : list[uuid.UUID] | None
        Brew method IDs to link. ``None`` means don't touch.
    stop_mode_ids : list[uuid.UUID] | None
        Stop mode IDs to link. ``None`` means don't touch.
    """
    if method_ids is not None:
        # Delete existing links
        existing_links = session.exec(
            select(BrewerMethodLink).where(
                BrewerMethodLink.brewer_id == brewer.id
            )
        ).all()
        for link in existing_links:
            session.delete(link)
        session.flush()

        # Add new links
        for mid in method_ids:
            method = session.get(BrewMethod, mid)
            if method is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"BrewMethod with id '{mid}' not found.",
                )
            session.add(BrewerMethodLink(brewer_id=brewer.id, method_id=mid))

    if stop_mode_ids is not None:
        # Delete existing links
        existing_links = session.exec(
            select(BrewerStopModeLink).where(
                BrewerStopModeLink.brewer_id == brewer.id
            )
        ).all()
        for link in existing_links:
            session.delete(link)
        session.flush()

        # Add new links
        for sid in stop_mode_ids:
            stop_mode = session.get(StopMode, sid)
            if stop_mode is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"StopMode with id '{sid}' not found.",
                )
            session.add(BrewerStopModeLink(brewer_id=brewer.id, stop_mode_id=sid))


@router.get("/brewers", response_model=PaginatedResponse[BrewerRead])
def list_brewers(
    q: str | None = Query(None, description="Case-insensitive name search"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List brewers with optional search, pagination, and sorting."""
    _validate_sort(sort_by, sort_dir, BREWER_SORT_FIELDS)

    stmt = select(Brewer)
    count_stmt = select(func.count()).select_from(Brewer)

    if not include_retired:
        stmt = stmt.where(Brewer.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Brewer.retired_at.is_(None))  # type: ignore[union-attr]
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Brewer.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Brewer.name.ilike(pattern))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Brewer, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    items = session.exec(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/brewers", response_model=BrewerRead, status_code=201)
def create_brewer(
    payload: BrewerCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new brewer with optional M2M methods and stop modes."""
    existing = session.exec(
        select(Brewer).where(Brewer.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A brewer with name '{payload.name}' already exists.",
        )

    # Build the brewer from payload, excluding M2M IDs
    db_brewer = Brewer(
        name=payload.name,
        temp_control_type=payload.temp_control_type,
        temp_min=payload.temp_min,
        temp_max=payload.temp_max,
        temp_step=payload.temp_step,
        preinfusion_type=payload.preinfusion_type,
        preinfusion_max_time=payload.preinfusion_max_time,
        pressure_control_type=payload.pressure_control_type,
        pressure_min=payload.pressure_min,
        pressure_max=payload.pressure_max,
        flow_control_type=payload.flow_control_type,
        saturation_flow_rate=payload.saturation_flow_rate,
        has_bloom=payload.has_bloom,
    )
    session.add(db_brewer)
    session.flush()  # Get the ID

    _set_brewer_m2m(session, db_brewer, payload.method_ids, payload.stop_mode_ids)

    session.commit()
    session.refresh(db_brewer)
    return db_brewer


@router.get("/brewers/{brewer_id}", response_model=BrewerRead)
def get_brewer(
    brewer_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single brewer by ID."""
    db_brewer = session.get(Brewer, brewer_id)
    if db_brewer is None:
        raise HTTPException(status_code=404, detail="Brewer not found.")
    return db_brewer


@router.patch("/brewers/{brewer_id}", response_model=BrewerRead)
def update_brewer(
    brewer_id: uuid.UUID,
    payload: BrewerUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update a brewer, optionally replacing M2M relations."""
    db_brewer = session.get(Brewer, brewer_id)
    if db_brewer is None:
        raise HTTPException(status_code=404, detail="Brewer not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Check uniqueness if name changes
    if "name" in update_data:
        existing = session.exec(
            select(Brewer).where(
                Brewer.name == update_data["name"],
                Brewer.id != brewer_id,  # type: ignore[union-attr]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A brewer with name '{update_data['name']}' already exists.",
            )

    # Extract M2M IDs (don't pass them to sqlmodel_update)
    method_ids = update_data.pop("method_ids", None)
    stop_mode_ids = update_data.pop("stop_mode_ids", None)

    db_brewer.sqlmodel_update(update_data)
    session.add(db_brewer)
    session.flush()

    # Handle M2M only if provided (exclude_unset semantics)
    _set_brewer_m2m(
        session,
        db_brewer,
        method_ids if "method_ids" in payload.model_dump(exclude_unset=True) else None,
        stop_mode_ids
        if "stop_mode_ids" in payload.model_dump(exclude_unset=True)
        else None,
    )

    session.commit()
    session.refresh(db_brewer)
    return db_brewer


@router.delete("/brewers/{brewer_id}", response_model=BrewerRead)
def delete_brewer(
    brewer_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a brewer."""
    db_brewer = session.get(Brewer, brewer_id)
    if db_brewer is None:
        raise HTTPException(status_code=404, detail="Brewer not found.")

    db_brewer.retired_at = datetime.now(timezone.utc)
    session.add(db_brewer)
    session.commit()
    session.refresh(db_brewer)
    return db_brewer


# ======================================================================
# Paper CRUD
# ======================================================================

PAPER_SORT_FIELDS = ["name", "created_at", "updated_at"]


@router.get("/papers", response_model=PaginatedResponse[PaperRead])
def list_papers(
    q: str | None = Query(None, description="Case-insensitive name search"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List papers with optional search, pagination, and sorting."""
    _validate_sort(sort_by, sort_dir, PAPER_SORT_FIELDS)

    stmt = select(Paper)
    count_stmt = select(func.count()).select_from(Paper)

    if not include_retired:
        stmt = stmt.where(Paper.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Paper.retired_at.is_(None))  # type: ignore[union-attr]
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Paper.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Paper.name.ilike(pattern))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Paper, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    items = session.exec(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/papers", response_model=PaperRead, status_code=201)
def create_paper(
    payload: PaperCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new paper."""
    existing = session.exec(
        select(Paper).where(Paper.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A paper with name '{payload.name}' already exists.",
        )

    db_paper = Paper.model_validate(payload)
    session.add(db_paper)
    session.commit()
    session.refresh(db_paper)
    return db_paper


@router.get("/papers/{paper_id}", response_model=PaperRead)
def get_paper(
    paper_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single paper by ID."""
    db_paper = session.get(Paper, paper_id)
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return db_paper


@router.patch("/papers/{paper_id}", response_model=PaperRead)
def update_paper(
    paper_id: uuid.UUID,
    payload: PaperUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update a paper."""
    db_paper = session.get(Paper, paper_id)
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = session.exec(
            select(Paper).where(
                Paper.name == update_data["name"],
                Paper.id != paper_id,  # type: ignore[union-attr]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A paper with name '{update_data['name']}' already exists.",
            )

    db_paper.sqlmodel_update(update_data)
    session.add(db_paper)
    session.commit()
    session.refresh(db_paper)
    return db_paper


@router.delete("/papers/{paper_id}", response_model=PaperRead)
def delete_paper(
    paper_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a paper."""
    db_paper = session.get(Paper, paper_id)
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")

    db_paper.retired_at = datetime.now(timezone.utc)
    session.add(db_paper)
    session.commit()
    session.refresh(db_paper)
    return db_paper


# ======================================================================
# Water CRUD
# ======================================================================

WATER_SORT_FIELDS = ["name", "created_at", "updated_at"]


def _set_water_minerals(
    session: Session,
    water: Water,
    minerals: list[Any],
) -> None:
    """Delete all existing minerals and reinsert from the given list.

    Parameters
    ----------
    session : Session
        Database session.
    water : Water
        The parent water.
    minerals : list[Any]
        Mineral create schemas to insert.
    """
    # Delete existing
    existing = session.exec(
        select(WaterMineral).where(WaterMineral.water_id == water.id)
    ).all()
    for m in existing:
        session.delete(m)
    session.flush()

    # Insert new
    for m in minerals:
        db_mineral = WaterMineral(
            water_id=water.id,
            mineral_name=m.mineral_name if hasattr(m, "mineral_name") else m["mineral_name"],
            ppm=m.ppm if hasattr(m, "ppm") else m["ppm"],
        )
        session.add(db_mineral)


@router.get("/waters", response_model=PaginatedResponse[WaterRead])
def list_waters(
    q: str | None = Query(None, description="Case-insensitive name search"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List waters with optional search, pagination, and sorting."""
    _validate_sort(sort_by, sort_dir, WATER_SORT_FIELDS)

    stmt = select(Water)
    count_stmt = select(func.count()).select_from(Water)

    if not include_retired:
        stmt = stmt.where(Water.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Water.retired_at.is_(None))  # type: ignore[union-attr]
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Water.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Water.name.ilike(pattern))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Water, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    items = session.exec(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/waters", response_model=WaterRead, status_code=201)
def create_water(
    payload: WaterCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new water with optional inline minerals."""
    existing = session.exec(
        select(Water).where(Water.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A water with name '{payload.name}' already exists.",
        )

    db_water = Water(name=payload.name, notes=payload.notes)
    session.add(db_water)
    session.flush()

    if payload.minerals:
        _set_water_minerals(session, db_water, payload.minerals)

    session.commit()
    session.refresh(db_water)
    return db_water


@router.get("/waters/{water_id}", response_model=WaterRead)
def get_water(
    water_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single water by ID."""
    db_water = session.get(Water, water_id)
    if db_water is None:
        raise HTTPException(status_code=404, detail="Water not found.")
    return db_water


@router.patch("/waters/{water_id}", response_model=WaterRead)
def update_water(
    water_id: uuid.UUID,
    payload: WaterUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update a water, optionally replacing minerals."""
    db_water = session.get(Water, water_id)
    if db_water is None:
        raise HTTPException(status_code=404, detail="Water not found.")

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = session.exec(
            select(Water).where(
                Water.name == update_data["name"],
                Water.id != water_id,  # type: ignore[union-attr]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A water with name '{update_data['name']}' already exists.",
            )

    # Handle minerals: delete-and-reinsert only if minerals was sent
    minerals_data = update_data.pop("minerals", None)

    # Apply scalar updates
    db_water.sqlmodel_update(update_data)
    session.add(db_water)
    session.flush()

    if "minerals" in payload.model_dump(exclude_unset=True):
        # minerals was explicitly sent — replace all
        _set_water_minerals(session, db_water, payload.minerals or [])

    session.commit()
    session.refresh(db_water)
    return db_water


@router.delete("/waters/{water_id}", response_model=WaterRead)
def delete_water(
    water_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a water."""
    db_water = session.get(Water, water_id)
    if db_water is None:
        raise HTTPException(status_code=404, detail="Water not found.")

    db_water.retired_at = datetime.now(timezone.utc)
    session.add(db_water)
    session.commit()
    session.refresh(db_water)
    return db_water
