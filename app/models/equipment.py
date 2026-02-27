import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Table, func
from sqlalchemy.orm import relationship

from app.database import Base


# Valid values for brewer capability enums
TEMP_CONTROL_TYPES = ("none", "preset", "pid", "profiling")
PREINFUSION_TYPES = ("none", "fixed", "timed", "adjustable_pressure", "programmable", "manual")
PRESSURE_CONTROL_TYPES = (
    "fixed",
    "opv_adjustable",
    "electronic",
    "manual_profiling",
    "programmable",
)
FLOW_CONTROL_TYPES = ("none", "manual_paddle", "manual_valve", "programmable")
STOP_MODES = ("manual", "timed", "volumetric", "gravimetric")


# Association table for Brewer <-> BrewMethod many-to-many relationship
brewer_methods = Table(
    "brewer_methods",
    Base.metadata,
    Column("brewer_id", String, ForeignKey("brewers.id"), primary_key=True),
    Column("method_id", String, ForeignKey("brew_methods.id"), primary_key=True),
)


class Grinder(Base):
    __tablename__ = "grinders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    dial_type = Column(String, nullable=False, default="stepless")  # "stepped" or "stepless"
    step_size = Column(Float, nullable=True)  # only meaningful when dial_type="stepped"
    min_value = Column(Float, nullable=True)  # minimum grind setting
    max_value = Column(Float, nullable=True)  # maximum grind setting
    is_retired = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Brewer(Base):
    __tablename__ = "brewers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    is_retired = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # ── Capability flags ─────────────────────────────────────────────────
    # Temperature capabilities
    temp_control_type = Column(String, nullable=False, default="pid")
    # Values: "none", "preset", "pid", "profiling"
    temp_min = Column(Float, nullable=True)  # °C — null means no settable range
    temp_max = Column(Float, nullable=True)  # °C
    temp_step = Column(Float, nullable=True)  # Resolution in °C (e.g., 0.5, 1.0)

    # Pre-infusion capabilities
    preinfusion_type = Column(String, nullable=False, default="none")
    # Values: "none", "fixed", "timed", "adjustable_pressure", "programmable", "manual"
    preinfusion_max_time = Column(Float, nullable=True)  # seconds

    # Pressure capabilities
    pressure_control_type = Column(String, nullable=False, default="fixed")
    # Values: "fixed", "opv_adjustable", "electronic", "manual_profiling", "programmable"
    pressure_min = Column(Float, nullable=True)  # bar
    pressure_max = Column(Float, nullable=True)  # bar

    # Flow capabilities
    flow_control_type = Column(String, nullable=False, default="none")
    # Values: "none", "manual_paddle", "manual_valve", "programmable"
    saturation_flow_rate = Column(Float, nullable=True)
    # ml/s — fixed brewer-level setting for saturation flow rate (e.g., 1.5 for Sage DB slayer mod)

    # Bloom capability
    has_bloom = Column(Boolean, nullable=False, default=False)

    # Stop mode
    stop_mode = Column(String, nullable=False, default="manual")
    # Values: "manual", "timed", "volumetric", "gravimetric"

    methods = relationship("BrewMethod", secondary="brewer_methods", backref="brewers")

    def __init__(self, **kwargs):
        # Set Python-side defaults so attributes are accessible before DB flush
        kwargs.setdefault("temp_control_type", "pid")
        kwargs.setdefault("preinfusion_type", "none")
        kwargs.setdefault("pressure_control_type", "fixed")
        kwargs.setdefault("flow_control_type", "none")
        kwargs.setdefault("has_bloom", False)
        kwargs.setdefault("stop_mode", "manual")
        super().__init__(**kwargs)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_retired = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


class WaterRecipe(Base):
    __tablename__ = "water_recipes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    recipe_details = Column(String, nullable=True)
    notes = Column(String, nullable=True)  # how it was made
    gh = Column(Float, nullable=True)  # General Hardness
    kh = Column(Float, nullable=True)  # Carbonate Hardness
    ca = Column(Float, nullable=True)  # Calcium
    mg = Column(Float, nullable=True)  # Magnesium
    na = Column(Float, nullable=True)  # Sodium
    cl = Column(Float, nullable=True)  # Chloride
    so4 = Column(Float, nullable=True)  # Sulfate
    is_retired = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
