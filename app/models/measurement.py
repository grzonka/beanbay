from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False, index=True)
    recommendation_id = Column(String, nullable=True, unique=True)

    # BayBE parameters
    grind_setting = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    preinfusion_pct = Column(Float, nullable=False)
    dose_in = Column(Float, nullable=False)
    target_yield = Column(Float, nullable=False)
    saturation = Column(String, nullable=False)

    # Target (required)
    taste = Column(Float, nullable=False)

    # Metadata (optional)
    extraction_time = Column(Float, nullable=True)
    is_failed = Column(Boolean, default=False)
    notes = Column(String, nullable=True)

    # Flavor profile (all optional, Phase 4)
    acidity = Column(Float, nullable=True)
    sweetness = Column(Float, nullable=True)
    body = Column(Float, nullable=True)
    bitterness = Column(Float, nullable=True)
    aroma = Column(Float, nullable=True)
    intensity = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    bean = relationship("Bean", back_populates="measurements")
