"""Tests for brew router — optimization loop: recommend, record, repeat best."""

import pytest
from unittest.mock import AsyncMock, patch
import uuid

from app.main import app
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.models.pending_recommendation import PendingRecommendation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    """Create a sample bean."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
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
        "preinfusion_pressure_pct": 75.0,
        "dose_in": 19.0,
        "target_yield": 40.0,
        "saturation": "yes",
    }


def _seed_measurement(
    db_session, bean_id: str, taste: float = 8.0, rec_id: str | None = None
) -> Measurement:
    """Insert a measurement directly into the DB."""
    m = Measurement(
        bean_id=bean_id,
        recommendation_id=rec_id or str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
        is_failed=False,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# GET /brew — no active bean
# ---------------------------------------------------------------------------


def test_brew_index_no_active_bean_shows_prompt(client):
    """GET /brew without active bean cookie -> shows pick-a-bean prompt."""
    response = client.get("/brew")
    assert response.status_code == 200
    assert "Pick a bean" in response.text
    assert "/beans" in response.text


# ---------------------------------------------------------------------------
# GET /brew — with active bean
# ---------------------------------------------------------------------------


def test_brew_index_with_active_bean(active_client):
    """GET /brew with active bean shows action buttons."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Get Recommendation" in response.text
    assert "BeanBay" in response.text


