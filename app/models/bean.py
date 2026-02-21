import uuid

from sqlalchemy import Column, DateTime, JSON, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Bean(Base):
    __tablename__ = "beans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    roaster = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Per-bean BayBE parameter range overrides.
    # JSON dict, e.g. {"grind_setting": {"min": 18.0, "max": 22.0}, ...}
    # Only include parameters that differ from defaults. null/{} = use defaults.
    parameter_overrides = Column(JSON, nullable=True, default=None)

    measurements = relationship("Measurement", back_populates="bean", cascade="all, delete-orphan")
