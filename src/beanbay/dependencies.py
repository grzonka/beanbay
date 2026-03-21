"""Shared FastAPI dependency types for BeanBay."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from beanbay.database import get_session

SessionDep = Annotated[Session, Depends(get_session)]
