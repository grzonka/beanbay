"""Tests for history router — shot history list with filters and shot detail/edit."""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.models.bean import Bean
from app.models.measurement import Measurement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    """Create a sample bean."""
    bean = Bean(name="Ethiopian Yirgacheffe", roaster="Onyx", origin="Ethiopia")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


@pytest.fixture()
def second_bean(db_session):
    """Create a second sample bean."""
    bean = Bean(name="Colombian Huila", roaster="Counter Culture", origin="Colombia")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


def _seed_shot(
    db_session,
    bean_id: str,
    taste: float = 8.0,
    is_failed: bool = False,
    notes: str | None = None,
    created_at: datetime | None = None,
    is_manual: bool = False,
) -> Measurement:
    """Seed a measurement directly into the DB."""
    m = Measurement(
        bean_id=bean_id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
        is_failed=is_failed,
        is_manual=is_manual,
        notes=notes,
    )
    if created_at is not None:
        m.created_at = created_at
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_history_page_loads(client, sample_bean, db_session):
    """GET /history returns 200 and contains page title."""
    _seed_shot(db_session, sample_bean.id)
    response = client.get("/history")
    assert response.status_code == 200
    assert "Brew History" in response.text


def test_history_shows_shots_reverse_chronological(client, sample_bean, db_session):
    """Shots appear in newest-first order."""
    now = datetime.utcnow()
    shot_old = _seed_shot(
        db_session, sample_bean.id, taste=5.0, created_at=now - timedelta(hours=2)
    )
    shot_mid = _seed_shot(
        db_session, sample_bean.id, taste=7.0, created_at=now - timedelta(hours=1)
    )
    shot_new = _seed_shot(db_session, sample_bean.id, taste=9.0, created_at=now)

    response = client.get("/history")
    assert response.status_code == 200
    html = response.text

    # Newer shots should appear before older ones
    pos_new = html.find(f"shot-{shot_new.id}")
    pos_mid = html.find(f"shot-{shot_mid.id}")
    pos_old = html.find(f"shot-{shot_old.id}")

    assert pos_new < pos_mid < pos_old, "Shots should be in reverse-chronological order"


def test_history_filter_by_bean(client, sample_bean, second_bean, db_session):
    """GET /history/shots?bean_id=X returns only shots for that bean."""
    shot_a = _seed_shot(db_session, sample_bean.id, taste=8.0)
    shot_b = _seed_shot(db_session, second_bean.id, taste=7.0)

    response = client.get(f"/history/shots?bean_id={sample_bean.id}")
    assert response.status_code == 200
    html = response.text

    assert f"shot-{shot_a.id}" in html
    assert f"shot-{shot_b.id}" not in html


def test_history_filter_by_min_taste(client, sample_bean, db_session):
    """GET /history/shots?min_taste=7 returns only shots with taste >= 7."""
    shot_low = _seed_shot(db_session, sample_bean.id, taste=5.0)
    shot_mid = _seed_shot(db_session, sample_bean.id, taste=7.0)
    shot_high = _seed_shot(db_session, sample_bean.id, taste=9.0)

    response = client.get("/history/shots?min_taste=7")
    assert response.status_code == 200
    html = response.text

    assert f"shot-{shot_mid.id}" in html
    assert f"shot-{shot_high.id}" in html
    assert f"shot-{shot_low.id}" not in html


def test_history_combined_filters(client, sample_bean, second_bean, db_session):
    """Filter by bean AND min_taste together."""
    shot_match = _seed_shot(db_session, sample_bean.id, taste=8.0)
    shot_wrong_bean = _seed_shot(db_session, second_bean.id, taste=9.0)
    shot_low_taste = _seed_shot(db_session, sample_bean.id, taste=5.0)

    response = client.get(f"/history/shots?bean_id={sample_bean.id}&min_taste=7")
    assert response.status_code == 200
    html = response.text

    assert f"shot-{shot_match.id}" in html
    assert f"shot-{shot_wrong_bean.id}" not in html
    assert f"shot-{shot_low_taste.id}" not in html


def test_history_empty_state(client):
    """No shots -> empty state message."""
    response = client.get("/history")
    assert response.status_code == 200
    assert "Start brewing" in response.text


def test_history_shows_failed_indicator(client, sample_bean, db_session):
    """Failed shot has 'Failed' badge in HTML."""
    _seed_shot(db_session, sample_bean.id, taste=1.0, is_failed=True)

    response = client.get("/history")
    assert response.status_code == 200
    assert "Failed" in response.text