def test_brew_index_no_repeat_best_without_measurements(active_client):
    """GET /brew without measurements does NOT show Repeat Best."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Repeat Best" not in response.text


def test_brew_index_shows_repeat_best_with_measurements(active_client, sample_bean, db_session):
    """GET /brew with measurements shows Repeat Best button."""
    _seed_measurement(db_session, sample_bean.id)
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Repeat Best" in response.text


# ---------------------------------------------------------------------------
# POST /brew/recommend
# ---------------------------------------------------------------------------


def test_trigger_recommend_no_active_bean(client):
    """POST /brew/recommend without active bean -> redirect to /beans."""
    response = client.post("/brew/recommend", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_trigger_recommend_generates_and_redirects(active_client):
    """POST /brew/recommend generates recommendation, redirects to display page."""
    fake_rec = _make_rec()
    fake_insights = {
        "phase": "random",
        "phase_label": "Random exploration",
        "explanation": "Exploring randomly — building initial understanding of the parameter space.",
        "predicted_mean": None,
        "predicted_std": None,
        "predicted_range": None,
        "shot_count": 0,
    }

    with patch.object(
        app.state.__class__,
        "__getattribute__",
        side_effect=AttributeError,
    ):
        pass  # just checking the mock approach compiles

    # Patch the optimizer on app.state directly
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock(return_value=fake_rec)
    mock_optimizer.get_recommendation_insights = MagicMock(return_value=fake_insights)
    mock_optimizer.get_transfer_metadata = MagicMock(return_value=None)
    app.state.optimizer = mock_optimizer

    response = active_client.post("/brew/recommend", follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/brew/recommend/")
    # The rec_id should be in the URL
    assert fake_rec["recommendation_id"] in location


# ---------------------------------------------------------------------------
# GET /brew/recommend/{recommendation_id}
# ---------------------------------------------------------------------------


def test_show_recommendation_displays_params(active_client, sample_bean, db_session):
    """GET /brew/recommend/{id} shows recipe params in large display."""
    rec_id = str(uuid.uuid4())
    rec = _make_rec(rec_id)

    # Seed pending recommendation in DB
    db_session.add(PendingRecommendation(recommendation_id=rec_id, recommendation_data=rec))
    db_session.commit()

    response = active_client.get(f"/brew/recommend/{rec_id}")
    assert response.status_code == 200
    # 6 params visible
    assert "20.0" in response.text  # grind_setting
    assert "93" in response.text  # temperature
    assert "75" in response.text  # preinfusion_pressure_pct
    assert "19" in response.text  # dose_in
    assert "40" in response.text  # target_yield
    assert "yes" in response.text  # saturation
    # Brew ratio
    assert "1:2.1" in response.text


def test_show_recommendation_expired_redirects(active_client):
    """GET /brew/recommend/{unknown_id} -> redirect back to /brew."""
    response = active_client.get(f"/brew/recommend/{uuid.uuid4()}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"


# ---------------------------------------------------------------------------
# POST /brew/record
# ---------------------------------------------------------------------------


def _record_payload(
    rec_id: str, taste: float = 8.0, is_failed: str | None = None, **kwargs
) -> dict:
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "preinfusion_pressure_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": str(taste),
    }
    if is_failed is not None:
        payload["is_failed"] = is_failed
    payload.update(kwargs)
    return payload


def test_record_measurement_saves_and_redirects(active_client, sample_bean, db_session):
    """POST /brew/record with valid data saves measurement, redirects to /brew."""
    rec_id = str(uuid.uuid4())

    # Patch optimizer.add_measurement so we don't need BayBE
    # add_measurement is synchronous, so use MagicMock (not AsyncMock)
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    response = active_client.post(
        "/brew/record", data=_record_payload(rec_id, taste=8.0), follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"

    # Verify saved
    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.taste == 8.0
    assert m.is_failed is False
    assert m.bean_id == sample_bean.id


def test_record_failed_shot_sets_taste_to_1(active_client, sample_bean, db_session):
    """POST /brew/record with is_failed=true -> auto-sets taste to 1."""
    rec_id = str(uuid.uuid4())

    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    response = active_client.post(
        "/brew/record",
        data=_record_payload(rec_id, taste=7.5, is_failed="true"),
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.taste == 1.0
    assert m.is_failed is True


def test_record_measurement_deduplication(active_client, sample_bean, db_session):
    """Recording the same recommendation_id twice only stores one measurement."""
    rec_id = str(uuid.uuid4())

    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    payload = _record_payload(rec_id, taste=8.0)
    active_client.post("/brew/record", data=payload, follow_redirects=False)
    active_client.post(
        "/brew/record", data=payload, follow_redirects=False
    )  # second time — should be ignored

    db_session.expire_all()
    count = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).count()
    assert count == 1


def test_record_measurement_no_active_bean(client):
    """POST /brew/record without active bean -> redirect to /beans."""
    response = client.post(
        "/brew/record", data=_record_payload(str(uuid.uuid4())), follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


# ---------------------------------------------------------------------------
# GET /brew/best
# ---------------------------------------------------------------------------


def test_show_best_no_measurements(active_client, sample_bean):
    """GET /brew/best with no measurements -> empty state shown."""
    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "No shots yet" in response.text


def test_show_best_shows_highest_rated(active_client, sample_bean, db_session):
    """GET /brew/best shows the highest-tasting (non-failed) measurement."""
    _seed_measurement(db_session, sample_bean.id, taste=6.0)
    _seed_measurement(db_session, sample_bean.id, taste=9.0)  # best
    _seed_measurement(db_session, sample_bean.id, taste=7.5)

    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "9.0" in response.text
    assert "Best Recipe" in response.text


def test_show_best_excludes_failed_shots(active_client, sample_bean, db_session):
    """GET /brew/best ignores failed shots when computing the best."""
    # Only measurement is a failed shot
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=1.0,
        is_failed=True,
    )
    db_session.add(m)
    db_session.commit()

    response = active_client.get("/brew/best")
    assert response.status_code == 200
    assert "No shots yet" in response.text


def test_show_best_displays_brew_ratio(active_client, sample_bean, db_session):
    """GET /brew/best shows the dose:yield brew ratio."""
    _seed_measurement(db_session, sample_bean.id, taste=8.5)
    response = active_client.get("/brew/best")
    assert response.status_code == 200
    # dose_in=19, target_yield=40 -> ratio ~ 1:2.1
    assert "1:2.1" in response.text


def test_show_best_no_active_bean(client):
    """GET /brew/best without active bean -> redirect to /beans."""
    response = client.get("/brew/best", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


# ---------------------------------------------------------------------------
# GET /brew/best — fresh UUID per visit (deduplication fix)
# ---------------------------------------------------------------------------


def test_show_best_recommendation_id_is_uuid(active_client, sample_bean, db_session):
    """GET /brew/best returns a valid UUID as recommendation_id in the form."""
    _seed_measurement(db_session, sample_bean.id, taste=8.0)

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


def test_show_best_brew_again_creates_new_measurement(active_client, sample_bean, db_session):
    """Brew Again on /brew/best creates a new measurement each visit (dedup only blocks same-page double-submit)."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    _seed_measurement(db_session, sample_bean.id, taste=8.0)

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
        "preinfusion_pressure_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": "9.5",
    }
    r = active_client.post("/brew/record", data=payload1, follow_redirects=False)
    assert r.status_code == 303

    # DB should now have 2 measurements
    db_session.expire_all()
    count = db_session.query(Measurement).filter(Measurement.bean_id == sample_bean.id).count()
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
    r2 = active_client.post("/brew/record", data=payload2, follow_redirects=False)
    assert r2.status_code == 303

    # DB should now have 3 measurements
    db_session.expire_all()
    count = db_session.query(Measurement).filter(Measurement.bean_id == sample_bean.id).count()
    assert count == 3


