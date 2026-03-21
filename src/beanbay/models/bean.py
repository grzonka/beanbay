"""Bean and Bag models for BeanBay.

Bean represents a coffee bean with many-to-many relationships to Origin,
ProcessMethod, and BeanVariety, a foreign key to Roaster, and a
one-to-many relationship to Bag.

Bag represents a physical bag of a particular bean, tracking weight,
price, roast date, and whether it is pre-ground.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default


# ---------------------------------------------------------------------------
# Junction / link models for Bean M2M
# ---------------------------------------------------------------------------


class BeanOriginLink(SQLModel, table=True):
    """Link table between Bean and Origin.

    Attributes
    ----------
    bean_id : uuid.UUID
        Foreign key to the bean.
    origin_id : uuid.UUID
        Foreign key to the origin.
    """

    __tablename__ = "bean_origins"  # type: ignore[assignment]

    bean_id: uuid.UUID = Field(
        foreign_key="beans.id", primary_key=True
    )
    origin_id: uuid.UUID = Field(
        foreign_key="origins.id", primary_key=True
    )


class BeanProcessLink(SQLModel, table=True):
    """Link table between Bean and ProcessMethod.

    Attributes
    ----------
    bean_id : uuid.UUID
        Foreign key to the bean.
    process_id : uuid.UUID
        Foreign key to the process method.
    """

    __tablename__ = "bean_processes"  # type: ignore[assignment]

    bean_id: uuid.UUID = Field(
        foreign_key="beans.id", primary_key=True
    )
    process_id: uuid.UUID = Field(
        foreign_key="process_methods.id", primary_key=True
    )


class BeanVarietyLink(SQLModel, table=True):
    """Link table between Bean and BeanVariety.

    Attributes
    ----------
    bean_id : uuid.UUID
        Foreign key to the bean.
    variety_id : uuid.UUID
        Foreign key to the bean variety.
    """

    __tablename__ = "bean_variety_link"  # type: ignore[assignment]

    bean_id: uuid.UUID = Field(
        foreign_key="beans.id", primary_key=True
    )
    variety_id: uuid.UUID = Field(
        foreign_key="bean_varieties.id", primary_key=True
    )


# ---------------------------------------------------------------------------
# Bean model
# ---------------------------------------------------------------------------


class Bean(SQLModel, table=True):
    """A coffee bean entry.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Name of the bean / blend.
    roaster_id : uuid.UUID | None
        Foreign key to the roaster.
    notes : str | None
        Free-text notes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "beans"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True)
    roaster_id: uuid.UUID | None = Field(
        default=None, foreign_key="roasters.id"
    )
    notes: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    roaster: Optional["Roaster"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
    )
    bags: list["Bag"] = Relationship(back_populates="bean")
    origins: list["Origin"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BeanOriginLink,
    )
    processes: list["ProcessMethod"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BeanProcessLink,
    )
    varieties: list["BeanVariety"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BeanVarietyLink,
    )


# ---------------------------------------------------------------------------
# Bag model
# ---------------------------------------------------------------------------


class Bag(SQLModel, table=True):
    """A physical bag of coffee beans.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the parent bean.
    roast_date : date | None
        Date the coffee was roasted.
    opened_at : date | None
        Date the bag was opened.
    weight : float
        Weight in grams (canonical unit).
    price : float | None
        Price paid for the bag.
    is_preground : bool
        Whether the coffee is pre-ground.
    notes : str | None
        Free-text notes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "bags"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id")
    roast_date: date | None = None
    opened_at: date | None = None
    weight: float
    price: float | None = None
    is_preground: bool = Field(default=False)
    notes: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    bean: Bean = Relationship(back_populates="bags")
