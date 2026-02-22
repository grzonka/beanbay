"""Tests for brew router — optimization loop: recommend, record, repeat best."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import uuid

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.bean import Bean
from app.models.measurement import Measurement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app, follow_redirects=False)


@pytest.fixture()
def db():
    """Direct DB session for test setup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_bean(db):
    """Create a sample bean."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db.add(bean)
    db.commit()
    db.refresh(bean)
    return bean


@pytest.fixture()
def active_client(client, sample_bean):
    """Client with active bean cookie set."""
    client.cookies.set("active_bean_id", sample_bean.id)
    return client


def _make_rec(rec_id: str | None = None) -> dict:
    """Build a realistic fake recommendation dict."""
    return {
        "recommendation_id": rec_id or str(uuid.uuid4()),
        "grind_setting": 20.0,
        "temperature": 93.0,
        "preinfusion_pct": 75.0,
        "dose_in": 19.0,
        "target_yield": 40.0,
        "saturation": "yes",
    }


def _seed_measurement(
    db, bean_id: str, taste: float = 8.0, rec_id: str | None = None
) -> Measurement:
    """Insert a measurement directly into the DB."""
    m = Measurement(
        bean_id=bean_id,
        recommendation_id=rec_id or str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
        is_failed=False,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# GET /brew — no active bean
# ---------------------------------------------------------------------------


def test_brew_index_no_active_bean_redirects(client):
    """GET /brew without active bean cookie → redirect to /beans."""
    response = client.get("/brew")
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


# ---------------------------------------------------------------------------
# GET /brew — with active bean
# ---------------------------------------------------------------------------


def test_brew_index_with_active_bean(active_client):
    """GET /brew with active bean shows action buttons."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Get Recommendation" in response.text
    assert "BrewFlow" in response.text


