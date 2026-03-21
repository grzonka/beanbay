"""Integration tests for the Vendor API."""


class TestVendorCRUD:
    def test_create_vendor(self, client):
        resp = client.post(
            "/api/v1/vendors",
            json={"name": "Coffee Island", "url": "https://coffeeisland.example.com", "location": "Athens, Greece"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Coffee Island"
        assert data["url"] == "https://coffeeisland.example.com"
        assert data["location"] == "Athens, Greece"
        assert data["is_retired"] is False

    def test_create_vendor_minimal(self, client):
        resp = client.post("/api/v1/vendors", json={"name": "Local Shop"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] is None
        assert data["location"] is None
        assert data["notes"] is None

    def test_list_vendors(self, client):
        client.post("/api/v1/vendors", json={"name": "Shop A"})
        client.post("/api/v1/vendors", json={"name": "Shop B"})
        resp = client.get("/api/v1/vendors")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_update_vendor(self, client):
        resp = client.post("/api/v1/vendors", json={"name": "Old Name"})
        vid = resp.json()["id"]
        resp = client.patch(f"/api/v1/vendors/{vid}", json={"name": "New Name", "url": "https://new.example.com"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["url"] == "https://new.example.com"

    def test_delete_vendor(self, client):
        resp = client.post("/api/v1/vendors", json={"name": "To Delete"})
        vid = resp.json()["id"]
        resp = client.delete(f"/api/v1/vendors/{vid}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True
