import uuid

from sqlalchemy import Column, DateTime, String, func

from app.database import Base


class BrewMethod(Base):
    __tablename__ = "brew_methods"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