def test_brew_index_no_repeat_best_without_measurements(active_client):
    """GET /brew without measurements does NOT show Repeat Best."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Repeat Best" not in response.text


def test_brew_index_shows_repeat_best_with_measurements(active_client, sample_bean, db):
    """GET /brew with measurements shows Repeat Best button."""
    _seed_measurement(db, sample_bean.id)
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Repeat Best" in response.text


# ---------------------------------------------------------------------------
# POST /brew/recommend
# ---------------------------------------------------------------------------


def test_trigger_recommend_no_active_bean(client):
    """POST /brew/recommend without active bean → redirect to /beans."""
    response = client.post("/brew/recommend")
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_trigger_recommend_generates_and_redirects(active_client):
    """POST /brew/recommend generates recommendation, redirects to display page."""
    fake_rec = _make_rec()

    with patch.object(
        app.state.__class__,
        "__getattribute__",
        side_effect=AttributeError,
    ):
        pass  # just checking the mock approach compiles

    # Patch the optimizer on app.state directly
    mock_optimizer = AsyncMock()
    mock_optimizer.recommend = AsyncMock(return_value=fake_rec)
    app.state.optimizer = mock_optimizer

    response = active_client.post("/brew/recommend")
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/brew/recommend/")
    # The rec_id should be in the URL
    assert fake_rec["recommendation_id"] in location


# ---------------------------------------------------------------------------
# GET /brew/recommend/{recommendation_id}
# ---------------------------------------------------------------------------


def test_show_recommendation_displays_params(active_client, sample_bean):
    """GET /brew/recommend/{id} shows recipe params in large display."""
    rec_id = str(uuid.uuid4())
    rec = _make_rec(rec_id)

    # Seed pending_recommendations in app state
    if not hasattr(app.state, "pending_recommendations"):
        app.state.pending_recommendations = {}
    app.state.pending_recommendations[rec_id] = rec

    response = active_client.get(f"/brew/recommend/{rec_id}")
    assert response.status_code == 200
    # 6 params visible
    assert "20.0" in response.text  # grind_setting
    assert "93" in response.text  # temperature
    assert "75" in response.text  # preinfusion_pct
    assert "19" in response.text  # dose_in
    assert "40" in response.text  # target_yield
    assert "yes" in response.text  # saturation
    # Brew ratio
    assert "1:2.1" in response.text


def test_show_recommendation_expired_redirects(active_client):
    """GET /brew/recommend/{unknown_id} → redirect back to /brew."""
    response = active_client.get(f"/brew/recommend/{uuid.uuid4()}")
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"


# ---------------------------------------------------------------------------
# POST /brew/record
# ---------------------------------------------------------------------------


def _record_payload(rec_id: str, taste: float = 8.0, is_failed: str | None = None) -> dict:
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "preinfusion_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": str(taste),
    }
    if is_failed is not None:
        payload["is_failed"] = is_failed
    return payload


def test_record_measurement_saves_and_redirects(active_client, sample_bean, db):
    """POST /brew/record with valid data saves measurement, redirects to /brew."""
    rec_id = str(uuid.uuid4())

    # Patch optimizer.add_measurement so we don't need BayBE
    # add_measurement is synchronous, so use MagicMock (not AsyncMock)
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    response = active_client.post("/brew/record", data=_record_payload(rec_id, taste=8.0))
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"

    # Verify saved
    db.expire_all()
    m = db.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.taste == 8.0
    assert m.is_failed is False
    assert m.bean_id == sample_bean.id


def test_record_failed_shot_sets_taste_to_1(active_client, sample_bean, db):
    """POST /brew/record with is_failed=true → auto-sets taste to 1."""
    rec_id = str(uuid.uuid4())

    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    response = active_client.post(
        "/brew/record",
        data=_record_payload(rec_id, taste=7.5, is_failed="true"),
    )
    assert response.status_code == 303

    db.expire_all()
    m = db.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.taste == 1.0
    assert m.is_failed is True


def test_record_measurement_deduplication(active_client, sample_bean, db):
    """Recording the same recommendation_id twice only stores one measurement."""
    rec_id = str(uuid.uuid4())

    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    payload = _record_payload(rec_id, taste=8.0)
    active_client.post("/brew/record", data=payload)
    active_client.post("/brew/record", data=payload)  # second time — should be ignored

    db.expire_all()
    count = db.query(Measurement).filter(Measurement.recommendation_id == rec_id).count()
    assert count == 1


def test_record_measurement_no_active_bean(client):
    """POST /brew/record without active bean → redirect to /beans."""
    response = client.post("/brew/record", data=_record_payload(str(uuid.uuid4())))
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


# ---------------------------------------------------------------------------
# GET /brew/best
# ---------------------------------------------------------------------------


def test_show_best_no_measurements(active_client, sample_bean):
    """GET /brew/best with no measurements → empty state shown."""
    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "No shots yet" in response.text


def test_show_best_shows_highest_rated(active_client, sample_bean, db):
    """GET /brew/best shows the highest-tasting (non-failed) measurement."""
    _seed_measurement(db, sample_bean.id, taste=6.0)
    _seed_measurement(db, sample_bean.id, taste=9.0)  # best
    _seed_measurement(db, sample_bean.id, taste=7.5)

    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "9.0" in response.text
    assert "Best Recipe" in response.text


def test_show_best_excludes_failed_shots(active_client, sample_bean, db):
    """GET /brew/best ignores failed shots when computing the best."""
    # Only measurement is a failed shot
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=1.0,
        is_failed=True,
    )
    db.add(m)
    db.commit()

    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "No shots yet" in response.text


def test_show_best_displays_brew_ratio(active_client, sample_bean, db):
    """GET /brew/best shows the dose:yield brew ratio."""
    _seed_measurement(db, sample_bean.id, taste=8.5)
    response = active_client.get("/brew/best")
    assert response.status_code == 200
    # dose_in=19, target_yield=40 → ratio ≈ 1:2.1
    assert "1:2.1" in response.text


def test_show_best_no_active_bean(client):
    """GET /brew/best without active bean → redirect to /beans."""
    response = client.get("/brew/best")
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


# ---------------------------------------------------------------------------
# GET /brew/best — fresh UUID per visit (deduplication fix)
# ---------------------------------------------------------------------------


def test_show_best_recommendation_id_is_uuid(active_client, sample_bean, db):
    """GET /brew/best returns a valid UUID as recommendation_id in the form."""
    _seed_measurement(db, sample_bean.id, taste=8.0)

    response = active_client.get("/brew/best")
    assert response.status_code == 200

    # Extract recommendation_id from the hidden input
    import re

    match = re.search(r'name="recommendation_id"\s+value="([^"]+)"', response.text)
    assert match is not None, "recommendation_id hidden input not found in page"
    extracted_id = match.group(1)

    # Assert it's a valid UUID (should not raise)
    parsed = uuid.UUID(extracted_id)
    assert str(parsed) == extracted_id


def test_show_best_brew_again_creates_new_measurement(active_client, sample_bean, db):
    """Brew Again on /brew/best creates a new measurement each visit (dedup only blocks same-page double-submit)."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    _seed_measurement(db, sample_bean.id, taste=8.0)

    import re

    # --- First visit ---
    response1 = active_client.get("/brew/best")
    assert response1.status_code == 200
    match1 = re.search(r'name="recommendation_id"\s+value="([^"]+)"', response1.text)
    assert match1 is not None
    rec_id_1 = match1.group(1)

    # Submit "Brew Again" with first visit's recommendation_id
    payload1 = {
        "recommendation_id": rec_id_1,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "preinfusion_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": "9.5",
    }
    r = active_client.post("/brew/record", data=payload1)
    assert r.status_code == 303

    # DB should now have 2 measurements
    db.expire_all()
    count = db.query(Measurement).filter(Measurement.bean_id == sample_bean.id).count()
    assert count == 2

    # --- Second visit ---
    response2 = active_client.get("/brew/best")
    assert response2.status_code == 200
    match2 = re.search(r'name="recommendation_id"\s+value="([^"]+)"', response2.text)
    assert match2 is not None
    rec_id_2 = match2.group(1)

    # The new recommendation_id must differ from the first
    assert rec_id_2 != rec_id_1

    # Submit "Brew Again" with second visit's recommendation_id
    payload2 = {**payload1, "recommendation_id": rec_id_2, "taste": "9.0"}
    r2 = active_client.post("/brew/record", data=payload2)
    assert r2.status_code == 303

    # DB should now have 3 measurements
    db.expire_all()
    count = db.query(Measurement).filter(Measurement.bean_id == sample_bean.id).count()
    assert count == 3