def test_history_shows_notes_indicator(client, sample_bean, db_session):
    """Shot with notes shows the notes icon."""
    _seed_shot(db_session, sample_bean.id, notes="Very floral, slight brightness")

    response = client.get("/history")
    assert response.status_code == 200
    assert "Has notes" in response.text


def test_history_bean_preselect(client, sample_bean, db_session):
    """GET /history?bean_id=X renders that bean selected in the dropdown."""
    _seed_shot(db_session, sample_bean.id)

    response = client.get(f"/history?bean_id={sample_bean.id}")
    assert response.status_code == 200
    # The bean option should have 'selected' attribute
    assert "selected" in response.text
    assert sample_bean.name in response.text


def test_history_shots_partial_htmx(client, sample_bean, db_session):
    """GET /history/shots with HX-Request header returns partial only."""
    _seed_shot(db_session, sample_bean.id, taste=8.0)

    response = client.get(
        "/history/shots",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    # Partial should NOT include the full base.html nav/head
    assert "<!DOCTYPE html>" not in response.text
    assert "BeanBay" not in response.text
    # But should include the shot row
    assert "shot-row" in response.text


# ---------------------------------------------------------------------------
# Shot detail modal tests
# ---------------------------------------------------------------------------


def test_shot_detail_returns_modal_html(client, sample_bean, db_session):
    """GET /history/{shot_id} returns 200 with shot details."""
    shot = _seed_shot(db_session, sample_bean.id, taste=8.5)

    response = client.get(f"/history/{shot.id}")
    assert response.status_code == 200
    html = response.text

    # Should show taste score and grind setting
    assert "8.5" in html
    assert str(shot.grind_setting) in html
    # Should show bean name
    assert "Ethiopian Yirgacheffe" in html


def test_shot_detail_includes_hx_trigger(client, sample_bean, db_session):
    """GET /history/{shot_id} response includes HX-Trigger: openShotModal header."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.get(f"/history/{shot.id}")
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "openShotModal"


def test_shot_detail_nonexistent_returns_404(client):
    """GET /history/99999 returns 404."""
    response = client.get("/history/99999")
    assert response.status_code == 404


def test_shot_edit_form_loads(client, sample_bean, db_session):
    """GET /history/{shot_id}/edit returns 200 with edit form."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.5)

    response = client.get(f"/history/{shot.id}/edit")
    assert response.status_code == 200
    html = response.text

    # Should contain form elements
    assert "hx-post" in html
    assert "edit-notes" in html
    assert "flavor-slider" in html


def test_shot_edit_saves_notes(client, sample_bean, db_session):
    """POST /history/{shot_id}/edit with notes updates DB."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.post(
        f"/history/{shot.id}/edit",
        data={"notes": "great shot, very balanced"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated = db_session.query(Measurement).filter(Measurement.id == shot.id).first()
    assert updated.notes == "great shot, very balanced"


def test_shot_edit_saves_flavor_dimensions(client, sample_bean, db_session):
    """POST /history/{shot_id}/edit with flavor dimensions updates DB."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.post(
        f"/history/{shot.id}/edit",
        data={"acidity": "3", "sweetness": "5"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated = db_session.query(Measurement).filter(Measurement.id == shot.id).first()
    assert updated.acidity == 3.0
    assert updated.sweetness == 5.0
    # Unsubmitted dimensions should be None
    assert updated.body is None


def test_shot_edit_saves_flavor_tags(client, sample_bean, db_session):
    """POST /history/{shot_id}/edit with flavor_tags saves as JSON list."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.post(
        f"/history/{shot.id}/edit",
        data={"flavor_tags": "chocolate,citrus"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated = db_session.query(Measurement).filter(Measurement.id == shot.id).first()
    tags = json.loads(updated.flavor_tags)
    assert "chocolate" in tags
    assert "citrus" in tags


def test_shot_edit_clears_notes(client, sample_bean, db_session):
    """POST /history/{shot_id}/edit with empty notes clears existing notes."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0, notes="old notes to clear")

    response = client.post(
        f"/history/{shot.id}/edit",
        data={"notes": ""},
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated = db_session.query(Measurement).filter(Measurement.id == shot.id).first()
    assert updated.notes is None


def test_shot_edit_returns_oob_row_update(client, sample_bean, db_session):
    """POST /history/{shot_id}/edit response contains hx-swap-oob for the shot row."""
    shot = _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.post(
        f"/history/{shot.id}/edit",
        data={"notes": "updated feedback"},
    )
    assert response.status_code == 200
    html = response.text

    # Response must contain oob swap for the row element
    assert "hx-swap-oob" in html
    assert f"shot-{shot.id}" in html


# ---------------------------------------------------------------------------
# Manual badge tests
# ---------------------------------------------------------------------------


def test_history_shows_manual_badge(client, sample_bean, db_session):
    """Manual measurement shows 'Manual' badge in history list."""
    _seed_shot(db_session, sample_bean.id, is_manual=True)

    response = client.get("/history")
    assert response.status_code == 200
    assert "badge-manual" in response.text
    assert "Manual" in response.text


def test_history_manual_badge_not_shown_for_regular(client, sample_bean, db_session):
    """Regular (non-manual) measurement does not show 'Manual' badge."""
    _seed_shot(db_session, sample_bean.id, is_manual=False)

    response = client.get("/history")
    assert response.status_code == 200
    assert "badge-manual" not in response.text


def test_shot_detail_shows_manual_badge(client, sample_bean, db_session):
    """Manual measurement shows 'Manual' badge in shot detail modal."""
    shot = _seed_shot(db_session, sample_bean.id, is_manual=True)

    response = client.get(f"/history/{shot.id}")
    assert response.status_code == 200
    assert "badge-manual" in response.text
    assert "Manual" in response.text


# ---------------------------------------------------------------------------
# Batch delete tests
# ---------------------------------------------------------------------------


def test_delete_batch_removes_measurements(client, sample_bean, db_session):
    """POST /history/delete-batch with shot_ids removes selected measurements."""
    from app.main import app

    shot1 = _seed_shot(db_session, sample_bean.id, taste=8.0)
    shot2 = _seed_shot(db_session, sample_bean.id, taste=7.0)
    shot3 = _seed_shot(db_session, sample_bean.id, taste=6.0)

    # Capture IDs before delete (objects may be detached after)
    id1, id2, id3 = shot1.id, shot2.id, shot3.id

    mock_optimizer = MagicMock()
    mock_optimizer.rebuild_campaign = MagicMock()
    app.state.optimizer = mock_optimizer

    response = client.post(
        "/history/delete-batch",
        data={"shot_ids": [str(id1), str(id2)]},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    remaining = db_session.query(Measurement).filter(Measurement.bean_id == sample_bean.id).all()
    remaining_ids = {m.id for m in remaining}
    assert id3 in remaining_ids
    assert id1 not in remaining_ids
    assert id2 not in remaining_ids


def test_delete_batch_rebuilds_campaign(client, sample_bean, db_session):
    """POST /history/delete-batch calls rebuild_campaign for affected bean."""
    from app.main import app

    shot1 = _seed_shot(db_session, sample_bean.id, taste=8.0)
    _seed_shot(db_session, sample_bean.id, taste=7.0)  # one remains

    mock_optimizer = MagicMock()
    mock_optimizer.rebuild_campaign = MagicMock()
    app.state.optimizer = mock_optimizer

    response = client.post(
        "/history/delete-batch",
        data={"shot_ids": [str(shot1.id)]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    mock_optimizer.rebuild_campaign.assert_called_once()
    call_args = mock_optimizer.rebuild_campaign.call_args
    assert str(sample_bean.id) == str(call_args[0][0])


def test_delete_batch_empty_ids_redirects(client, sample_bean, db_session):
    """POST /history/delete-batch with no shot_ids redirects without DB changes."""
    shot = _seed_shot(db_session, sample_bean.id, taste=8.0)

    response = client.post(
        "/history/delete-batch",
        data={},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    still_exists = db_session.query(Measurement).filter(Measurement.id == shot.id).first()
    assert still_exists is not None


def test_delete_batch_multiple_beans(client, sample_bean, second_bean, db_session):
    """POST /history/delete-batch calls rebuild_campaign once per affected bean."""
    from app.main import app

    shot_a = _seed_shot(db_session, sample_bean.id, taste=8.0)
    shot_b = _seed_shot(db_session, second_bean.id, taste=7.0)

    mock_optimizer = MagicMock()
    mock_optimizer.rebuild_campaign = MagicMock()
    app.state.optimizer = mock_optimizer

    response = client.post(
        "/history/delete-batch",
        data={"shot_ids": [str(shot_a.id), str(shot_b.id)]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert mock_optimizer.rebuild_campaign.call_count == 2
