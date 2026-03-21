"""CRUD routers for BeanRating and BeanTaste models.

BeanRating is append-only — no PATCH on the rating itself.
Taste is a 1:1 sub-resource managed via PUT/PATCH/DELETE.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlmodel import Session, select

from beanbay.database import get_session
from beanbay.models.bean import Bean
from beanbay.models.person import Person
from beanbay.models.rating import (
    BeanRating,
    BeanTaste,
    BeanTasteFlavorTagLink,
)
from beanbay.models.tag import FlavorTag
from beanbay.schemas.common import PaginatedResponse
from beanbay.schemas.rating import (
    BeanRatingCreate,
    BeanRatingRead,
    BeanTasteCreate,
    BeanTasteRead,
    BeanTasteUpdate,
)

router = APIRouter(tags=["Ratings"])


# ======================================================================
# Helper: set M2M flavor tags on a BeanTaste
# ======================================================================


def _set_taste_flavor_tags(
    session: Session,
    taste: BeanTaste,
    flavor_tag_ids: list[uuid.UUID],
) -> None:
    """Replace M2M flavor tags on a taste.

    Parameters
    ----------
    session : Session
        Database session.
    taste : BeanTaste
        The taste to update.
    flavor_tag_ids : list[uuid.UUID]
        Flavor tag IDs to link.
    """
    # Delete existing links
    existing = session.exec(
        select(BeanTasteFlavorTagLink).where(
            BeanTasteFlavorTagLink.bean_taste_id == taste.id
        )
    ).all()
    for link in existing:
        session.delete(link)
    session.flush()

    # Insert new links
    for tag_id in flavor_tag_ids:
        tag = session.get(FlavorTag, tag_id)
        if tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"FlavorTag with id '{tag_id}' not found.",
            )
        session.add(
            BeanTasteFlavorTagLink(
                bean_taste_id=taste.id, flavor_tag_id=tag_id
            )
        )


# ======================================================================
# Helper: create a BeanTaste from schema
# ======================================================================


def _create_taste(
    session: Session,
    rating_id: uuid.UUID,
    taste_data: BeanTasteCreate,
) -> BeanTaste:
    """Create a BeanTaste row and set its flavor tags.

    Parameters
    ----------
    session : Session
        Database session.
    rating_id : uuid.UUID
        Parent rating's primary key.
    taste_data : BeanTasteCreate
        Taste creation data.

    Returns
    -------
    BeanTaste
        The created taste.
    """
    db_taste = BeanTaste(
        bean_rating_id=rating_id,
        score=taste_data.score,
        acidity=taste_data.acidity,
        sweetness=taste_data.sweetness,
        body=taste_data.body,
        bitterness=taste_data.bitterness,
        aroma=taste_data.aroma,
        intensity=taste_data.intensity,
        notes=taste_data.notes,
    )
    session.add(db_taste)
    session.flush()

    if taste_data.flavor_tag_ids:
        _set_taste_flavor_tags(session, db_taste, taste_data.flavor_tag_ids)

    return db_taste


# ======================================================================
# GET /beans/{bean_id}/ratings — list ratings for a bean
# ======================================================================


@router.get(
    "/beans/{bean_id}/ratings",
    response_model=PaginatedResponse[BeanRatingRead],
)
def list_bean_ratings(
    bean_id: uuid.UUID,
    person_id: uuid.UUID | None = Query(None, description="Filter by person"),
    include_retired: bool = Query(False, description="Include soft-deleted items"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """List ratings for a bean, ordered by rated_at desc.

    Parameters
    ----------
    bean_id : uuid.UUID
        The bean's primary key.
    person_id : uuid.UUID | None
        Optional filter by person.
    include_retired : bool
        When ``True``, include soft-deleted ratings.
    limit : int
        Maximum items per page (1--200).
    offset : int
        Number of items to skip.
    session : Session
        Database session (injected).

    Returns
    -------
    dict[str, Any]
        Paginated response with ``items``, ``total``, ``limit``, ``offset``.
    """
    # Verify bean exists
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    stmt = select(BeanRating).where(BeanRating.bean_id == bean_id)
    count_stmt = (
        select(func.count())
        .select_from(BeanRating)
        .where(BeanRating.bean_id == bean_id)
    )

    if not include_retired:
        stmt = stmt.where(BeanRating.retired_at.is_(None))  # type: ignore[union-attr]
        count_stmt = count_stmt.where(BeanRating.retired_at.is_(None))  # type: ignore[union-attr]

    if person_id is not None:
        stmt = stmt.where(BeanRating.person_id == person_id)
        count_stmt = count_stmt.where(BeanRating.person_id == person_id)

    total: int = session.exec(count_stmt).one()  # type: ignore[arg-type]

    stmt = stmt.order_by(BeanRating.rated_at.desc())  # type: ignore[union-attr]
    stmt = stmt.offset(offset).limit(limit)
    items = session.exec(stmt).all()

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ======================================================================
# POST /beans/{bean_id}/ratings — create new rating (append-only)
# ======================================================================


@router.post(
    "/beans/{bean_id}/ratings",
    response_model=BeanRatingRead,
    status_code=201,
)
def create_bean_rating(
    bean_id: uuid.UUID,
    payload: BeanRatingCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create a new rating for a bean.

    Multiple ratings for the same bean+person are allowed (append-only).

    Parameters
    ----------
    bean_id : uuid.UUID
        The bean's primary key (from path).
    payload : BeanRatingCreate
        Rating data including optional inline taste.
    session : Session
        Database session (injected).

    Returns
    -------
    Any
        The created rating.
    """
    # Verify bean exists
    db_bean = session.get(Bean, bean_id)
    if db_bean is None:
        raise HTTPException(status_code=404, detail="Bean not found.")

    # Verify person exists
    db_person = session.get(Person, payload.person_id)
    if db_person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    db_rating = BeanRating(
        bean_id=bean_id,
        person_id=payload.person_id,
    )
    if payload.rated_at is not None:
        db_rating.rated_at = payload.rated_at

    session.add(db_rating)
    session.flush()

    # Create inline taste if provided
    if payload.taste is not None:
        _create_taste(session, db_rating.id, payload.taste)

    session.commit()
    session.refresh(db_rating)
    return db_rating


