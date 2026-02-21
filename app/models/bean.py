import uuid

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Bean(Base):
    __tablename__ = "beans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    roaster = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    measurements = relationship("Measurement", back_populates="bean", cascade="all, delete-orphan")
