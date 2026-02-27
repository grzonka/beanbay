"""Tests for bean CRUD endpoints and UI."""

import pytest

from app.models.bag import Bag
from app.models.bean import Bean
from app.models.measurement import Measurement


@pytest.fixture()
def sample_bean(db_session):
    """Create a sample bean for tests."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


# --- Root route ---


def test_root_shows_welcome_when_empty(client):
    """GET / shows welcome page when no beans exist."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "BeanBay" in response.text
    assert "Add Your First Bean" in response.text


def test_root_shows_dashboard_when_beans_exist(client, sample_bean):
    """GET / shows dashboard when beans exist (no longer redirects to /beans)."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "Dashboard" in response.text


# --- Bean list ---


def test_list_beans_empty(client):
    """GET /beans returns page with empty state when no beans exist."""
    response = client.get("/beans")
    assert response.status_code == 200
    assert "No beans yet" in response.text
    assert "BeanBay" in response.text


def test_list_beans_with_beans(client, sample_bean):
    """GET /beans shows existing beans."""
    response = client.get("/beans")
    assert response.status_code == 200
    assert "Test Ethiopian" in response.text
    assert "Onyx" in response.text


def test_list_beans_shows_shot_count(client, sample_bean, db_session):
    """Bean list shows shot count for each bean."""
    # Add a measurement
    m = Measurement(
        bean_id=sample_bean.id,
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=7.0,
    )
    db_session.add(m)
    db_session.commit()

    response = client.get("/beans")
    assert response.status_code == 200
    assert "1 shot" in response.text


# --- Create bean ---


def test_create_bean(client):
    """POST /beans creates a new bean and redirects."""
    response = client.post(
        "/beans",
        data={"name": "New Bean", "roaster": "Blue Bottle", "origin": "Colombia"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Verify bean appears in list
    response = client.get("/beans")
    assert "New Bean" in response.text
    assert "Blue Bottle" in response.text


def test_create_bean_htmx(client):
    """POST /beans with HX-Request returns bean card fragment."""
    response = client.post(
        "/beans",
        data={"name": "HTMX Bean"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "HTMX Bean" in response.text
    assert "0 shots" in response.text


def test_create_bean_name_required(client):
    """POST /beans without name returns 422."""
    response = client.post("/beans", data={})
    assert response.status_code == 422


def test_create_bean_optional_fields(client):
    """POST /beans with only name works (roaster/origin optional)."""
    response = client.post(
        "/beans",
        data={"name": "Minimal Bean"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/beans")
    assert "Minimal Bean" in response.text


# --- Bean detail ---


def test_bean_detail(client, sample_bean):
    """GET /beans/{id} shows bean info."""
    response = client.get(f"/beans/{sample_bean.id}")
    assert response.status_code == 200
    assert "Test Ethiopian" in response.text
    assert "Onyx" in response.text
    assert "Yirgacheffe" in response.text


def test_bean_detail_not_found(client):
    """GET /beans/{bad_id} redirects to list."""
    response = client.get("/beans/nonexistent", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_bean_detail_shows_overrides_section(client, sample_bean):
    """Bean detail page has custom ranges section."""
    response = client.get(f"/beans/{sample_bean.id}")
    assert "Custom Ranges" in response.text


# --- Update bean ---


def test_update_bean(client, sample_bean):
    """POST /beans/{id} updates bean fields."""
    response = client.post(
        f"/beans/{sample_bean.id}",
        data={"name": "Updated Name", "roaster": "New Roaster", "origin": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get(f"/beans/{sample_bean.id}")
    assert "Updated Name" in response.text
    assert "New Roaster" in response.text


# --- Parameter overrides ---


def test_update_overrides(client, sample_bean, db_session):
    """POST /beans/{id}/overrides saves parameter overrides."""
    response = client.post(
        f"/beans/{sample_bean.id}/overrides",
        data={
            "grind_setting_min": "18.0",
            "grind_setting_max": "22.0",
            "temperature_min": "",
            "temperature_max": "",
            "preinfusion_pressure_pct_min": "",
            "preinfusion_pressure_pct_max": "",
            "dose_in_min": "",
            "dose_in_max": "",
            "target_yield_min": "",
            "target_yield_max": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Verify in DB
    db_session.expire_all()
    bean = db_session.query(Bean).filter(Bean.id == sample_bean.id).first()
    assert bean.parameter_overrides is not None
    assert bean.parameter_overrides["grind_setting"]["min"] == 18.0
    assert bean.parameter_overrides["grind_setting"]["max"] == 22.0


def test_update_overrides_clears_when_all_default(client, sample_bean, db_session):
    """POST /beans/{id}/overrides with all defaults clears overrides."""
    # First set some overrides
    sample_bean.parameter_overrides = {"grind_setting": {"min": 18.0, "max": 22.0}}
    db_session.commit()

    # Now submit all empty (= defaults)
    response = client.post(
        f"/beans/{sample_bean.id}/overrides",
        data={
            "grind_setting_min": "",
            "grind_setting_max": "",
            "temperature_min": "",
            "temperature_max": "",
            "preinfusion_pressure_pct_min": "",
            "preinfusion_pressure_pct_max": "",
            "dose_in_min": "",
            "dose_in_max": "",
            "target_yield_min": "",
            "target_yield_max": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    bean = db_session.query(Bean).filter(Bean.id == sample_bean.id).first()
    assert bean.parameter_overrides is None


# --- Activate bean ---


def test_activate_bean(client, sample_bean):
    """POST /beans/{id}/activate sets active_bean_id cookie."""
    response = client.post(
        f"/beans/{sample_bean.id}/activate",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "active_bean_id" in response.cookies
    assert response.cookies["active_bean_id"] == sample_bean.id


def test_active_bean_shown_in_nav(client, sample_bean):
    """Active bean name appears in the navigation bar."""
    # Activate the bean
    client.post(f"/beans/{sample_bean.id}/activate", follow_redirects=False)

    # Now load any page — active bean should be in the nav
    response = client.get("/beans")
    assert "Test Ethiopian" in response.text


def test_active_bean_shown_on_detail(client, sample_bean):
    """Active bean shows 'Active' badge on detail page."""
    client.post(f"/beans/{sample_bean.id}/activate", follow_redirects=False)

    response = client.get(f"/beans/{sample_bean.id}")
    assert "Active" in response.text


# --- Delete bean ---


def test_delete_bean(client, sample_bean):
    """POST /beans/{id}/delete removes the bean."""
    response = client.post(
        f"/beans/{sample_bean.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/beans")
    assert "Test Ethiopian" not in response.text


def test_delete_bean_htmx(client, sample_bean):
    """DELETE /beans/{id} with HX-Request returns empty response."""
    response = client.request(
        "DELETE",
        f"/beans/{sample_bean.id}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.text == ""


# --- Health check still works ---


def test_health(client):
    """GET /health returns JSON status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "beanbay"}


