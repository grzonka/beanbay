"""CRUD router for Brew and BrewTaste.

Endpoints for listing, creating, reading, updating, and retiring brews,
plus sub-resource CRUD for taste (PUT/PATCH/DELETE).
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select

from beanbay.dependencies import SessionDep, validate_sort
from beanbay.models.bean import Bag, Bean
from beanbay.models.brew import Brew, BrewSetup, BrewTaste, BrewTasteFlavorTagLink
from beanbay.models.equipment import Grinder
from beanbay.models.person import Person
from beanbay.models.tag import BrewMethod, FlavorTag, StopMode
from beanbay.schemas.brew import (
    BrewCreate,
    BrewListRead,
    BrewRead,
    BrewTasteCreate,
    BrewTasteRead,
    BrewTasteUpdate,
    BrewUpdate,
)
from beanbay.schemas.common import PaginatedResponse
from beanbay.services.campaign import ensure_campaign
from beanbay.utils.grinder_display import from_display, to_display

router = APIRouter(tags=["Brews"])

BREW_SORT_FIELDS = [
    "brewed_at", "created_at", "dose", "grind_setting",
    "temperature", "yield_amount", "pressure", "flow_rate",
    "total_time", "pre_infusion_time",
    "score", "bean_name", "brew_method_name", "person_name",
    "grind_setting_display",
]


def _get_ring_sizes(grinder: Grinder | None) -> list[tuple[float, float, float | None]] | None:
    """Parse ring_sizes_json from a grinder.

    Parameters
    ----------
    grinder : Grinder | None
        The grinder model instance.

    Returns
    -------
    list[tuple[float, float, float | None]] | None
        Parsed ring sizes or ``None``.
    """
    if grinder is None or grinder.ring_sizes_json is None:
        return None
    raw = json.loads(grinder.ring_sizes_json)
    return [(r[0], r[1], r[2] if len(r) > 2 else None) for r in raw]


def _compute_grind_display(
    grind_setting: float | None,
    brew_setup: BrewSetup | None,
) -> str | None:
    """Compute grind_setting_display from a canonical float.

    Parameters
    ----------
    grind_setting : float | None
        The canonical numeric grind setting.
    brew_setup : BrewSetup
        The brew setup (used to look up grinder).

    Returns
    -------
    str | None
        The display string, or ``None`` if not computable.
    """
    if grind_setting is None or brew_setup is None:
        return None
    grinder = brew_setup.grinder
    ring_sizes = _get_ring_sizes(grinder)
    if ring_sizes is None:
        return str(grind_setting)
    return to_display(grind_setting, ring_sizes)


def _resolve_grind_setting(
    payload_grind_setting: float | None,
    payload_display: str | None,
    brew_setup: BrewSetup | None,
) -> float | None:
    """Resolve the canonical grind setting from payload inputs.

    If ``grind_setting_display`` is provided, it takes precedence and is
    converted to a float. Otherwise the raw ``grind_setting`` float is used.

    Parameters
    ----------
    payload_grind_setting : float | None
        The raw float from the request.
    payload_display : str | None
        The display string from the request.
    brew_setup : BrewSetup
        The brew setup (used to look up grinder ring config).

    Returns
    -------
    float | None
        The canonical grind setting.
    """
    if payload_display is not None:
        grinder = brew_setup.grinder if brew_setup else None
        ring_sizes = _get_ring_sizes(grinder)
        if ring_sizes is None:
            return float(payload_display)
        return from_display(payload_display, ring_sizes)
    return payload_grind_setting


def _set_taste_tags(
    session: SessionDep,
    taste: BrewTaste,
    flavor_tag_ids: list[uuid.UUID],
) -> None:
    """Set M2M flavor tags on a taste, replacing existing links.

    Parameters
    ----------
    session : SessionDep
        Database session.
    taste : BrewTaste
        The taste to update.
    flavor_tag_ids : list[uuid.UUID]
        Flavor tag IDs to link.

    Raises
    ------
    HTTPException
        If a flavor tag is not found.
    """
    # Delete existing links
    existing_links = session.exec(
        select(BrewTasteFlavorTagLink).where(
            BrewTasteFlavorTagLink.brew_taste_id == taste.id
        )
    ).all()
    for link in existing_links:
        session.delete(link)
    session.flush()

    # Add new links
    for tag_id in flavor_tag_ids:
        tag = session.get(FlavorTag, tag_id)
        if tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"FlavorTag with id '{tag_id}' not found.",
            )
        session.add(
            BrewTasteFlavorTagLink(brew_taste_id=taste.id, flavor_tag_id=tag_id)
        )


def _create_taste(
    session: SessionDep,
    brew: Brew,
    taste_data: BrewTasteCreate,
) -> BrewTaste:
    """Create a BrewTaste for a brew.

    Parameters
    ----------
    session : SessionDep
        Database session.
    brew : Brew
        The parent brew.
    taste_data : BrewTasteCreate
        The taste creation payload.

    Returns
    -------
    BrewTaste
        The newly created taste.
    """
    db_taste = BrewTaste(
        brew_id=brew.id,
        score=taste_data.score,
        acidity=taste_data.acidity,
        sweetness=taste_data.sweetness,
        body=taste_data.body,
        bitterness=taste_data.bitterness,
        balance=taste_data.balance,
        aftertaste=taste_data.aftertaste,
        notes=taste_data.notes,
    )
    session.add(db_taste)
    session.flush()

    if taste_data.flavor_tag_ids:
        _set_taste_tags(session, db_taste, taste_data.flavor_tag_ids)

    return db_taste


def _brew_to_list_read(brew: Brew, brew_setup: BrewSetup | None) -> BrewListRead:
    """Convert a Brew ORM object to BrewListRead dict.

    Parameters
    ----------
    brew : Brew
        The brew model.
    brew_setup : BrewSetup
        The brew setup (for grind display and method name).

    Returns
    -------
    BrewListRead
        Summary representation of the brew for list views.
    """
    grind_display = _compute_grind_display(brew.grind_setting, brew_setup)
    bag = brew.bag
    bean_name = bag.bean.name if bag and bag.bean else "Unknown"
    method = brew_setup.brew_method if brew_setup else None
    brew_method_name = method.name if method else "Unknown"
    person_name = brew.person.name if brew.person else "Unknown"
    taste = brew.taste
    score = taste.score if taste else None

    return BrewListRead(
        id=brew.id,
        grind_setting=brew.grind_setting,
        grind_setting_display=grind_display,
        dose=brew.dose,
        temperature=brew.temperature,
        is_failed=brew.is_failed,
        brewed_at=brew.brewed_at,
        created_at=brew.created_at,
        bean_name=bean_name,
        brew_method_name=brew_method_name,
        person_name=person_name,
        score=score,
    )


def _brew_to_read(brew: Brew) -> dict[str, Any]:
    """Convert a Brew ORM object to BrewRead dict with grind display.

    Parameters
    ----------
    brew : Brew
        The brew model (with relationships loaded).

    Returns
    -------
    dict[str, Any]
        Dict suitable for BrewRead validation.
    """
    brew_setup = brew.brew_setup
    grind_display = _compute_grind_display(brew.grind_setting, brew_setup)

    # Build bag dict with nested bean
    bag = brew.bag
    bag_dict = None
    if bag:
        bean = bag.bean
        bag_dict = {
            "id": bag.id,
            "bean_id": bag.bean_id,
            "weight": bag.weight,
            "price": bag.price,
            "is_preground": bag.is_preground,
            "roast_date": bag.roast_date,
            "opened_at": bag.opened_at,
            "notes": bag.notes,
            "bean": {
                "id": bean.id,
                "name": bean.name,
            }
            if bean
            else None,
        }

    # Person dict
    person = brew.person
    person_dict = None
    if person:
        person_dict = {
            "id": person.id,
            "name": person.name,
        }

    # Stop mode dict
    stop_mode = brew.stop_mode
    stop_mode_dict = None
    if stop_mode:
        stop_mode_dict = {
            "id": stop_mode.id,
            "name": stop_mode.name,
        }

    return {
        "id": brew.id,
        "bag_id": brew.bag_id,
        "brew_setup_id": brew.brew_setup_id,
        "person_id": brew.person_id,
        "grind_setting": brew.grind_setting,
        "grind_setting_display": grind_display,
        "temperature": brew.temperature,
        "pressure": brew.pressure,
        "flow_rate": brew.flow_rate,
        "dose": brew.dose,
        "yield_amount": brew.yield_amount,
        "pre_infusion_time": brew.pre_infusion_time,
        "total_time": brew.total_time,
        "bloom_weight": brew.bloom_weight,
        "preinfusion_pressure": brew.preinfusion_pressure,
        "pressure_profile": brew.pressure_profile,
        "brew_mode": brew.brew_mode,
        "saturation": brew.saturation,
        "bloom_pause": brew.bloom_pause,
        "temp_profile": brew.temp_profile,
        "stop_mode_id": brew.stop_mode_id,
        "is_failed": brew.is_failed,
        "notes": brew.notes,
        "brewed_at": brew.brewed_at,
        "created_at": brew.created_at,
        "updated_at": brew.updated_at,
        "retired_at": brew.retired_at,
        "is_retired": brew.retired_at is not None,
        "bag": bag_dict,
        "brew_setup": brew_setup,
        "person": person_dict,
        "taste": brew.taste,
        "stop_mode": stop_mode_dict,
    }


# ======================================================================
# Brew CRUD
# ======================================================================


@router.get("/brews", response_model=PaginatedResponse[BrewListRead])
def list_brews(
    *,
    person_id: uuid.UUID | None = Query(None, description="Filter by person"),
    bean_id: uuid.UUID | None = Query(None, description="Filter by bean (resolves through bag)"),
    bag_id: uuid.UUID | None = Query(None, description="Filter by bag"),
    brew_setup_id: uuid.UUID | None = Query(None, description="Filter by brew setup"),
    brewed_after: datetime | None = Query(None, description="Filter brewed_at >= value"),
    brewed_before: datetime | None = Query(None, description="Filter brewed_at <= value"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("brewed_at", description="Field to sort by"),
    sort_dir: str = Query("desc", description="Sort direction: asc or desc"),
    session: SessionDep,
) -> PaginatedResponse[BrewListRead]:
    """List brews with filtering, pagination, and sorting."""
    validate_sort(sort_by, sort_dir, BREW_SORT_FIELDS)

    stmt = select(Brew)
    count_stmt = select(func.count()).select_from(Brew)

    if not include_retired:
        stmt = stmt.where(Brew.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Brew.retired_at.is_(None))  # type: ignore[union-attr]

    if person_id is not None:
        stmt = stmt.where(Brew.person_id == person_id)
        count_stmt = count_stmt.where(Brew.person_id == person_id)

    if bean_id is not None:
        # Resolve through bag: find bag IDs for this bean
        bag_ids_stmt = select(Bag.id).where(Bag.bean_id == bean_id)
        stmt = stmt.where(Brew.bag_id.in_(bag_ids_stmt))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Brew.bag_id.in_(bag_ids_stmt))  # type: ignore[union-attr]

    if bag_id is not None:
        stmt = stmt.where(Brew.bag_id == bag_id)
        count_stmt = count_stmt.where(Brew.bag_id == bag_id)

    if brew_setup_id is not None:
        stmt = stmt.where(Brew.brew_setup_id == brew_setup_id)
        count_stmt = count_stmt.where(Brew.brew_setup_id == brew_setup_id)

    if brewed_after is not None:
        stmt = stmt.where(Brew.brewed_at >= brewed_after)  # type: ignore[operator]
        count_stmt = count_stmt.where(Brew.brewed_at >= brewed_after)  # type: ignore[operator]

    if brewed_before is not None:
        stmt = stmt.where(Brew.brewed_at <= brewed_before)  # type: ignore[operator]
        count_stmt = count_stmt.where(Brew.brewed_at <= brewed_before)  # type: ignore[operator]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    # Handle join-based and aliased sort fields
    if sort_by == "grind_setting_display":
        sort_column = Brew.grind_setting
    elif sort_by == "score":
        stmt = stmt.outerjoin(BrewTaste, Brew.id == BrewTaste.brew_id)  # type: ignore[arg-type]
        sort_column = BrewTaste.score
    elif sort_by == "bean_name":
        stmt = stmt.join(Bag, Brew.bag_id == Bag.id).join(Bean, Bag.bean_id == Bean.id)  # type: ignore[arg-type]
        sort_column = Bean.name
    elif sort_by == "brew_method_name":
        stmt = stmt.join(BrewSetup, Brew.brew_setup_id == BrewSetup.id).join(  # type: ignore[arg-type]
            BrewMethod, BrewSetup.brew_method_id == BrewMethod.id
        )
        sort_column = BrewMethod.name
    elif sort_by == "person_name":
        stmt = stmt.join(Person, Brew.person_id == Person.id)  # type: ignore[arg-type]
        sort_column = Person.name
    else:
        sort_column = getattr(Brew, sort_by)

    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)
    stmt = stmt.offset(offset).limit(limit)

    brews = session.exec(stmt).all()
    items = [_brew_to_list_read(b, b.brew_setup) for b in brews]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/brews", response_model=BrewRead, status_code=201)
def create_brew(
    payload: BrewCreate,
    session: SessionDep,
) -> BrewRead:
    """Create a new brew with optional inline taste."""
    # Validate FK references
    bag = session.get(Bag, payload.bag_id)
    if bag is None:
        raise HTTPException(status_code=404, detail="Bag not found.")

    # Auto-mark bag as opened when first used in a brew
    if bag.opened_at is None:
        bag.opened_at = datetime.now(timezone.utc)
        session.add(bag)

    brew_setup = session.get(BrewSetup, payload.brew_setup_id)
    if brew_setup is None:
        raise HTTPException(status_code=404, detail="BrewSetup not found.")

    person = session.get(Person, payload.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    if payload.stop_mode_id is not None:
        stop_mode = session.get(StopMode, payload.stop_mode_id)
        if stop_mode is None:
            raise HTTPException(status_code=404, detail="StopMode not found.")

    # Resolve grind setting
    grind_setting = _resolve_grind_setting(
        payload.grind_setting, payload.grind_setting_display, brew_setup
    )

    db_brew = Brew(
        bag_id=payload.bag_id,
        brew_setup_id=payload.brew_setup_id,
        person_id=payload.person_id,
        grind_setting=grind_setting,
        temperature=payload.temperature,
        pressure=payload.pressure,
        flow_rate=payload.flow_rate,
        dose=payload.dose,
        yield_amount=payload.yield_amount,
        pre_infusion_time=payload.pre_infusion_time,
        total_time=payload.total_time,
        bloom_weight=payload.bloom_weight,
        preinfusion_pressure=payload.preinfusion_pressure,
        pressure_profile=payload.pressure_profile,
        brew_mode=payload.brew_mode,
        saturation=payload.saturation,
        bloom_pause=payload.bloom_pause,
        temp_profile=payload.temp_profile,
        stop_mode_id=payload.stop_mode_id,
        is_failed=payload.is_failed,
        notes=payload.notes,
        brewed_at=payload.brewed_at,
    )
    session.add(db_brew)
    session.flush()

    # Inline taste creation
    if payload.taste is not None:
        _create_taste(session, db_brew, payload.taste)

    session.commit()

    # Auto-create campaign for this bean+setup combination
    ensure_campaign(
        session, bean_id=bag.bean_id, brew_setup_id=payload.brew_setup_id
    )

    session.refresh(db_brew)
    return _brew_to_read(db_brew)  # type: ignore[return-value]


@router.get("/brews/{brew_id}", response_model=BrewRead)
def get_brew(
    brew_id: uuid.UUID,
    session: SessionDep,
) -> BrewRead:
    """Get a single brew by ID with full nesting."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")
    return _brew_to_read(db_brew)  # type: ignore[return-value]


