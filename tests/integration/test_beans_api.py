"""Integration tests for the Bean and Bag CRUD endpoints.

Tests cover bean creation with M2M relationships, nested detail views,
M2M updates, bag CRUD, delete-with-active-bags blocking (409), and
top-level bag listing with filters.
"""

import uuid

BEANS = "/api/v1/beans"
BAGS = "/api/v1/bags"
ORIGINS = "/api/v1/origins"
PROCESS_METHODS = "/api/v1/process-methods"
BEAN_VARIETIES = "/api/v1/bean-varieties"
ROASTERS = "/api/v1/roasters"


# ======================================================================
# Helpers
# ======================================================================


def _create_origin(client, name):
    """Create an origin and return its id."""
    resp = client.post(ORIGINS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_process(client, name):
    """Create a process method and return its id."""
    resp = client.post(PROCESS_METHODS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_variety(client, name):
    """Create a bean variety and return its id."""
    resp = client.post(BEAN_VARIETIES, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_roaster(client, name):
    """Create a roaster and return its id."""
    resp = client.post(ROASTERS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_bean(client, name, **kwargs):
    """Create a bean and return the full response body."""
    payload = {"name": name, **kwargs}
    resp = client.post(BEANS, json=payload)
    assert resp.status_code == 201
    return resp.json()


def _create_bag(client, bean_id, weight=250.0, **kwargs):
    """Create a bag under a bean and return the full response body."""
    payload = {"weight": weight, **kwargs}
    resp = client.post(f"{BEANS}/{bean_id}/bags", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ======================================================================
# 1. Create bean with M2M
# ======================================================================


class TestBeanCreateWithM2M:
    """POST /api/v1/beans with origin_ids, process_ids, variety_ids."""

    def test_create_bean_with_m2m_returns_201(self, client):
        """Create a bean with M2M IDs and verify nested objects in response."""
        origin_id = _create_origin(client, "Ethiopia-b1")
        process_id = _create_process(client, "Washed-b1")
        variety_id = _create_variety(client, "Typica-b1")

        body = _create_bean(
            client,
            "Test Bean M2M",
            origin_ids=[origin_id],
            process_ids=[process_id],
            variety_ids=[variety_id],
        )
        assert body["name"] == "Test Bean M2M"
        assert "id" in body
        assert body["is_retired"] is False
        assert len(body["origins"]) == 1
        assert body["origins"][0]["id"] == origin_id
        assert len(body["processes"]) == 1
        assert body["processes"][0]["id"] == process_id
        assert len(body["varieties"]) == 1
        assert body["varieties"][0]["id"] == variety_id


# ======================================================================
# 2. GET bean detail has nested M2M
# ======================================================================


class TestBeanDetailNested:
    """GET /api/v1/beans/{id} returns nested origins, processes, varieties."""

    def test_get_bean_has_nested_m2m(self, client):
        """GET detail includes nested M2M relationships."""
        origin_id = _create_origin(client, "Colombia-b2")
        process_id = _create_process(client, "Natural-b2")
        variety_id = _create_variety(client, "Bourbon-b2")

        bean = _create_bean(
            client,
            "Detail Bean",
            origin_ids=[origin_id],
            process_ids=[process_id],
            variety_ids=[variety_id],
        )
        resp = client.get(f"{BEANS}/{bean['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["origins"]) == 1
        assert body["origins"][0]["name"] == "Colombia-b2"
        assert len(body["processes"]) == 1
        assert body["processes"][0]["name"] == "Natural-b2"
        assert len(body["varieties"]) == 1
        assert body["varieties"][0]["name"] == "Bourbon-b2"


# ======================================================================
# 3. Create bean with roaster_id
# ======================================================================


class TestBeanWithRoaster:
    """POST /api/v1/beans with roaster_id nests roaster in read."""

    def test_create_bean_with_roaster(self, client):
        """Bean created with roaster_id includes nested roaster in GET."""
        roaster_id = _create_roaster(client, "SquareMile-b3")
        bean = _create_bean(
            client, "Roasted Bean", roaster_id=roaster_id
        )
        assert bean["roaster_id"] == roaster_id
        assert bean["roaster"] is not None
        assert bean["roaster"]["name"] == "SquareMile-b3"

        # Also verify via GET
        resp = client.get(f"{BEANS}/{bean['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["roaster"]["id"] == roaster_id


# ======================================================================
# 4. PATCH bean updates M2M lists
# ======================================================================


class TestBeanUpdateM2M:
    """PATCH /api/v1/beans/{id} updates M2M relationships."""

    def test_patch_bean_updates_m2m(self, client):
        """PATCH with new origin_ids replaces the M2M list."""
        origin1 = _create_origin(client, "Kenya-b4")
        origin2 = _create_origin(client, "Rwanda-b4")

        bean = _create_bean(
            client, "Update Bean", origin_ids=[origin1]
        )
        assert len(bean["origins"]) == 1

        # Update to origin2
        resp = client.patch(
            f"{BEANS}/{bean['id']}",
            json={"origin_ids": [origin2]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["origins"]) == 1
        assert body["origins"][0]["id"] == origin2

    def test_patch_bean_clears_m2m(self, client):
        """PATCH with empty list clears the M2M relationship."""
        origin_id = _create_origin(client, "Brazil-b4b")
        bean = _create_bean(
            client, "Clear Bean", origin_ids=[origin_id]
        )
        assert len(bean["origins"]) == 1

        resp = client.patch(
            f"{BEANS}/{bean['id']}",
            json={"origin_ids": []},
        )
        assert resp.status_code == 200
        assert len(resp.json()["origins"]) == 0


# ======================================================================
# 5. Create bag under bean
# ======================================================================


class TestBagCreate:
    """POST /api/v1/beans/{bean_id}/bags creates a bag."""

    def test_create_bag_returns_201(self, client):
        """Create a bag under a bean and verify response fields."""
        bean = _create_bean(client, "Bag Bean")
        bag = _create_bag(client, bean["id"], weight=340.0, price=18.50)
        assert bag["bean_id"] == bean["id"]
        assert bag["weight"] == 340.0
        assert bag["price"] == 18.50
        assert bag["is_preground"] is False
        assert bag["is_retired"] is False

    def test_create_bag_for_nonexistent_bean_404(self, client):
        """Create a bag for a non-existent bean returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{BEANS}/{fake_id}/bags",
            json={"weight": 250.0},
        )
        assert resp.status_code == 404


# ======================================================================
# 6. GET /bags top-level list filterable by bean_id
# ======================================================================


class TestBagListByBean:
    """GET /api/v1/bags filterable by bean_id."""

    def test_bags_filter_by_bean_id(self, client):
        """GET /bags?bean_id=... returns only bags for that bean."""
        bean_a = _create_bean(client, "Bean A bags")
        bean_b = _create_bean(client, "Bean B bags")
        _create_bag(client, bean_a["id"], weight=200.0)
        _create_bag(client, bean_b["id"], weight=300.0)

        resp = client.get(BAGS, params={"bean_id": bean_a["id"]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["bean_id"] == bean_a["id"]


# ======================================================================
# 7. GET /bags filterable by is_preground
# ======================================================================


class TestBagListByPreground:
    """GET /api/v1/bags filterable by is_preground."""

    def test_bags_filter_by_is_preground(self, client):
        """GET /bags?is_preground=true returns only pre-ground bags."""
        bean = _create_bean(client, "Preground Bean")
        _create_bag(client, bean["id"], weight=250.0, is_preground=True)
        _create_bag(client, bean["id"], weight=250.0, is_preground=False)

        resp = client.get(BAGS, params={"is_preground": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["is_preground"] is True


# ======================================================================
# 8. Delete bean with active bags → 409
# ======================================================================


class TestDeleteBeanWithActiveBags:
    """DELETE /api/v1/beans/{id} blocked if active bags exist."""

    def test_delete_bean_with_active_bags_returns_409(self, client):
        """DELETE a bean that has non-retired bags returns 409 Conflict."""
        bean = _create_bean(client, "Bean with bags")
        _create_bag(client, bean["id"], weight=250.0)

        resp = client.delete(f"{BEANS}/{bean['id']}")
        assert resp.status_code == 409
        assert "active" in resp.json()["detail"].lower()


# ======================================================================
# 9. Delete bean after retiring all bags → success
# ======================================================================


class TestDeleteBeanAfterRetiringBags:
    """DELETE /api/v1/beans/{id} succeeds after all bags are retired."""

    def test_delete_bean_after_retiring_bags(self, client):
        """DELETE succeeds once all bags are soft-deleted."""
        bean = _create_bean(client, "Bean retire bags")
        bag = _create_bag(client, bean["id"], weight=250.0)

        # Retire the bag first
        resp = client.delete(f"{BAGS}/{bag['id']}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True

        # Now delete the bean
        resp = client.delete(f"{BEANS}/{bean['id']}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True


# ======================================================================
# 10. Bag CRUD (PATCH, DELETE)
# ======================================================================


class TestBagCRUD:
    """PATCH and DELETE on /api/v1/bags/{id}."""

    def test_patch_bag_updates_fields(self, client):
        """PATCH /bags/{id} updates the given fields."""
        bean = _create_bean(client, "Patch Bag Bean")
        bag = _create_bag(client, bean["id"], weight=250.0)

        resp = client.patch(
            f"{BAGS}/{bag['id']}",
            json={"weight": 500.0, "notes": "Updated notes"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["weight"] == 500.0
        assert body["notes"] == "Updated notes"

    def test_delete_bag_soft_deletes(self, client):
        """DELETE /bags/{id} sets retired_at."""
        bean = _create_bean(client, "Delete Bag Bean")
        bag = _create_bag(client, bean["id"], weight=250.0)

        resp = client.delete(f"{BAGS}/{bag['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["retired_at"] is not None
        assert body["is_retired"] is True

    def test_get_bag_by_id(self, client):
        """GET /bags/{id} returns the bag."""
        bean = _create_bean(client, "Get Bag Bean")
        bag = _create_bag(client, bean["id"], weight=250.0)

        resp = client.get(f"{BAGS}/{bag['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == bag["id"]

    def test_get_bag_not_found(self, client):
        """GET /bags/{id} with unknown id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BAGS}/{fake_id}")
        assert resp.status_code == 404

    def test_bean_detail_excludes_retired_bags(self, client):
        """GET /beans/{id} excludes retired bags from nested list."""
        bean = _create_bean(client, "Exclude Retired Bags Bean")
        bag1 = _create_bag(client, bean["id"], weight=200.0)
        _create_bag(client, bean["id"], weight=300.0)

        # Retire bag1
        client.delete(f"{BAGS}/{bag1['id']}")

        resp = client.get(f"{BEANS}/{bean['id']}")
        assert resp.status_code == 200
        body = resp.json()
        # Only the non-retired bag should appear
        assert len(body["bags"]) == 1
        assert body["bags"][0]["weight"] == 300.0
