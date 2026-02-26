from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False, index=True)
    recommendation_id = Column(String, nullable=True, unique=True)

    # BayBE parameters — core (always present)
    grind_setting = Column(Float, nullable=False)
    # temperature is nullable from Phase 21 onwards: cold-brew has no heated water
    temperature = Column(Float, nullable=True)
    dose_in = Column(Float, nullable=False)

    # Espresso-specific parameters (nullable for non-espresso methods)
    preinfusion_pressure_pct = Column(
        Float, nullable=True
    )  # pump pressure % during pre-infusion (55-100%)
    target_yield = Column(Float, nullable=True)
    saturation = Column(String, nullable=True)

    # Phase 20: Advanced espresso parameters (all nullable)
    preinfusion_time = Column(Float, nullable=True)  # seconds — pre-infusion hold time
    preinfusion_pressure = Column(Float, nullable=True)  # bar — pressure during pre-infusion
    brew_pressure = Column(Float, nullable=True)  # bar — target brew pressure
    pressure_profile = Column(
        String, nullable=True
    )  # categorical: flat/ramp_up/ramp_down/pre_infusion_ramp
    bloom_pause = Column(Float, nullable=True)  # seconds — pour-over bloom pause
    flow_rate = Column(Float, nullable=True)  # ml/s — flow rate
    temp_profile = Column(String, nullable=True)  # categorical: flat/ramp_up/ramp_down

    # Phase 21: Method-specific parameters (all nullable)
    # steep_time: minutes steeping (french-press, aeropress, cold-brew)
    steep_time = Column(Float, nullable=True)
    # brew_volume: total water in ml (pour-over, french-press, aeropress, turkish, moka-pot)
    brew_volume = Column(Float, nullable=True)
    # bloom_weight: bloom water weight in g (pour-over)
    bloom_weight = Column(Float, nullable=True)
    # brew_mode: "standard"/"inverted" for aeropress (also used as general brew_mode)
    brew_mode = Column(String, nullable=True)

    # Target (required)
    taste = Column(Float, nullable=False)

    # Metadata (optional)
    extraction_time = Column(Float, nullable=True)
    is_failed = Column(Boolean, default=False)
    is_manual = Column(Boolean, nullable=True, default=False)
    notes = Column(String, nullable=True)

    # Flavor profile (all optional, Phase 4)
    acidity = Column(Float, nullable=True)
    sweetness = Column(Float, nullable=True)
    body = Column(Float, nullable=True)
    bitterness = Column(Float, nullable=True)
    aroma = Column(Float, nullable=True)
    intensity = Column(Float, nullable=True)
    flavor_tags = Column(String, nullable=True)  # JSON-encoded list of tag strings

    # Phase 13: Link to brew setup (nullable for backward compatibility)
    brew_setup_id = Column(String, ForeignKey("brew_setups.id"), nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now())

    bean = relationship("Bean", back_populates="measurements")
    brew_setup = relationship("BrewSetup")
