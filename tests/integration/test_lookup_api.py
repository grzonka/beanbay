"""Integration tests for the generic lookup-table CRUD endpoints.

FlavorTag is tested thoroughly as the representative model.
Origin receives a smoke test to verify the factory wires correctly.
"""

import uuid


# ======================================================================
# FlavorTag — full CRUD test suite
# ======================================================================

BASE = "/api/v1/flavor-tags"


class TestFlavorTagCreate:
    """POST /api/v1/flavor-tags"""

    def test_create_returns_201(self, client):
        """POST creates a tag and returns 201 with id, name, created_at."""
        resp = client.post(BASE, json={"name": "Chocolate"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Chocolate"
        assert "id" in body
        assert "created_at" in body
        assert body["is_retired"] is False
        assert body["retired_at"] is None

    def test_create_duplicate_returns_409(self, client):
        """POST with a duplicate name returns 409 Conflict."""
        client.post(BASE, json={"name": "Duplicate"})
        resp = client.post(BASE, json={"name": "Duplicate"})
        assert resp.status_code == 409


class TestFlavorTagList:
    """GET /api/v1/flavor-tags"""

    def test_list_returns_paginated(self, client):
        """GET / returns items, total, limit, offset."""
        client.post(BASE, json={"name": "Fruity"})
        client.post(BASE, json={"name": "Nutty"})
        resp = client.get(BASE)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert body["total"] >= 2

    def test_list_search_q(self, client):
        """GET /?q=choc filters by case-insensitive name match."""
        client.post(BASE, json={"name": "Dark Chocolate"})
        client.post(BASE, json={"name": "Caramel"})
        resp = client.get(BASE, params={"q": "choc"})
        assert resp.status_code == 200
        body = resp.json()
        names = [item["name"] for item in body["items"]]
        assert "Dark Chocolate" in names
        assert "Caramel" not in names

    def test_list_excludes_retired_by_default(self, client):
        """GET / excludes soft-deleted items by default."""
        r = client.post(BASE, json={"name": "ToRetire"})
        item_id = r.json()["id"]
        client.delete(f"{BASE}/{item_id}")

        resp = client.get(BASE, params={"q": "ToRetire"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_include_retired(self, client):
        """GET /?include_retired=true includes soft-deleted items."""
        r = client.post(BASE, json={"name": "RetiredTag"})
        item_id = r.json()["id"]
        client.delete(f"{BASE}/{item_id}")

        resp = client.get(BASE, params={"q": "RetiredTag", "include_retired": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["is_retired"] is True

    def test_list_sort_by_name_desc(self, client):
        """GET /?sort_by=name&sort_dir=desc sorts correctly."""
        client.post(BASE, json={"name": "AAA_first"})
        client.post(BASE, json={"name": "ZZZ_last"})
        resp = client.get(BASE, params={"sort_by": "name", "sort_dir": "desc"})
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert names == sorted(names, reverse=True)

    def test_list_sort_by_invalid_returns_422(self, client):
        """GET /?sort_by=invalid returns 422."""
        resp = client.get(BASE, params={"sort_by": "invalid"})
        assert resp.status_code == 422


class TestFlavorTagGetById:
    """GET /api/v1/flavor-tags/{id}"""

    def test_get_by_id(self, client):
        """GET /{id} returns the item."""
        r = client.post(BASE, json={"name": "Berry"})
        item_id = r.json()["id"]
        resp = client.get(f"{BASE}/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Berry"

    def test_get_not_found(self, client):
        """GET /{id} with unknown id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE}/{fake_id}")
        assert resp.status_code == 404


class TestFlavorTagUpdate:
    """PATCH /api/v1/flavor-tags/{id}"""

    def test_patch_updates_name(self, client):
        """PATCH /{id} updates the name."""
        r = client.post(BASE, json={"name": "OldName"})
        item_id = r.json()["id"]
        resp = client.patch(f"{BASE}/{item_id}", json={"name": "NewName"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewName"

    def test_patch_not_found(self, client):
        """PATCH /{id} with unknown id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE}/{fake_id}", json={"name": "X"})
        assert resp.status_code == 404


class TestFlavorTagDelete:
    """DELETE /api/v1/flavor-tags/{id}"""

    def test_delete_soft_deletes(self, client):
        """DELETE /{id} sets retired_at and returns the item."""
        r = client.post(BASE, json={"name": "Earthy"})
        item_id = r.json()["id"]
        resp = client.delete(f"{BASE}/{item_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["retired_at"] is not None
        assert body["is_retired"] is True

    def test_delete_not_found(self, client):
        """DELETE /{id} with unknown id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE}/{fake_id}")
        assert resp.status_code == 404


# ======================================================================
# Origin — smoke test
# ======================================================================

ORIGIN_BASE = "/api/v1/origins"


class TestOriginSmoke:
    """Quick sanity check that the Origin router works end-to-end."""

    def test_create_and_get(self, client):
        """POST then GET on /origins verifies the factory wires correctly."""
        r = client.post(ORIGIN_BASE, json={"name": "Ethiopia"})
        assert r.status_code == 201
        item_id = r.json()["id"]

        resp = client.get(f"{ORIGIN_BASE}/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Ethiopia"

    def test_list(self, client):
        """GET /origins returns paginated results."""
        client.post(ORIGIN_BASE, json={"name": "Colombia"})
        resp = client.get(ORIGIN_BASE)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ======================================================================
# Origin — enrichment tests
# ======================================================================


class TestOriginEnrichment:
    """Tests for enriched Origin fields (country, region)."""

    def test_create_origin_with_country_region(self, client):
        """POST /origins with country and region stores and returns them."""
        resp = client.post(
            "/api/v1/origins",
            json={"name": "Yirgacheffe", "country": "Ethiopia", "region": "Sidamo"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["country"] == "Ethiopia"
        assert data["region"] == "Sidamo"

    def test_create_origin_minimal(self, client):
        """POST /origins without country/region defaults them to None."""
        resp = client.post("/api/v1/origins", json={"name": "Brazil"})
        assert resp.status_code == 201
        assert resp.json()["country"] is None
        assert resp.json()["region"] is None


# ======================================================================
# ProcessMethod — enrichment tests
# ======================================================================


class TestProcessMethodEnrichment:
    """Tests for enriched ProcessMethod fields (category)."""

    def test_create_process_with_category(self, client):
        """POST /process-methods with category stores and returns it."""
        resp = client.post(
            "/api/v1/process-methods",
            json={"name": "Fully Washed", "category": "washed"},
        )
        assert resp.status_code == 201
        assert resp.json()["category"] == "washed"

    def test_create_process_minimal(self, client):
        """POST /process-methods without category defaults it to None."""
        resp = client.post("/api/v1/process-methods", json={"name": "Experimental X"})
        assert resp.status_code == 201
        assert resp.json()["category"] is None


# ======================================================================
# BeanVariety — enrichment tests
# ======================================================================


class TestBeanVarietyEnrichment:
    """Tests for enriched BeanVariety fields (species)."""

    def test_create_variety_with_species(self, client):
        """POST /bean-varieties with species stores and returns it."""
        resp = client.post(
            "/api/v1/bean-varieties",
            json={"name": "Gesha", "species": "arabica"},
        )
        assert resp.status_code == 201
        assert resp.json()["species"] == "arabica"

    def test_create_variety_minimal(self, client):
        """POST /bean-varieties without species defaults it to None."""
        resp = client.post("/api/v1/bean-varieties", json={"name": "Robusta X"})
        assert resp.status_code == 201
        assert resp.json()["species"] is None