# ---------------------------------------------------------------------------
# Feedback panel — notes, flavor dimensions, flavor tags
# ---------------------------------------------------------------------------


def test_record_with_notes(active_client, sample_bean, db_session):
    """POST /brew/record with notes field saves notes to DB."""
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    payload = _record_payload(rec_id, taste=7.5, notes="Nice fruity finish, slightly sharp")
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.notes == "Nice fruity finish, slightly sharp"


def test_record_with_flavor_dimensions(active_client, sample_bean, db_session):
    """POST /brew/record with flavor dimension sliders saves only touched values."""
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    # Only acidity and sweetness submitted (simulating touched sliders)
    payload = _record_payload(rec_id, taste=8.0, acidity="3", sweetness="4")
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.acidity == 3.0
    assert m.sweetness == 4.0
    # Other dimensions not submitted — should be None
    assert m.body is None
    assert m.bitterness is None
    assert m.aroma is None
    assert m.intensity is None


def test_record_with_flavor_tags(active_client, sample_bean, db_session):
    """POST /brew/record with flavor_tags saves as JSON list; max 10 enforced."""
    import json as _json
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    # Submit 3 tags as comma-separated string
    payload = _record_payload(rec_id, taste=8.5, flavor_tags="chocolate,citrus,fruity")
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.flavor_tags is not None
    parsed = _json.loads(m.flavor_tags)
    assert parsed == ["chocolate", "citrus", "fruity"]

    # Test max 10 enforced — submit 12 tags
    rec_id2 = str(uuid.uuid4())
    all_tags = "a,b,c,d,e,f,g,h,i,j,k,l"  # 12 tags
    payload2 = _record_payload(rec_id2, taste=7.0, flavor_tags=all_tags)
    active_client.post("/brew/record", data=payload2, follow_redirects=False)

    db_session.expire_all()
    m2 = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id2).first()
    assert m2 is not None
    parsed2 = _json.loads(m2.flavor_tags)
    assert len(parsed2) == 10  # capped at 10


# ---------------------------------------------------------------------------
# Recommendation insights — explore/exploit explanation
# ---------------------------------------------------------------------------


