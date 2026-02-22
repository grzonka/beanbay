import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Bag(Base):
    __tablename__ = "bags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False, index=True)
    purchase_date = Column(Date, nullable=True)
    cost = Column(Float, nullable=True)
    weight_grams = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    bean = relationship("Bean", back_populates="bags")
