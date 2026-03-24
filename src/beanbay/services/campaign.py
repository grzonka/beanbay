"""Shared campaign creation logic."""

from __future__ import annotations

import uuid

from sqlmodel import Session, select

from beanbay.models.optimization import Campaign


def ensure_campaign(
    session: Session,
    *,
    bean_id: uuid.UUID,
    brew_setup_id: uuid.UUID,
) -> tuple[Campaign, bool]:
    """Return existing campaign or create a new one for the bean+setup pair.

    Idempotent: if a campaign already exists for this combination,
    returns it without modification. Otherwise creates a new campaign
    with default state.

    Parameters
    ----------
    session : Session
        Database session.
    bean_id : uuid.UUID
        Bean foreign key.
    brew_setup_id : uuid.UUID
        Brew setup foreign key.

    Returns
    -------
    tuple[Campaign, bool]
        The campaign and whether it was newly created (True) or
        already existed (False).
    """
    existing = session.exec(
        select(Campaign).where(
            Campaign.bean_id == bean_id,
            Campaign.brew_setup_id == brew_setup_id,
        )
    ).first()

    if existing is not None:
        return existing, False

    campaign = Campaign(bean_id=bean_id, brew_setup_id=brew_setup_id)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign, True
