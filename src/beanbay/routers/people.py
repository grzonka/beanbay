"""CRUD router for the Person model.

Unlike the generic lookup factory, this router includes custom logic for
the ``is_default`` flag: when a person is set as default, any previous
default is automatically unset in the same transaction.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select

from beanbay.dependencies import SessionDep
from beanbay.models.person import Person
from beanbay.schemas.common import PaginatedResponse
from beanbay.schemas.person import PersonCreate, PersonRead, PersonUpdate

SORTABLE_FIELDS = ["name", "created_at", "updated_at"]

router = APIRouter(prefix="/people", tags=["People"])


# ------------------------------------------------------------------
# GET /  — list with filtering, pagination, sorting
# ------------------------------------------------------------------
@router.get("", response_model=PaginatedResponse[PersonRead])
def list_people(
    *,
    q: str | None = Query(None, description="Case-insensitive name search"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    session: SessionDep,
) -> PaginatedResponse[PersonRead]:
    """List people with optional search, pagination, and sorting.

    Parameters
    ----------
    q : str | None
        Case-insensitive substring match on ``name``.
    include_retired : bool
        When ``True``, include soft-deleted people.
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
    PaginatedResponse[PersonRead]
        Paginated response with ``items``, ``total``, ``limit``, ``offset``.
    """
    if sort_by not in SORTABLE_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid sort_by field '{sort_by}'. "
                f"Allowed: {SORTABLE_FIELDS}"
            ),
        )
    if sort_dir not in ("asc", "desc"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_dir '{sort_dir}'. Must be 'asc' or 'desc'.",
        )

    stmt = select(Person)
    count_stmt = select(func.count()).select_from(Person)

    if not include_retired:
        stmt = stmt.where(Person.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Person.retired_at.is_(None))  # type: ignore[union-attr]

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Person.name.ilike(pattern))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(Person.name.ilike(pattern))  # type: ignore[union-attr]

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    sort_column = getattr(Person, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)

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
@router.post("", response_model=PersonRead, status_code=201)
def create_person(
    payload: PersonCreate,
    session: SessionDep,
) -> PersonRead:
    """Create a new person.

    Parameters
    ----------
    payload : PersonCreate
        The person data.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PersonRead
        The created person.
    """
    existing = session.exec(
        select(Person).where(Person.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A person with name '{payload.name}' already exists.",
        )

    db_person = Person.model_validate(payload)
    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return db_person  # type: ignore[return-value]


# ------------------------------------------------------------------
# GET /{id}  — get by ID
# ------------------------------------------------------------------
@router.get("/{person_id}", response_model=PersonRead)
def get_person(
    person_id: uuid.UUID,
    session: SessionDep,
) -> PersonRead:
    """Get a single person by ID.

    Parameters
    ----------
    person_id : uuid.UUID
        The person's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PersonRead
        The person.
    """
    db_person = session.get(Person, person_id)
    if db_person is None:
        raise HTTPException(status_code=404, detail="Person not found.")
    return db_person  # type: ignore[return-value]


# ------------------------------------------------------------------
# PATCH /{id}  — partial update
# ------------------------------------------------------------------
@router.patch("/{person_id}", response_model=PersonRead)
def update_person(
    person_id: uuid.UUID,
    payload: PersonUpdate,
    session: SessionDep,
) -> PersonRead:
    """Partially update a person.

    When ``is_default`` is set to ``True``, the previous default person
    (if any) is automatically unset in the same transaction.

    Parameters
    ----------
    person_id : uuid.UUID
        The person's primary key.
    payload : PersonUpdate
        Fields to update.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PersonRead
        The updated person.
    """
    db_person = session.get(Person, person_id)
    if db_person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # If name is being updated, check uniqueness
    if "name" in update_data:
        existing = session.exec(
            select(Person).where(
                Person.name == update_data["name"],
                Person.id != person_id,  # type: ignore[union-attr]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A person with name '{update_data['name']}' already exists.",
            )

    # If setting is_default=True, unset the current default first
    if update_data.get("is_default") is True:
        current_default = session.exec(
            select(Person).where(
                Person.is_default.is_(True),  # type: ignore[union-attr]
                Person.id != person_id,  # type: ignore[union-attr]
            )
        ).first()
        if current_default is not None:
            current_default.is_default = False
            session.add(current_default)

    db_person.sqlmodel_update(update_data)
    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return db_person  # type: ignore[return-value]


# ------------------------------------------------------------------
# DELETE /{id}  — soft-delete
# ------------------------------------------------------------------
@router.delete("/{person_id}", response_model=PersonRead)
def delete_person(
    person_id: uuid.UUID,
    session: SessionDep,
) -> PersonRead:
    """Soft-delete a person by setting ``retired_at``.

    Parameters
    ----------
    person_id : uuid.UUID
        The person's primary key.
    session : SessionDep
        Database session (injected).

    Returns
    -------
    PersonRead
        The soft-deleted person.
    """
    db_person = session.get(Person, person_id)
    if db_person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    db_person.retired_at = datetime.now(timezone.utc)
    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return db_person  # type: ignore[return-value]
