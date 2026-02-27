from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.types import JSON

from app.database import Base


class PendingRecommendation(Base):
    __tablename__ = "pending_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String, unique=True, nullable=False, index=True)
    recommendation_data = Column(JSON, nullable=False)  # Full recommendation dict
    created_at = Column(DateTime, server_default=func.now())
