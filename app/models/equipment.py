import uuid

from sqlalchemy import Column, DateTime, String, func

from app.database import Base


class Grinder(Base):
    __tablename__ = "grinders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Brewer(Base):
    __tablename__ = "brewers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class WaterRecipe(Base):
    __tablename__ = "water_recipes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    recipe_details = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