def test_recommendation_shows_insights(active_client, sample_bean, db_session):
    """GET /brew/recommend/{id} shows phase_label from insights in the response."""
    rec_id = str(uuid.uuid4())
    rec = _make_rec(rec_id)
    rec["insights"] = {
        "phase": "random",
        "phase_label": "Random exploration",
        "explanation": "Exploring randomly — building initial understanding of the parameter space.",
        "predicted_mean": None,
        "predicted_std": None,
        "predicted_range": None,
        "shot_count": 0,
    }

    # Seed pending recommendation in DB
    db_session.add(PendingRecommendation(recommendation_id=rec_id, recommendation_data=rec))
    db_session.commit()

    response = active_client.get(f"/brew/recommend/{rec_id}")
    assert response.status_code == 200
    assert "Random exploration" in response.text
    assert "Exploring randomly" in response.text


def test_recommendation_insights_no_prediction_first_shot(active_client, sample_bean, db_session):
    """First recommendation (random phase) shows no predicted_range in response."""
    rec_id = str(uuid.uuid4())
    rec = _make_rec(rec_id)
    rec["insights"] = {
        "phase": "random",
        "phase_label": "Random exploration",
        "explanation": "Exploring randomly — building initial understanding of the parameter space.",
        "predicted_mean": None,
        "predicted_std": None,
        "predicted_range": None,
        "shot_count": 0,
    }

    # Seed pending recommendation in DB
    db_session.add(PendingRecommendation(recommendation_id=rec_id, recommendation_data=rec))
    db_session.commit()

    response = active_client.get(f"/brew/recommend/{rec_id}")
    assert response.status_code == 200
    # No predicted taste range shown for first shot
    assert "Expected taste" not in response.text
    assert "insight-prediction" not in response.text


# ---------------------------------------------------------------------------
# Manual input — bean picker, mode buttons, is_manual field
# ---------------------------------------------------------------------------


def test_brew_index_shows_manual_input_button(active_client):
    """GET /brew with active bean -> contains 'Manual Input' and '/brew/manual'."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "Manual Input" in response.text
    assert "/brew/manual" in response.text


def test_brew_index_shows_bean_picker(active_client, sample_bean):
    """GET /brew with active bean -> contains <select and the active bean name."""
    response = active_client.get("/brew")
    assert response.status_code == 200
    assert "<select" in response.text
    assert sample_bean.name in response.text


def test_record_manual_measurement(active_client, sample_bean, db_session):
    """POST /brew/record with is_manual='true' -> is_manual=True saved in DB."""
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    payload = _record_payload(rec_id, taste=7.5, is_manual="true")
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.is_manual is True


def test_record_manual_rejects_out_of_range(active_client, sample_bean, db_session):
    """POST /brew/record with is_manual='true' and grind_setting=5.0 -> 422."""
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    # grind_setting=5.0 is outside DEFAULT_BOUNDS (15.0, 25.0)
    payload = _record_payload(rec_id, taste=7.0, is_manual="true")
    payload["grind_setting"] = "5.0"
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 422

    data = response.json()
    assert data["error"] == "Parameters out of range"
    assert any(v["param"] == "grind_setting" for v in data["violations"])

    # Verify nothing was saved
    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is None


def test_record_non_manual_allows_any_values(active_client, sample_bean, db_session):
    """POST /brew/record without is_manual flag allows out-of-range grind_setting=5.0."""
    from unittest.mock import MagicMock

    rec_id = str(uuid.uuid4())
    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    # grind_setting=5.0 is outside DEFAULT_BOUNDS but no is_manual flag -> should save normally
    payload = _record_payload(rec_id, taste=7.0)
    payload["grind_setting"] = "5.0"
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.grind_setting == 5.0


# ---------------------------------------------------------------------------
# GET /brew/manual — manual brew form
# ---------------------------------------------------------------------------


def test_manual_page_loads_with_active_bean(active_client):
    """GET /brew/manual with active bean -> 200 and form present."""
    response = active_client.get("/brew/manual")
    assert response.status_code == 200
    assert "Manual Brew" in response.text
    assert "Submit Manual Brew" in response.text
    assert 'name="is_manual"' in response.text
    assert 'value="true"' in response.text


def test_manual_page_no_active_bean_redirects(client):
    """GET /brew/manual without active bean -> redirect to /beans."""
    response = client.get("/brew/manual", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_manual_page_prefills_from_best(active_client, sample_bean, db_session):
    """GET /brew/manual with measurements -> pre-fills from best measurement."""
    _seed_measurement(db_session, sample_bean.id, taste=9.0)
    response = active_client.get("/brew/manual")
    assert response.status_code == 200
    # The best measurement has grind_setting=20.0, temperature=93.0
    assert "20.0" in response.text
    assert "93" in response.text


def test_manual_page_prefills_midpoint_no_measurements(active_client, sample_bean):
    """GET /brew/manual with no measurements -> pre-fills midpoint of default bounds."""
    response = active_client.get("/brew/manual")
    assert response.status_code == 200
    # grind_setting midpoint of (15, 25) = 20.0
    assert "20.0" in response.text
    # temperature midpoint of (86, 96) = 91
    assert "91" in response.text


def test_record_manual_brew_end_to_end(active_client, sample_bean, db_session):
    """POST /brew/record from manual form saves with is_manual=True and redirects."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "is_manual": "true",
        "grind_setting": "20.0",
        "temperature": "93.0",
        "preinfusion_pressure_pct": "75.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "saturation": "yes",
        "taste": "8.0",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.is_manual is True
    assert m.taste == 8.0


