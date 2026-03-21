"""BeanBay database models.

Re-exports all models so Alembic can discover them via ``SQLModel.metadata``.

Canonical Units (SI/Metric)
---------------------------
All physical quantities are stored in SI/metric units. The API always
accepts and returns these units. Frontend clients handle display conversion.

- **Weight / mass**: grams (g) — dose, yield_amount, bag weight
- **Temperature**: degrees Celsius (C) — brew temperature, brewer temp_min/max/step
- **Pressure**: bar — brew pressure, brewer pressure_min/max
- **Flow rate**: millilitres per second (ml/s) — flow_rate, saturation_flow_rate
- **Time**: seconds (s) — pre_infusion_time, total_time, preinfusion_max_time
- **Concentration**: parts per million (ppm) — water mineral content
"""
from beanbay.models.bean import (  # noqa: F401
    Bag,
    Bean,
    BeanOriginLink,
    BeanProcessLink,
    BeanVarietyLink,
)
from beanbay.models.brew import (  # noqa: F401
    Brew,
    BrewSetup,
    BrewTaste,
    BrewTasteFlavorTagLink,
)
from beanbay.models.equipment import (  # noqa: F401
    Brewer,
    BrewerMethodLink,
    BrewerStopModeLink,
    Grinder,
    Paper,
    Water,
    WaterMineral,
)
from beanbay.models.person import Person  # noqa: F401
from beanbay.models.rating import (  # noqa: F401
    BeanRating,
    BeanTaste,
    BeanTasteFlavorTagLink,
)
from beanbay.models.tag import (  # noqa: F401
    BeanVariety,
    BrewMethod,
    FlavorTag,
    Origin,
    ProcessMethod,
    Roaster,
    StopMode,
    StorageType,
    Vendor,
)
