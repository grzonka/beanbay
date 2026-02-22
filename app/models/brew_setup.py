import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class BrewSetup(Base):
    __tablename__ = "brew_setups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    brew_method_id = Column(String, ForeignKey("brew_methods.id"), nullable=False)
    grinder_id = Column(String, ForeignKey("grinders.id"), nullable=True)
    brewer_id = Column(String, ForeignKey("brewers.id"), nullable=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=True)
    water_recipe_id = Column(String, ForeignKey("water_recipes.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    brew_method = relationship("BrewMethod")
    grinder = relationship("Grinder")
    brewer = relationship("Brewer")
    paper = relationship("Paper")
    water_recipe = relationship("WaterRecipe")
