# Re-export all models so Alembic can discover them via SQLModel.metadata
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
)
