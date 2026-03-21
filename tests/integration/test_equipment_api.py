"""Integration tests for equipment CRUD endpoints.

Covers Grinder, Brewer, Paper, and Water endpoints including ring config
parsing, M2M relationships, computed tier, and mineral management.
"""

import uuid


GRINDERS = "/api/v1/grinders"
BREWERS = "/api/v1/brewers"
PAPERS = "/api/v1/papers"
WATERS = "/api/v1/waters"
BREW_METHODS = "/api/v1/brew-methods"
STOP_MODES = "/api/v1/stop-modes"


# ======================================================================
# Grinder CRUD + ring config
# ======================================================================


class TestGrinderCRUD:
    """Grinder endpoint tests."""

    def test_create_grinder_minimal(self, client):
        """POST creates a grinder with no rings."""
        resp = client.post(GRINDERS, json={"name": "Niche Zero"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Niche Zero"
        assert "id" in body
        assert body["is_retired"] is False
        assert body["rings"] == []
        assert body["grind_range"] is None

    def test_create_grinder_with_single_ring(self, client):
        """POST creates a grinder with a single ring and correct grind_range."""
        rings = [{"label": "Main", "min": 0, "max": 50, "step": 1}]
        resp = client.post(
            GRINDERS,
            json={
                "name": "Comandante C40",
                "dial_type": "stepped",
                "rings": rings,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["rings"]) == 1
        assert body["rings"][0]["min"] == 0
        assert body["rings"][0]["max"] == 50
        assert body["grind_range"] is not None
        assert body["grind_range"]["min"] == 0
        assert body["grind_range"]["max"] == 50
        assert body["grind_range"]["step"] == 1

    def test_create_grinder_with_multi_ring(self, client):
        """POST creates a grinder with multiple rings and linearised grind_range."""
        rings = [
            {"label": "Outer", "min": 0, "max": 9, "step": 1},
            {"label": "Inner", "min": 0, "max": 9, "step": 1},
        ]
        resp = client.post(
            GRINDERS,
            json={"name": "Mazzer Mini", "rings": rings},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["rings"]) == 2
        assert body["grind_range"] is not None
        # 10 * 10 = 100 positions -> range 0..99
        assert body["grind_range"]["min"] == 0
        assert body["grind_range"]["max"] == 99
        assert body["grind_range"]["step"] == 1.0

    def test_get_grinder_by_id(self, client):
        """GET /{id} returns the grinder with parsed rings."""
        r = client.post(
            GRINDERS,
            json={
                "name": "DF64",
                "rings": [{"label": "Main", "min": 0, "max": 80, "step": 0.5}],
            },
        )
        grinder_id = r.json()["id"]
        resp = client.get(f"{GRINDERS}/{grinder_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "DF64"
        assert len(body["rings"]) == 1
        assert body["grind_range"]["min"] == 0
        assert body["grind_range"]["max"] == 80

    def test_update_grinder_rings(self, client):
        """PATCH updates rings and recomputes grind_range."""
        r = client.post(GRINDERS, json={"name": "EK43 Test"})
        grinder_id = r.json()["id"]

        # Initially no rings
        assert r.json()["rings"] == []

        # Add rings via PATCH
        new_rings = [{"label": "Main", "min": 0, "max": 20, "step": 0.25}]
        resp = client.patch(
            f"{GRINDERS}/{grinder_id}", json={"rings": new_rings}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["rings"]) == 1
        assert body["grind_range"]["max"] == 20

    def test_delete_grinder_soft_deletes(self, client):
        """DELETE sets retired_at and is_retired=True."""
        r = client.post(GRINDERS, json={"name": "RetireGrinder"})
        grinder_id = r.json()["id"]
        resp = client.delete(f"{GRINDERS}/{grinder_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["retired_at"] is not None
        assert body["is_retired"] is True

    def test_create_duplicate_name_returns_409(self, client):
        """POST with duplicate name returns 409."""
        client.post(GRINDERS, json={"name": "DupGrinder"})
        resp = client.post(GRINDERS, json={"name": "DupGrinder"})
        assert resp.status_code == 409

    def test_list_grinders_pagination(self, client):
        """GET / returns paginated results."""
        client.post(GRINDERS, json={"name": "ListGrinder1"})
        client.post(GRINDERS, json={"name": "ListGrinder2"})
        resp = client.get(GRINDERS)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 2

    def test_grinder_not_found(self, client):
        """GET /{id} with unknown id returns 404."""
        resp = client.get(f"{GRINDERS}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ======================================================================
# Brewer CRUD + M2M + tier
# ======================================================================


class TestBrewerCRUD:
    """Brewer endpoint tests."""

    def test_create_brewer_minimal(self, client):
        """POST creates a basic brewer."""
        resp = client.post(BREWERS, json={"name": "Gaggia Classic"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Gaggia Classic"
        assert body["is_retired"] is False
        assert body["methods"] == []
        assert body["stop_modes"] == []
        assert "tier" in body

    def test_create_brewer_with_m2m(self, client):
        """POST creates a brewer with linked methods and stop_modes."""
        # Create a brew method and stop mode first
        m_resp = client.post(BREW_METHODS, json={"name": "espresso_test_bm"})
        assert m_resp.status_code == 201
        method_id = m_resp.json()["id"]

        s_resp = client.post(STOP_MODES, json={"name": "time_test_sm"})
        assert s_resp.status_code == 201
        stop_mode_id = s_resp.json()["id"]

        resp = client.post(
            BREWERS,
            json={
                "name": "Profitec Pro 600",
                "method_ids": [method_id],
                "stop_mode_ids": [stop_mode_id],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["methods"]) == 1
        assert body["methods"][0]["name"] == "espresso_test_bm"
        assert len(body["stop_modes"]) == 1
        assert body["stop_modes"][0]["name"] == "time_test_sm"

    def test_brewer_computed_tier_basic(self, client):
        """Brewer with no capabilities -> tier 1."""
        resp = client.post(
            BREWERS,
            json={
                "name": "BasicBrewer",
                "temp_control_type": "none",
                "preinfusion_type": "none",
                "pressure_control_type": "fixed",
                "flow_control_type": "none",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["tier"] == 1

    def test_brewer_computed_tier_pid(self, client):
        """Brewer with PID temp control -> tier 2."""
        resp = client.post(
            BREWERS,
            json={
                "name": "PIDBrewerTest",
                "temp_control_type": "pid",
                "preinfusion_type": "none",
                "pressure_control_type": "fixed",
                "flow_control_type": "none",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["tier"] == 2

    def test_brewer_computed_tier_preinfusion(self, client):
        """Brewer with timed pre-infusion -> tier 3."""
        resp = client.post(
            BREWERS,
            json={
                "name": "PreinfusionBrewer",
                "temp_control_type": "pid",
                "preinfusion_type": "timed",
                "pressure_control_type": "fixed",
                "flow_control_type": "none",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["tier"] == 3

    def test_brewer_computed_tier_flow(self, client):
        """Brewer with programmable flow -> tier 5."""
        resp = client.post(
            BREWERS,
            json={
                "name": "DecentDE1Test",
                "temp_control_type": "profiling",
                "preinfusion_type": "programmable",
                "pressure_control_type": "programmable",
                "flow_control_type": "programmable",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["tier"] == 5

    def test_update_brewer_m2m(self, client):
        """PATCH updates M2M method_ids."""
        # Create brew methods
        m1 = client.post(BREW_METHODS, json={"name": "espresso_upd"})
        m2 = client.post(BREW_METHODS, json={"name": "pourover_upd"})
        mid1 = m1.json()["id"]
        mid2 = m2.json()["id"]

        # Create brewer with one method
        r = client.post(
            BREWERS,
            json={"name": "UpdateBrewerM2M", "method_ids": [mid1]},
        )
        brewer_id = r.json()["id"]
        assert len(r.json()["methods"]) == 1

        # Update to have both methods
        resp = client.patch(
            f"{BREWERS}/{brewer_id}",
            json={"method_ids": [mid1, mid2]},
        )
        assert resp.status_code == 200
        assert len(resp.json()["methods"]) == 2

    def test_delete_brewer_soft_deletes(self, client):
        """DELETE sets retired_at and is_retired=True."""
        r = client.post(BREWERS, json={"name": "RetireBrewer"})
        brewer_id = r.json()["id"]
        resp = client.delete(f"{BREWERS}/{brewer_id}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True

    def test_brewer_not_found(self, client):
        """GET /{id} with unknown id returns 404."""
        resp = client.get(f"{BREWERS}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ======================================================================
# Paper CRUD
# ======================================================================


class TestPaperCRUD:
    """Paper endpoint tests."""

    def test_create_paper(self, client):
        """POST creates a paper."""
        resp = client.post(
            PAPERS, json={"name": "Hario V60 02", "notes": "tabbed"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Hario V60 02"
        assert body["notes"] == "tabbed"
        assert body["is_retired"] is False

    def test_list_papers(self, client):
        """GET / returns paginated papers."""
        client.post(PAPERS, json={"name": "PaperA"})
        client.post(PAPERS, json={"name": "PaperB"})
        resp = client.get(PAPERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_update_paper(self, client):
        """PATCH updates paper name."""
        r = client.post(PAPERS, json={"name": "OldPaper"})
        paper_id = r.json()["id"]
        resp = client.patch(f"{PAPERS}/{paper_id}", json={"name": "NewPaper"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewPaper"

    def test_delete_paper(self, client):
        """DELETE soft-deletes a paper."""
        r = client.post(PAPERS, json={"name": "RetirePaper"})
        paper_id = r.json()["id"]
        resp = client.delete(f"{PAPERS}/{paper_id}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True

    def test_paper_duplicate_409(self, client):
        """POST with duplicate name returns 409."""
        client.post(PAPERS, json={"name": "DupPaper"})
        resp = client.post(PAPERS, json={"name": "DupPaper"})
        assert resp.status_code == 409


# ======================================================================
# Water CRUD + minerals
# ======================================================================


class TestWaterCRUD:
    """Water endpoint tests."""

    def test_create_water_no_minerals(self, client):
        """POST creates a water with no minerals."""
        resp = client.post(
            WATERS, json={"name": "Distilled", "notes": "pure H2O"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Distilled"
        assert body["minerals"] == []

    def test_create_water_with_minerals(self, client):
        """POST creates a water with inline minerals."""
        minerals = [
            {"mineral_name": "calcium", "ppm": 40.0},
            {"mineral_name": "magnesium", "ppm": 10.0},
        ]
        resp = client.post(
            WATERS,
            json={"name": "Third Wave Water", "minerals": minerals},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["minerals"]) == 2
        mineral_names = {m["mineral_name"] for m in body["minerals"]}
        assert "calcium" in mineral_names
        assert "magnesium" in mineral_names

    def test_get_water_with_minerals(self, client):
        """GET /{id} returns nested minerals."""
        minerals = [{"mineral_name": "sodium", "ppm": 5.0}]
        r = client.post(
            WATERS,
            json={"name": "SodiumWater", "minerals": minerals},
        )
        water_id = r.json()["id"]

        resp = client.get(f"{WATERS}/{water_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["minerals"]) == 1
        assert body["minerals"][0]["mineral_name"] == "sodium"
        assert body["minerals"][0]["ppm"] == 5.0

    def test_update_water_replace_minerals(self, client):
        """PATCH with minerals replaces all existing minerals."""
        minerals = [
            {"mineral_name": "calcium", "ppm": 40.0},
            {"mineral_name": "magnesium", "ppm": 10.0},
        ]
        r = client.post(
            WATERS,
            json={"name": "ReplaceTest", "minerals": minerals},
        )
        water_id = r.json()["id"]
        assert len(r.json()["minerals"]) == 2

        # Replace with new set
        new_minerals = [{"mineral_name": "potassium", "ppm": 3.0}]
        resp = client.patch(
            f"{WATERS}/{water_id}", json={"minerals": new_minerals}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["minerals"]) == 1
        assert body["minerals"][0]["mineral_name"] == "potassium"

    def test_update_water_without_minerals_preserves(self, client):
        """PATCH without minerals key preserves existing minerals."""
        minerals = [{"mineral_name": "calcium", "ppm": 30.0}]
        r = client.post(
            WATERS,
            json={"name": "PreserveTest", "minerals": minerals},
        )
        water_id = r.json()["id"]

        # Update only name — minerals should be preserved
        resp = client.patch(
            f"{WATERS}/{water_id}", json={"name": "PreserveTestRenamed"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "PreserveTestRenamed"
        assert len(body["minerals"]) == 1
        assert body["minerals"][0]["mineral_name"] == "calcium"

    def test_delete_water_soft_deletes(self, client):
        """DELETE soft-deletes a water."""
        r = client.post(WATERS, json={"name": "RetireWater"})
        water_id = r.json()["id"]
        resp = client.delete(f"{WATERS}/{water_id}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True

    def test_water_not_found(self, client):
        """GET /{id} with unknown id returns 404."""
        resp = client.get(f"{WATERS}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_water_duplicate_409(self, client):
        """POST with duplicate name returns 409."""
        client.post(WATERS, json={"name": "DupWater"})
        resp = client.post(WATERS, json={"name": "DupWater"})
        assert resp.status_code == 409
