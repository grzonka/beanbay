"""Read / write schemas for BrewSetup.

Schemas for creating, updating, and reading brew setups with light
nesting of related equipment names.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel


# ---------------------------------------------------------------------------
# BrewSetup
# ---------------------------------------------------------------------------


class BrewSetupBase(SQLModel):
    """Shared fields for BrewSetup schemas.

    Attributes
    ----------
    name : str | None
        Optional name for the setup.
    """

    name: str | None = None


class BrewSetupCreate(BrewSetupBase):
    """Schema for creating a BrewSetup.

    Attributes
    ----------
    brew_method_id : uuid.UUID
        Required brew method FK.
    grinder_id : uuid.UUID | None
        Optional grinder FK.
    brewer_id : uuid.UUID | None
        Optional brewer FK.
    paper_id : uuid.UUID | None
        Optional paper FK.
    water_id : uuid.UUID | None
        Optional water FK.
    """

    brew_method_id: uuid.UUID
    grinder_id: uuid.UUID | None = None
    brewer_id: uuid.UUID | None = None
    paper_id: uuid.UUID | None = None
    water_id: uuid.UUID | None = None


class BrewSetupUpdate(SQLModel):
    """Schema for partially updating a BrewSetup.

    Attributes
    ----------
    name : str | None
        Updated name.
    brew_method_id : uuid.UUID | None
        Updated brew method FK.
    grinder_id : uuid.UUID | None
        Updated grinder FK.
    brewer_id : uuid.UUID | None
        Updated brewer FK.
    paper_id : uuid.UUID | None
        Updated paper FK.
    water_id : uuid.UUID | None
        Updated water FK.
    """

    name: str | None = None
    brew_method_id: uuid.UUID | None = None
    grinder_id: uuid.UUID | None = None
    brewer_id: uuid.UUID | None = None
    paper_id: uuid.UUID | None = None
    water_id: uuid.UUID | None = None


class BrewSetupRead(BrewSetupBase):
    """Schema returned when reading a BrewSetup.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    brew_method_id : uuid.UUID
        Brew method FK.
    grinder_id : uuid.UUID | None
        Grinder FK.
    brewer_id : uuid.UUID | None
        Brewer FK.
    paper_id : uuid.UUID | None
        Paper FK.
    water_id : uuid.UUID | None
        Water FK.
    brew_method_name : str | None
        Name of the linked brew method.
    grinder_name : str | None
        Name of the linked grinder.
    brewer_name : str | None
        Name of the linked brewer.
    paper_name : str | None
        Name of the linked paper.
    water_name : str | None
        Name of the linked water.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    brew_method_id: uuid.UUID
    grinder_id: uuid.UUID | None
    brewer_id: uuid.UUID | None
    paper_id: uuid.UUID | None
    water_id: uuid.UUID | None

    brew_method_name: str | None = None
    grinder_name: str | None = None
    brewer_name: str | None = None
    paper_name: str | None = None
    water_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_brew_setup_fields(cls, data: Any) -> Any:
        """Compute ``is_retired`` and extract nested equipment names.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : Any
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        Any
            A dict with computed fields populated.
        """
        if not isinstance(data, dict):
            d: dict[str, Any] = {}
            for field in (
                "id",
                "name",
                "brew_method_id",
                "grinder_id",
                "brewer_id",
                "paper_id",
                "water_id",
                "created_at",
                "updated_at",
                "retired_at",
            ):
                d[field] = getattr(data, field, None)

            # Extract names from relationships
            brew_method = getattr(data, "brew_method", None)
            d["brew_method_name"] = brew_method.name if brew_method else None

            grinder = getattr(data, "grinder", None)
            d["grinder_name"] = grinder.name if grinder else None

            brewer = getattr(data, "brewer", None)
            d["brewer_name"] = brewer.name if brewer else None

            paper = getattr(data, "paper", None)
            d["paper_name"] = paper.name if paper else None

            water = getattr(data, "water", None)
            d["water_name"] = water.name if water else None

            data = d

        data["is_retired"] = data.get("retired_at") is not None
        return data