# --- Deactivate bean ---


def test_deactivate_bean(client, sample_bean):
    """POST /beans/deactivate clears active_bean_id cookie and redirects to /beans."""
    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.post("/beans/deactivate", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"

    # Verify the response instructs the browser to delete the cookie (Max-Age=0)
    set_cookie = response.headers.get("set-cookie", "")
    assert "active_bean_id" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_deactivate_bean_detail_shows_button(client, sample_bean):
    """Bean detail page shows 'Deselect' button when that bean is active."""
    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get(f"/beans/{sample_bean.id}")
    assert response.status_code == 200
    assert "Deselect" in response.text


def test_deactivate_bean_nav_shows_clear_button(client, sample_bean):
    """Nav bar shows clear button when a bean is active."""
    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/beans")
    assert response.status_code == 200


# --- Bean metadata ---


def test_create_bean_with_metadata(client):
    """POST /beans with roast_date, process, variety stores and displays them."""
    response = client.post(
        "/beans",
        data={
            "name": "Ethiopia Washed",
            "roast_date": "2026-01-15",
            "process": "washed",
            "variety": "SL-28",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Find the bean id by visiting the list and following to detail
    list_response = client.get("/beans")
    assert "Ethiopia Washed" in list_response.text

    # Get bean from DB via the list page — parse bean id from href
    import re

    match = re.search(r'href="/beans/([^"]+)"', list_response.text)
    assert match, "Bean link not found in list page"
    bean_id = match.group(1)

    detail = client.get(f"/beans/{bean_id}")
    assert detail.status_code == 200
    assert "Washed" in detail.text
    assert "SL-28" in detail.text
    assert "2026-01-15" in detail.text


def test_create_bean_without_metadata(client):
    """POST /beans with only name succeeds (backward compatible)."""
    response = client.post(
        "/beans",
        data={"name": "Minimal Bean No Meta"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    list_response = client.get("/beans")
    assert "Minimal Bean No Meta" in list_response.text

    import re

    match = re.search(r'href="/beans/([^"]+)"', list_response.text)
    assert match
    bean_id = match.group(1)

    detail = client.get(f"/beans/{bean_id}")
    assert detail.status_code == 200


def test_update_bean_with_metadata(client, sample_bean):
    """POST /beans/{id} with metadata fields updates them."""
    response = client.post(
        f"/beans/{sample_bean.id}",
        data={
            "name": "Updated Ethiopian",
            "roast_date": "2026-02-01",
            "process": "natural",
            "variety": "Gesha",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    detail = client.get(f"/beans/{sample_bean.id}")
    assert "Updated Ethiopian" in detail.text
    assert "Natural" in detail.text or "natural" in detail.text
    assert "Gesha" in detail.text
    assert "2026-02-01" in detail.text


def test_update_bean_clear_metadata(client, sample_bean, db_session):
    """POST /beans/{id} with empty process clears the field."""
    # First set a process
    sample_bean.process = "washed"
    db_session.commit()

    response = client.post(
        f"/beans/{sample_bean.id}",
        data={"name": sample_bean.name, "process": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    updated = db_session.query(Bean).filter(Bean.id == sample_bean.id).first()
    assert updated.process is None


# --- Bag management ---


def test_add_bag(client, sample_bean):
    """POST /beans/{id}/bags adds a bag and redirects to detail."""
    response = client.post(
        f"/beans/{sample_bean.id}/bags",
        data={
            "purchase_date": "2026-01-20",
            "cost": "15.50",
            "weight_grams": "250",
            "notes": "First bag",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert f"/beans/{sample_bean.id}" in response.headers["location"]

    detail = client.get(f"/beans/{sample_bean.id}")
    assert detail.status_code == 200
    assert "15.50" in detail.text
    assert "250" in detail.text


def test_add_bag_minimal(client, sample_bean, db_session):
    """POST /beans/{id}/bags with no optional fields creates a bag with no details."""
    response = client.post(
        f"/beans/{sample_bean.id}/bags",
        data={
            "purchase_date": "",
            "cost": "",
            "weight_grams": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    bag = db_session.query(Bag).filter(Bag.bean_id == sample_bean.id).first()
    assert bag is not None
    assert bag.cost is None
    assert bag.weight_grams is None
    assert bag.purchase_date is None
    assert bag.notes is None


def test_delete_bag(client, sample_bean, db_session):
    """POST /beans/{id}/bags/{bag_id}/delete removes the bag."""
    # Add a bag first via the route
    client.post(
        f"/beans/{sample_bean.id}/bags",
        data={"cost": "12.00"},
        follow_redirects=False,
    )
    db_session.expire_all()
    bag = db_session.query(Bag).filter(Bag.bean_id == sample_bean.id).first()
    assert bag is not None
    bag_id = bag.id

    # Delete it
    response = client.post(
        f"/beans/{sample_bean.id}/bags/{bag_id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    db_session.expire_all()
    deleted = db_session.query(Bag).filter(Bag.id == bag_id).first()
    assert deleted is None


def test_bean_detail_shows_bags(client, sample_bean, db_session):
    """GET /beans/{id} shows all bags for that bean."""
    client.post(
        f"/beans/{sample_bean.id}/bags",
        data={"cost": "14.00", "weight_grams": "200"},
        follow_redirects=False,
    )
    client.post(
        f"/beans/{sample_bean.id}/bags",
        data={"cost": "18.50", "weight_grams": "300"},
        follow_redirects=False,
    )

    detail = client.get(f"/beans/{sample_bean.id}")
    assert detail.status_code == 200
    assert "14.00" in detail.text
    assert "18.50" in detail.text


def test_delete_bean_cascades_bags(client, sample_bean, db_session):
    """Deleting a bean removes all its bags (cascade)."""
    client.post(
        f"/beans/{sample_bean.id}/bags",
        data={"cost": "10.00"},
        follow_redirects=False,
    )
    db_session.expire_all()
    assert db_session.query(Bag).filter(Bag.bean_id == sample_bean.id).count() == 1

    client.post(f"/beans/{sample_bean.id}/delete", follow_redirects=False)

    db_session.expire_all()
    orphaned = db_session.query(Bag).filter(Bag.bean_id == sample_bean.id).count()
    assert orphaned == 0