def test_manual_page_shows_bean_bounds(active_client, sample_bean):
    """GET /brew/manual -> shows default parameter bounds in form."""
    response = active_client.get("/brew/manual")
    assert response.status_code == 200
    # Default grind bounds: 15–25
    assert "15" in response.text
    assert "25" in response.text
    # Default temperature bounds: 86–96
    assert "86" in response.text
    assert "96" in response.text


# ---------------------------------------------------------------------------
# POST /brew/extend-ranges
# ---------------------------------------------------------------------------


def test_extend_ranges_updates_parameter_overrides(active_client, sample_bean, db_session):
    """POST /brew/extend-ranges with new bounds -> bean.parameter_overrides updated."""
    response = active_client.post(
        "/brew/extend-ranges",
        data={"grind_setting_min": "13", "grind_setting_max": "28"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    db_session.expire_all()
    db_session.refresh(sample_bean)
    overrides = sample_bean.parameter_overrides
    assert overrides is not None
    assert "grind_setting" in overrides
    assert overrides["grind_setting"]["min"] == 13.0
    assert overrides["grind_setting"]["max"] == 28.0


def test_extend_ranges_preserves_existing_overrides(active_client, sample_bean, db_session):
    """POST /brew/extend-ranges with grind changes preserves existing temperature overrides."""
    # Pre-seed temperature overrides
    sample_bean.parameter_overrides = {"temperature": {"min": 84.0, "max": 98.0}}
    db_session.commit()

    response = active_client.post(
        "/brew/extend-ranges",
        data={"grind_setting_min": "13", "grind_setting_max": "28"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    db_session.refresh(sample_bean)
    overrides = sample_bean.parameter_overrides
    assert "temperature" in overrides
    assert overrides["temperature"]["min"] == 84.0
    assert overrides["temperature"]["max"] == 98.0
    assert "grind_setting" in overrides
    assert overrides["grind_setting"]["min"] == 13.0
    assert overrides["grind_setting"]["max"] == 28.0


def test_extend_ranges_no_active_bean_redirects(client):
    """POST /brew/extend-ranges without active bean -> 303 redirect to /beans."""
    response = client.post(
        "/brew/extend-ranges",
        data={"grind_setting_min": "13", "grind_setting_max": "28"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_manual_form_has_range_data_attributes(active_client, sample_bean):
    """GET /brew/manual -> number inputs have data-min, data-max, data-param attributes."""
    response = active_client.get("/brew/manual")
    assert response.status_code == 200
    html = response.text
    # data-min and data-max should appear for each parameter number input
    assert 'data-min="15' in html or 'data-min="15.0' in html  # grind_setting default min
    assert 'data-max="25' in html or 'data-max="25.0' in html  # grind_setting default max
    # Phase 20 Tier-1 active params (preinfusion_pressure_pct is legacy — excluded from new campaigns)
    assert 'data-param="grind_setting"' in html
    assert 'data-param="temperature"' in html
    assert 'data-param="dose_in"' in html
    assert 'data-param="target_yield"' in html
    # Number inputs should NOT have min/max HTML attributes on param-number inputs
    # (sliders still have them; number inputs use data-min/data-max instead)
    assert 'id="is_manual_flag"' in html


# ---------------------------------------------------------------------------
# Brewer context wiring — brewer passed to optimizer, outdated detection
# ---------------------------------------------------------------------------


def test_trigger_recommend_passes_brewer_to_optimizer(active_client):
    """POST /brew/recommend with no active setup passes brewer=None to optimizer."""
    from unittest.mock import MagicMock

    fake_rec = _make_rec()
    fake_insights = {
        "phase": "random",
        "phase_label": "Random exploration",
        "explanation": "Exploring.",
        "predicted_mean": None,
        "predicted_std": None,
        "predicted_range": None,
        "shot_count": 0,
    }

    mock_optimizer = MagicMock()
    mock_optimizer.recommend = AsyncMock(return_value=fake_rec)
    mock_optimizer.get_recommendation_insights = MagicMock(return_value=fake_insights)
    mock_optimizer.get_transfer_metadata = MagicMock(return_value=None)
    mock_optimizer.is_campaign_outdated = MagicMock(return_value=False)
    mock_optimizer.was_rebuild_declined = MagicMock(return_value=False)
    app.state.optimizer = mock_optimizer

    # No active setup cookie → brewer=None
    response = active_client.post("/brew/recommend", follow_redirects=False)
    assert response.status_code == 303

    # Verify brewer=None was passed to recommend
    mock_optimizer.recommend.assert_awaited_once()
    _, kwargs = mock_optimizer.recommend.call_args
    assert "brewer" in kwargs
    assert kwargs["brewer"] is None


def test_trigger_recommend_outdated_campaign_redirects_to_prompt(active_client):
    """POST /brew/recommend when campaign is outdated and not declined → redirect to prompt page."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.is_campaign_outdated = MagicMock(return_value=True)
    mock_optimizer.was_rebuild_declined = MagicMock(return_value=False)
    # recommend should NOT be called
    mock_optimizer.recommend = AsyncMock()
    app.state.optimizer = mock_optimizer

    response = active_client.post("/brew/recommend", follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    assert "/brew/campaign-outdated" in location

    # Verify recommend was never called
    mock_optimizer.recommend.assert_not_awaited()


def test_trigger_recommend_outdated_campaign_declined_proceeds_normally(active_client):
    """POST /brew/recommend when campaign outdated but rebuild_declined >= 2 → proceeds normally."""
    from unittest.mock import MagicMock

    fake_rec = _make_rec()
    fake_insights = {
        "phase": "random",
        "phase_label": "Random exploration",
        "explanation": "Exploring.",
        "predicted_mean": None,
        "predicted_std": None,
        "predicted_range": None,
        "shot_count": 0,
    }

    mock_optimizer = MagicMock()
    mock_optimizer.is_campaign_outdated = MagicMock(return_value=True)
    mock_optimizer.was_rebuild_declined = MagicMock(return_value=True)  # permanently declined
    mock_optimizer.recommend = AsyncMock(return_value=fake_rec)
    mock_optimizer.get_recommendation_insights = MagicMock(return_value=fake_insights)
    mock_optimizer.get_transfer_metadata = MagicMock(return_value=None)
    app.state.optimizer = mock_optimizer

    response = active_client.post("/brew/recommend", follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    # Should redirect to recommendation page, NOT to campaign-outdated
    assert "/brew/recommend/" in location
    assert "campaign-outdated" not in location


def test_campaign_outdated_page_renders(active_client):
    """GET /brew/campaign-outdated renders with new_params list."""
    response = active_client.get(
        "/brew/campaign-outdated?campaign_key=abc__espresso__None&method=espresso"
    )
    assert response.status_code == 200
    assert "Campaign Update" in response.text
    assert "Rebuild Campaign" in response.text
    assert "Skip for Now" in response.text


def test_rebuild_campaign_route_calls_accept_rebuild_and_redirects(active_client):
    """POST /brew/rebuild-campaign calls accept_rebuild and redirects to /brew/recommend."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.accept_rebuild = MagicMock(return_value=None)
    app.state.optimizer = mock_optimizer

    response = active_client.post(
        "/brew/rebuild-campaign",
        data={"campaign_key": "abc__espresso__None", "method": "espresso"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/brew/recommend"

    mock_optimizer.accept_rebuild.assert_called_once()
    call_args = mock_optimizer.accept_rebuild.call_args
    # campaign_key is passed as first positional arg
    assert call_args[0][0] == "abc__espresso__None"


def test_decline_rebuild_route_calls_decline_and_redirects(active_client):
    """POST /brew/decline-rebuild calls decline_rebuild and redirects to /brew."""
    from unittest.mock import MagicMock

    mock_optimizer = MagicMock()
    mock_optimizer.decline_rebuild = MagicMock(return_value=None)
    app.state.optimizer = mock_optimizer

    response = active_client.post(
        "/brew/decline-rebuild",
        data={"campaign_key": "abc__espresso__None"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/brew"

    mock_optimizer.decline_rebuild.assert_called_once_with("abc__espresso__None")


# ---------------------------------------------------------------------------
# Phase 20 Plan 03 — param_hints and PARAM_HINTS coverage
# ---------------------------------------------------------------------------


def test_show_recommendation_context_includes_param_hints(active_client, sample_bean, db_session):
    """GET /brew/recommend/{id} response includes param hint text for Phase 20 params."""
    rec_id = str(uuid.uuid4())
    rec = _make_rec(rec_id)

    db_session.add(PendingRecommendation(recommendation_id=rec_id, recommendation_data=rec))
    db_session.commit()

    response = active_client.get(f"/brew/recommend/{rec_id}")
    assert response.status_code == 200
    # The route passes param_hints to the template; the template renders data-param-hint attrs
    # on hint cards. Verify the hints container is rendered (even if no hints are visible
    # without localStorage context, the container + data attrs are present).
    assert "param-hints-container" in response.text


def test_param_hints_dict_covers_phase20_params():
    """PARAM_HINTS dict in brew.py contains entries for all Phase 20 espresso params."""
    from app.routers.brew import PARAM_HINTS

    phase20_params = [
        "preinfusion_time",
        "preinfusion_pressure",
        "brew_pressure",
        "pressure_profile",
        "flow_rate",
        "bloom_pause",
        "temp_profile",
        "brew_mode",
        "saturation",
    ]
    for param in phase20_params:
        assert param in PARAM_HINTS, f"PARAM_HINTS missing hint for '{param}'"
        assert len(PARAM_HINTS[param]) > 10, f"Hint for '{param}' too short: {PARAM_HINTS[param]!r}"


def test_show_best_context_includes_param_defs(active_client, sample_bean, db_session):
    """GET /brew/best passes param_defs to template (dynamic hidden inputs)."""
    _seed_measurement(db_session, sample_bean.id, taste=8.0)

    response = active_client.get("/brew/best")
    assert response.status_code == 200
    # Dynamic loop produces hidden inputs driven by param_defs
    assert 'name="grind_setting"' in response.text
    assert 'name="temperature"' in response.text
    assert 'name="dose_in"' in response.text
