# Phase 1 Research: Foundation & Infrastructure

**Phase:** 01 — Foundation & Infrastructure
**Researched:** 2026-02-21
**Focus:** What do we need to know to PLAN this phase well?

## 1. BayBE Parameter Decision: Hybrid (Continuous + Categorical)

**Decision:** Use `NumericalContinuousParameter` for all numeric params, `CategoricalParameter` for saturation. This is a HYBRID search space.

**Why:** The existing notebook uses all `NumericalDiscreteParameter`, creating a 147,840-combination Cartesian product (21 x 11 x 10 x 4 x 8 x 2) serialized as ~20MB campaign JSON. Switching to continuous eliminates the full enumeration — BayBE optimizes analytically instead.

**Implementation:**
```python
from baybe.parameters import NumericalContinuousParameter, CategoricalParameter

grind_setting = NumericalContinuousParameter(
    name="grind_setting", bounds=(15.0, 25.0)
)
temperature = NumericalContinuousParameter(
    name="temperature", bounds=(86.0, 96.0)
)
preinfusion_pct = NumericalContinuousParameter(
    name="preinfusion_pct", bounds=(55.0, 100.0)
)
dose_in = NumericalContinuousParameter(
    name="dose_in", bounds=(18.5, 20.0)
)
target_yield = NumericalContinuousParameter(
    name="target_yield", bounds=(36.0, 50.0)
)
saturation = CategoricalParameter(
    name="saturation", values=["yes", "no"], encoding="OHE"
)
```

**Recommender for hybrid space:**
```python
from baybe.recommenders import TwoPhaseMetaRecommender, BotorchRecommender
recommender = TwoPhaseMetaRecommender(recommender=BotorchRecommender())
```

**Rounding recommendations to practical values:**
The service layer should round continuous recommendations to user-actionable precision:
- grind_setting: round to 0.5 (dial has half-marks)
- temperature: round to 1°C (machine PID resolution)
- preinfusion_pct: round to 5% (OPV knob positions)
- dose_in: round to 0.5g (scale precision)
- target_yield: round to 1g (practical accuracy)

**Gotchas:**
- Existing campaign files (discrete) are INCOMPATIBLE with new hybrid search space. No migration needed since we're starting fresh.
- `tolerance` parameter exists on discrete params but not continuous — not needed.
- BayBE 0.14.2 supports hybrid spaces (verified in Coffee_Optimization.py example).

**What to verify:** Create a hybrid campaign, run `recommend()`, check JSON size is <100KB instead of 20MB.

## 2. Dependencies (pyproject.toml)

```toml
[project]
name = "brewflow"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.115",
    "sqlalchemy>=2.0",
    "alembic>=1.18",
    "pydantic-settings>=2.0",
    "baybe==0.14.2",
    "pandas>=2.0",
    "numpy>=1.26,<2.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
    "ruff>=0.4",
]
```

**Critical:** Install CPU-only PyTorch BEFORE baybe:
```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -e ".[dev]"
```

**Do NOT use `baybe[chem,simulation]`** — those extras add rdkit and unnecessary deps (~500MB).

**Lock file:** Use `uv lock` to pin transitive deps (scipy, botorch, gpytorch, etc.) for Docker reproducibility.

## 3. SQLAlchemy Models

Two tables: `beans` and `measurements`. Keep it simple.

```python
# models/bean.py
import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Bean(Base):
    __tablename__ = "beans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    roaster = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    measurements = relationship("Measurement", back_populates="bean")
```

```python
# models/measurement.py
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Measurement(Base):
    __tablename__ = "measurements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False)
    recommendation_id = Column(String, nullable=True, unique=True)  # idempotency token
    
    # BayBE parameters (what was recommended/brewed)
    grind_setting = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    preinfusion_pct = Column(Float, nullable=False)
    dose_in = Column(Float, nullable=False)
    target_yield = Column(Float, nullable=False)
    saturation = Column(String, nullable=False)  # "yes" / "no"
    
    # Target (required)
    taste = Column(Float, nullable=False)
    
    # Metadata (optional)
    extraction_time = Column(Float, nullable=True)  # seconds
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
```