# ======================================================================
# GET /bean-ratings/{id} — detail with nested taste
# ======================================================================


@router.get("/bean-ratings/{rating_id}", response_model=BeanRatingRead)
def get_bean_rating(
    rating_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Get a single bean rating by ID with nested taste.

    Parameters
    ----------
    rating_id : uuid.UUID
        The rating's primary key.
    session : Session
        Database session (injected).

    Returns
    -------
    Any
        The rating with nested taste.
    """
    db_rating = session.get(BeanRating, rating_id)
    if db_rating is None:
        raise HTTPException(status_code=404, detail="BeanRating not found.")
    return db_rating


# ======================================================================
# DELETE /bean-ratings/{id} — soft-delete
# ======================================================================


@router.delete("/bean-ratings/{rating_id}", response_model=BeanRatingRead)
def delete_bean_rating(
    rating_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Any:
    """Soft-delete a bean rating.

    Parameters
    ----------
    rating_id : uuid.UUID
        The rating's primary key.
    session : Session
        Database session (injected).

    Returns
    -------
    Any
        The soft-deleted rating.
    """
    db_rating = session.get(BeanRating, rating_id)
    if db_rating is None:
        raise HTTPException(status_code=404, detail="BeanRating not found.")

    db_rating.retired_at = datetime.now(timezone.utc)
    session.add(db_rating)
    session.commit()
    session.refresh(db_rating)
    return db_rating


# ======================================================================
# PUT /bean-ratings/{id}/taste — create or replace taste
# ======================================================================


@router.put(
    "/bean-ratings/{rating_id}/taste",
    response_model=BeanTasteRead,
)
def put_bean_rating_taste(
    rating_id: uuid.UUID,
    payload: BeanTasteCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create or replace the taste for a bean rating.

    If a taste already exists, it is deleted and replaced with the new one.

    Parameters
    ----------
    rating_id : uuid.UUID
        The rating's primary key.
    payload : BeanTasteCreate
        Taste data.
    session : Session
        Database session (injected).

    Returns
    -------
    Any
        The created or replaced taste.
    """
    db_rating = session.get(BeanRating, rating_id)
    if db_rating is None:
        raise HTTPException(status_code=404, detail="BeanRating not found.")

    # Delete existing taste if present
    existing_taste = session.exec(
        select(BeanTaste).where(BeanTaste.bean_rating_id == rating_id)
    ).first()
    if existing_taste is not None:
        # Delete flavor tag links first
        existing_links = session.exec(
            select(BeanTasteFlavorTagLink).where(
                BeanTasteFlavorTagLink.bean_taste_id == existing_taste.id
            )
        ).all()
        for link in existing_links:
            session.delete(link)
        session.delete(existing_taste)
        session.flush()

    db_taste = _create_taste(session, rating_id, payload)
    session.commit()
    session.refresh(db_taste)
    return db_taste


# ======================================================================
# PATCH /bean-ratings/{id}/taste — partial update taste
# ======================================================================


@router.patch(
    "/bean-ratings/{rating_id}/taste",
    response_model=BeanTasteRead,
)
def patch_bean_rating_taste(
    rating_id: uuid.UUID,
    payload: BeanTasteUpdate,
    session: Session = Depends(get_session),
) -> Any:
    """Partially update the taste for a bean rating.

    Parameters
    ----------
    rating_id : uuid.UUID
        The rating's primary key.
    payload : BeanTasteUpdate
        Fields to update.
    session : Session
        Database session (injected).

    Returns
    -------
    Any
        The updated taste.
    """
    db_rating = session.get(BeanRating, rating_id)
    if db_rating is None:
        raise HTTPException(status_code=404, detail="BeanRating not found.")

    db_taste = session.exec(
        select(BeanTaste).where(BeanTaste.bean_rating_id == rating_id)
    ).first()
    if db_taste is None:
        raise HTTPException(status_code=404, detail="BeanTaste not found.")

    update_data = payload.model_dump(exclude_unset=True)

    # Extract flavor_tag_ids for M2M handling
    flavor_tag_ids = update_data.pop("flavor_tag_ids", None)

    # Apply scalar updates
    db_taste.sqlmodel_update(update_data)
    session.add(db_taste)
    session.flush()

    # Handle M2M only if provided
    raw_unset = payload.model_dump(exclude_unset=True)
    if "flavor_tag_ids" in raw_unset and flavor_tag_ids is not None:
        _set_taste_flavor_tags(session, db_taste, flavor_tag_ids)

    session.commit()
    session.refresh(db_taste)
    return db_taste


# ======================================================================
# DELETE /bean-ratings/{id}/taste — remove taste
# ======================================================================


@router.delete(
    "/bean-ratings/{rating_id}/taste",
    status_code=204,
)
def delete_bean_rating_taste(
    rating_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> Response:
    """Remove the taste from a bean rating.

    Parameters
    ----------
    rating_id : uuid.UUID
        The rating's primary key.
    session : Session
        Database session (injected).

    Returns
    -------
    Response
        Empty 204 response.
    """
    db_rating = session.get(BeanRating, rating_id)
    if db_rating is None:
        raise HTTPException(status_code=404, detail="BeanRating not found.")

    db_taste = session.exec(
        select(BeanTaste).where(BeanTaste.bean_rating_id == rating_id)
    ).first()
    if db_taste is None:
        raise HTTPException(status_code=404, detail="BeanTaste not found.")

    # Delete flavor tag links first
    existing_links = session.exec(
        select(BeanTasteFlavorTagLink).where(
            BeanTasteFlavorTagLink.bean_taste_id == db_taste.id
        )
    ).all()
    for link in existing_links:
        session.delete(link)
    session.delete(db_taste)
    session.commit()
    return Response(status_code=204)