@router.patch("/brews/{brew_id}", response_model=BrewRead)
def update_brew(
    brew_id: uuid.UUID,
    payload: BrewUpdate,
    session: SessionDep,
) -> BrewRead:
    """Partially update a brew."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Validate FK changes
    if "bag_id" in update_data:
        if session.get(Bag, update_data["bag_id"]) is None:
            raise HTTPException(status_code=404, detail="Bag not found.")
    if "brew_setup_id" in update_data:
        if session.get(BrewSetup, update_data["brew_setup_id"]) is None:
            raise HTTPException(status_code=404, detail="BrewSetup not found.")
    if "person_id" in update_data:
        if session.get(Person, update_data["person_id"]) is None:
            raise HTTPException(status_code=404, detail="Person not found.")
    if "stop_mode_id" in update_data and update_data["stop_mode_id"] is not None:
        if session.get(StopMode, update_data["stop_mode_id"]) is None:
            raise HTTPException(status_code=404, detail="StopMode not found.")

    # Handle grind setting display conversion
    grind_display = update_data.pop("grind_setting_display", None)
    if grind_display is not None:
        # Resolve brew_setup — use the updated one if changed, else current
        setup_id = update_data.get("brew_setup_id", db_brew.brew_setup_id)
        brew_setup = session.get(BrewSetup, setup_id)
        update_data["grind_setting"] = _resolve_grind_setting(
            update_data.get("grind_setting"), grind_display, brew_setup
        )
        # Remove raw grind_setting from update_data since we already set it
    elif "grind_setting" in update_data:
        pass  # keep as-is

    db_brew.sqlmodel_update(update_data)
    session.add(db_brew)
    session.commit()
    session.refresh(db_brew)
    return _brew_to_read(db_brew)  # type: ignore[return-value]


@router.delete("/brews/{brew_id}", response_model=BrewRead)
def delete_brew(
    brew_id: uuid.UUID,
    session: SessionDep,
) -> BrewRead:
    """Soft-delete a brew."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    db_brew.retired_at = datetime.now(timezone.utc)
    session.add(db_brew)
    session.commit()
    session.refresh(db_brew)
    return _brew_to_read(db_brew)  # type: ignore[return-value]


