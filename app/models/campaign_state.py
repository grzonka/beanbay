from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.types import JSON

from app.database import Base


class CampaignState(Base):
    __tablename__ = "campaign_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_key = Column(String, unique=True, nullable=False, index=True)
    campaign_json = Column(Text, nullable=False)  # BayBE Campaign.to_json() — opaque blob
    bounds_fingerprint = Column(String(16), nullable=True)  # 16-char hex hash of numeric ranges
    param_set_fingerprint = Column(String(16), nullable=True)  # 16-char hex hash of param names
    rebuild_declined = Column(
        Integer, nullable=True, default=0
    )  # 0=not declined, 1=declined once, 2=permanently declined
    transfer_metadata = Column(JSON, nullable=True)  # dict with contributing_beans, etc.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