**Key decisions:**
- UUID for bean IDs (avoids slug collisions from Pitfall #12)
- `recommendation_id` for idempotent submissions (Pitfall #4)
- Flavor profile columns added now but optional — avoids a migration later
- No separate flavor_profiles table (Anti-Pattern #5 from ARCHITECTURE.md)
- `is_failed` boolean tracks shot failures

## 4. BayBE Service Layer

```python
# services/optimizer.py
import asyncio
import threading
from pathlib import Path
from baybe.campaign import Campaign

class OptimizerService:
    def __init__(self, campaigns_dir: Path):
        self._campaigns_dir = campaigns_dir
        self._cache: dict[str, Campaign] = {}
        self._lock = threading.Lock()  # BayBE is not thread-safe
    
    def _campaign_path(self, bean_id: str) -> Path:
        return self._campaigns_dir / f"{bean_id}.json"
    
    def get_or_create_campaign(self, bean_id: str) -> Campaign:
        with self._lock:
            if bean_id not in self._cache:
                path = self._campaign_path(bean_id)
                if path.exists():
                    self._cache[bean_id] = Campaign.from_json(path.read_text())
                else:
                    self._cache[bean_id] = self._create_fresh_campaign()
                    self._save_campaign(bean_id)
            return self._cache[bean_id]
    
    async def recommend(self, bean_id: str) -> dict:
        """Run recommendation in thread pool (BayBE blocks for 3-10s)."""
        def _recommend():
            campaign = self.get_or_create_campaign(bean_id)
            with self._lock:
                rec_df = campaign.recommend(batch_size=1)
                self._save_campaign(bean_id)
            return rec_df.iloc[0].to_dict()
        return await asyncio.to_thread(_recommend)
    
    def add_measurement(self, bean_id: str, params: dict, taste: float):
        """Record a measurement. Runs synchronously (fast)."""
        import pandas as pd
        campaign = self.get_or_create_campaign(bean_id)
        measurement = {**params, "taste": taste}
        df = pd.DataFrame([measurement])
        with self._lock:
            campaign.add_measurements(df)
            self._save_campaign(bean_id)
    
    def rebuild_campaign(self, bean_id: str, measurements_df) -> Campaign:
        """Disaster recovery: rebuild from measurements."""
        campaign = self._create_fresh_campaign()
        if not measurements_df.empty:
            baybe_cols = ["grind_setting", "temperature", "preinfusion_pct",
                         "dose_in", "target_yield", "saturation", "taste"]
            campaign.add_measurements(measurements_df[baybe_cols])
        with self._lock:
            self._cache[bean_id] = campaign
            self._save_campaign(bean_id)
        return campaign
```

**Gotchas:**
- `campaign.recommend()` MODIFIES internal state (marks points as recommended). Must save after recommend.
- The lock protects against concurrent FastAPI requests to the same campaign.
- `asyncio.to_thread` pushes the blocking BayBE call to the thread pool so the event loop stays free.

## 5. Docker Multi-Stage Build

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml uv.lock ./

# Install uv
RUN pip install uv

# CPU-only PyTorch first
RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

# Then everything else
RUN uv pip install --system -e .

FROM python:3.11-slim AS runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

ENV CUDA_VISIBLE_DEVICES=""
ENV BREWFLOW_DATA_DIR="/data"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  brewflow:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - brewflow-data:/data
    environment:
      - BREWFLOW_DATA_DIR=/data
    restart: unless-stopped

volumes:
  brewflow-data:
```

**Target image size:** <1.5GB (CPU-only PyTorch saves ~1GB vs default).

**Gotchas:**
- `CUDA_VISIBLE_DEVICES=""` prevents PyTorch GPU warnings in Docker.
- Volume mount at `/data` persists SQLite DB + campaign JSON files.
- `--host 0.0.0.0` required for Docker networking (not just localhost).

## 6. Alembic Setup for SQLite

```bash
alembic init migrations
```

**Critical SQLite gotcha:** SQLite doesn't support `ALTER TABLE DROP COLUMN` or `ALTER TABLE ALTER COLUMN`. Alembic's `render_as_batch=True` handles this by recreating the table.

```python
# migrations/env.py — key change
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,  # Required for SQLite
)
```

**Initial migration:** Auto-generate from models:
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## 7. FastAPI Skeleton

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import engine, Base
from app.services.optimizer import OptimizerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, initialize optimizer
    Base.metadata.create_all(bind=engine)
    app.state.optimizer = OptimizerService(settings.campaigns_dir)
    yield
    # Shutdown: nothing to clean up

app = FastAPI(title="BrewFlow", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
```

```python
# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    data_dir: Path = Path("/data")
    database_url: str = ""
    
    @property
    def db_path(self) -> Path:
        return self.data_dir / "brewflow.db"
    
    @property
    def campaigns_dir(self) -> Path:
        d = self.data_dir / "campaigns"
        d.mkdir(parents=True, exist_ok=True)
        return d
    
    @property
    def effective_database_url(self) -> str:
        return self.database_url or f"sqlite:///{self.db_path}"
    
    model_config = {"env_prefix": "BREWFLOW_"}

settings = Settings()
```

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 8. Testing Strategy

**Test without full BayBE campaign where possible:**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.main import app
from httpx import AsyncClient

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

**Key tests for Phase 1:**
1. **Model tests:** Create bean, create measurement, query relationships
2. **Optimizer service tests:** Create campaign (hybrid), recommend (returns dict with 6 params), add measurement, recommend again (different result), rebuild from measurements
3. **Campaign persistence:** Save campaign JSON, load it back, verify state matches
4. **Docker smoke test:** `docker compose up`, curl health endpoint, verify 200

**BayBE integration test (slow, mark accordingly):**
```python
@pytest.mark.slow
def test_full_optimization_cycle():
    service = OptimizerService(tmp_path / "campaigns")
    rec = await service.recommend("test-bean")
    assert all(k in rec for k in ["grind_setting", "temperature", ...])
    service.add_measurement("test-bean", rec, taste=7.5)
    rec2 = await service.recommend("test-bean")
    # Second recommendation should exist (may or may not differ with 1 point)
```

**Gotcha:** BayBE import takes 3-5s. First test in suite will be slow. Consider a session-scoped fixture that imports BayBE once.

---

## Summary

| Topic | Decision |
|-------|----------|
| Parameters | Hybrid: continuous numeric + categorical saturation |
| Campaign size | <100KB (down from 20MB) |
| Database | SQLite with SQLAlchemy 2.0, Alembic migrations |
| Bean IDs | UUID (not name slugs) |
| Thread safety | threading.Lock around all campaign operations |
| Async recommend | asyncio.to_thread wrapping blocking BayBE call |
| Docker | Multi-stage, CPU-only PyTorch, target <1.5GB |
| Data persistence | Volume mount at /data (SQLite + campaign JSON) |
| Source of truth | Measurements in SQLite; campaigns rebuildable |