# ======================================================================
# Taste sub-resource
# ======================================================================


@router.put("/brews/{brew_id}/taste", response_model=BrewTasteRead)
def put_taste(
    brew_id: uuid.UUID,
    payload: BrewTasteCreate,
    session: SessionDep,
) -> BrewTasteRead:
    """Create or replace the taste for a brew."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    # Delete existing taste if any
    existing_taste = db_brew.taste
    if existing_taste is not None:
        # Delete tag links first
        existing_links = session.exec(
            select(BrewTasteFlavorTagLink).where(
                BrewTasteFlavorTagLink.brew_taste_id == existing_taste.id
            )
        ).all()
        for link in existing_links:
            session.delete(link)
        session.delete(existing_taste)
        session.flush()

    db_taste = _create_taste(session, db_brew, payload)
    session.commit()
    session.refresh(db_taste)
    return db_taste  # type: ignore[return-value]


@router.patch("/brews/{brew_id}/taste", response_model=BrewTasteRead)
def patch_taste(
    brew_id: uuid.UUID,
    payload: BrewTasteUpdate,
    session: SessionDep,
) -> BrewTasteRead:
    """Partially update the taste for a brew."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    db_taste = db_brew.taste
    if db_taste is None:
        raise HTTPException(status_code=404, detail="BrewTaste not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Handle flavor_tag_ids separately
    tag_ids = update_data.pop("flavor_tag_ids", None)

    db_taste.sqlmodel_update(update_data)
    session.add(db_taste)
    session.flush()

    if tag_ids is not None:
        _set_taste_tags(session, db_taste, tag_ids)

    session.commit()
    session.refresh(db_taste)
    return db_taste  # type: ignore[return-value]


@router.delete("/brews/{brew_id}/taste", status_code=204)
def delete_taste(
    brew_id: uuid.UUID,
    session: SessionDep,
) -> None:
    """Remove the taste from a brew."""
    db_brew = session.get(Brew, brew_id)
    if db_brew is None:
        raise HTTPException(status_code=404, detail="Brew not found.")

    db_taste = db_brew.taste
    if db_taste is None:
        raise HTTPException(status_code=404, detail="BrewTaste not found.")

    # Delete tag links
    existing_links = session.exec(
        select(BrewTasteFlavorTagLink).where(
            BrewTasteFlavorTagLink.brew_taste_id == db_taste.id
        )
    ).all()
    for link in existing_links:
        session.delete(link)

    session.delete(db_taste)
    session.commit()
