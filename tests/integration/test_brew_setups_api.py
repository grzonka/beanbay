"""Integration tests for BrewSetup CRUD endpoints.

Covers creation with equipment references, detail with nested names,
has_grinder filtering, brew_method_id filtering, soft-delete, and
list exclude-retired-by-default behaviour.
"""

import uuid


BREW_SETUPS = "/api/v1/brew-setups"
BREW_METHODS = "/api/v1/brew-methods"
GRINDERS = "/api/v1/grinders"
BREWERS = "/api/v1/brewers"
PAPERS = "/api/v1/papers"
WATERS = "/api/v1/waters"


def _create_brew_method(client, name: str) -> str:
    """Create a brew method and return its id."""
    resp = client.post(BREW_METHODS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_grinder(client, name: str) -> str:
    """Create a grinder and return its id."""
    resp = client.post(GRINDERS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_brewer(client, name: str) -> str:
    """Create a brewer and return its id."""
    resp = client.post(BREWERS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_paper(client, name: str) -> str:
    """Create a paper and return its id."""
    resp = client.post(PAPERS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_water(client, name: str) -> str:
    """Create a water and return its id."""
    resp = client.post(WATERS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestBrewSetupCRUD:
    """BrewSetup endpoint tests."""

    def test_create_brew_setup_with_equipment(self, client):
        """POST creates a brew setup referencing existing equipment -> 201."""
        method_id = _create_brew_method(client, "espresso_bs1")
        grinder_id = _create_grinder(client, "NicheZero_bs1")
        brewer_id = _create_brewer(client, "GaggiaClassic_bs1")
        paper_id = _create_paper(client, "HarioV60_bs1")
        water_id = _create_water(client, "ThirdWave_bs1")

        resp = client.post(
            BREW_SETUPS,
            json={
                "name": "Morning Espresso",
                "brew_method_id": method_id,
                "grinder_id": grinder_id,
                "brewer_id": brewer_id,
                "paper_id": paper_id,
                "water_id": water_id,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Morning Espresso"
        assert body["brew_method_id"] == method_id
        assert body["grinder_id"] == grinder_id
        assert body["brewer_id"] == brewer_id
        assert body["paper_id"] == paper_id
        assert body["water_id"] == water_id
        assert body["is_retired"] is False
        assert "id" in body

    def test_create_brew_setup_minimal(self, client):
        """POST creates a brew setup with only the required brew_method_id."""
        method_id = _create_brew_method(client, "pourover_bs2")

        resp = client.post(
            BREW_SETUPS,
            json={"brew_method_id": method_id},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["brew_method_id"] == method_id
        assert body["grinder_id"] is None
        assert body["brewer_id"] is None
        assert body["paper_id"] is None
        assert body["water_id"] is None

    def test_get_detail_has_nested_equipment_names(self, client):
        """GET /{id} returns nested equipment names."""
        method_id = _create_brew_method(client, "espresso_detail")
        grinder_id = _create_grinder(client, "DF64_detail")
        brewer_id = _create_brewer(client, "Profitec_detail")
        paper_id = _create_paper(client, "Kalita_detail")
        water_id = _create_water(client, "RPavlis_detail")

        create_resp = client.post(
            BREW_SETUPS,
            json={
                "name": "Detail Test",
                "brew_method_id": method_id,
                "grinder_id": grinder_id,
                "brewer_id": brewer_id,
                "paper_id": paper_id,
                "water_id": water_id,
            },
        )
        setup_id = create_resp.json()["id"]

        resp = client.get(f"{BREW_SETUPS}/{setup_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["brew_method_name"] == "espresso_detail"
        assert body["grinder_name"] == "DF64_detail"
        assert body["brewer_name"] == "Profitec_detail"
        assert body["paper_name"] == "Kalita_detail"
        assert body["water_name"] == "RPavlis_detail"

    def test_filter_has_grinder_true(self, client):
        """GET ?has_grinder=true returns only setups with a grinder."""
        method_id = _create_brew_method(client, "method_hg_true")
        grinder_id = _create_grinder(client, "Grinder_hg_true")

        # Setup WITH grinder
        client.post(
            BREW_SETUPS,
            json={
                "name": "WithGrinder",
                "brew_method_id": method_id,
                "grinder_id": grinder_id,
            },
        )
        # Setup WITHOUT grinder
        client.post(
            BREW_SETUPS,
            json={
                "name": "NoGrinder",
                "brew_method_id": method_id,
            },
        )

        resp = client.get(BREW_SETUPS, params={"has_grinder": True})
        assert resp.status_code == 200
        items = resp.json()["items"]
        for item in items:
            assert item["grinder_id"] is not None

    def test_filter_has_grinder_false(self, client):
        """GET ?has_grinder=false returns only setups without a grinder."""
        method_id = _create_brew_method(client, "method_hg_false")
        grinder_id = _create_grinder(client, "Grinder_hg_false")

        # Setup WITH grinder
        client.post(
            BREW_SETUPS,
            json={
                "name": "WithGrinder2",
                "brew_method_id": method_id,
                "grinder_id": grinder_id,
            },
        )
        # Setup WITHOUT grinder
        client.post(
            BREW_SETUPS,
            json={
                "name": "NoGrinder2",
                "brew_method_id": method_id,
            },
        )

        resp = client.get(BREW_SETUPS, params={"has_grinder": False})
        assert resp.status_code == 200
        items = resp.json()["items"]
        for item in items:
            assert item["grinder_id"] is None

    def test_filter_by_brew_method_id(self, client):
        """GET ?brew_method_id=... returns only setups for that method."""
        method_a = _create_brew_method(client, "espresso_filter")
        method_b = _create_brew_method(client, "pourover_filter")

        client.post(
            BREW_SETUPS,
            json={"name": "SetupA", "brew_method_id": method_a},
        )
        client.post(
            BREW_SETUPS,
            json={"name": "SetupB", "brew_method_id": method_b},
        )

        resp = client.get(BREW_SETUPS, params={"brew_method_id": method_a})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        for item in items:
            assert item["brew_method_id"] == method_a

    def test_retire_brew_setup(self, client):
        """DELETE soft-deletes a brew setup."""
        method_id = _create_brew_method(client, "method_retire")
        create_resp = client.post(
            BREW_SETUPS,
            json={"name": "RetireMe", "brew_method_id": method_id},
        )
        setup_id = create_resp.json()["id"]

        resp = client.delete(f"{BREW_SETUPS}/{setup_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["retired_at"] is not None
        assert body["is_retired"] is True

    def test_list_excludes_retired_by_default(self, client):
        """GET / excludes retired setups by default."""
        method_id = _create_brew_method(client, "method_excl")

        # Create and retire a setup
        create_resp = client.post(
            BREW_SETUPS,
            json={"name": "WillBeRetired", "brew_method_id": method_id},
        )
        setup_id = create_resp.json()["id"]
        client.delete(f"{BREW_SETUPS}/{setup_id}")

        # Create an active setup
        client.post(
            BREW_SETUPS,
            json={"name": "StillActive", "brew_method_id": method_id},
        )

        # Default list should not include the retired setup
        resp = client.get(BREW_SETUPS)
        assert resp.status_code == 200
        items = resp.json()["items"]
        retired_ids = [i["id"] for i in items if i["id"] == setup_id]
        assert len(retired_ids) == 0

        # With include_retired=true it should appear
        resp2 = client.get(BREW_SETUPS, params={"include_retired": True})
        assert resp2.status_code == 200
        all_ids = [i["id"] for i in resp2.json()["items"]]
        assert setup_id in all_ids

    def test_update_brew_setup(self, client):
        """PATCH updates a brew setup."""
        method_id = _create_brew_method(client, "method_update")
        grinder_id = _create_grinder(client, "Grinder_update")

        create_resp = client.post(
            BREW_SETUPS,
            json={"name": "Original", "brew_method_id": method_id},
        )
        setup_id = create_resp.json()["id"]
        assert create_resp.json()["grinder_id"] is None

        resp = client.patch(
            f"{BREW_SETUPS}/{setup_id}",
            json={"name": "Updated", "grinder_id": grinder_id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Updated"
        assert body["grinder_id"] == grinder_id

    def test_brew_setup_not_found(self, client):
        """GET /{id} with unknown id returns 404."""
        resp = client.get(f"{BREW_SETUPS}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_create_with_invalid_brew_method_returns_404(self, client):
        """POST with non-existent brew_method_id returns 404."""
        resp = client.post(
            BREW_SETUPS,
            json={"brew_method_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_list_pagination(self, client):
        """GET / returns paginated results."""
        method_id = _create_brew_method(client, "method_page")
        client.post(
            BREW_SETUPS,
            json={"name": "Page1", "brew_method_id": method_id},
        )
        client.post(
            BREW_SETUPS,
            json={"name": "Page2", "brew_method_id": method_id},
        )
        resp = client.get(BREW_SETUPS)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert body["total"] >= 2
