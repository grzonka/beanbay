"""Integration tests for the Cupping API."""


def _setup_bag(client):
    bean = client.post("/api/v1/beans", json={"name": "Cupping Bean"}).json()
    bag = client.post(f"/api/v1/beans/{bean['id']}/bags", json={"weight": 250.0}).json()
    return bag["id"]


def _setup_person(client):
    return client.post("/api/v1/people", json={"name": "Cupper"}).json()["id"]


class TestCuppingCRUD:
    def test_create_cupping(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        resp = client.post("/api/v1/cuppings", json={
            "bag_id": bag_id,
            "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
            "dry_fragrance": 7.5,
            "wet_aroma": 8.0,
            "brightness": 7.0,
            "flavor": 8.5,
            "body": 7.0,
            "finish": 7.5,
            "sweetness": 8.0,
            "clean_cup": 8.5,
            "complexity": 7.5,
            "uniformity": 8.0,
            "cuppers_correction": 0.5,
            "total_score": 85.0,
            "notes": "Excellent cup",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["dry_fragrance"] == 7.5
        assert data["total_score"] == 85.0
        assert data["bag_id"] == bag_id

    def test_create_cupping_minimal(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        resp = client.post("/api/v1/cuppings", json={
            "bag_id": bag_id,
            "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["dry_fragrance"] is None
        assert data["total_score"] is None

    def test_create_cupping_with_flavor_tags(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        tag = client.post("/api/v1/flavor-tags", json={"name": "berry"}).json()
        resp = client.post("/api/v1/cuppings", json={
            "bag_id": bag_id,
            "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
            "flavor_tag_ids": [tag["id"]],
        })
        assert resp.status_code == 201
        assert len(resp.json()["flavor_tags"]) == 1

    def test_list_cuppings(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        client.post("/api/v1/cuppings", json={
            "bag_id": bag_id, "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
        })
        client.post("/api/v1/cuppings", json={
            "bag_id": bag_id, "person_id": person_id,
            "cupped_at": "2026-03-22T10:00:00",
        })
        resp = client.get(f"/api/v1/cuppings?bag_id={bag_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_update_cupping(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        cupping = client.post("/api/v1/cuppings", json={
            "bag_id": bag_id, "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
            "dry_fragrance": 7.0,
        }).json()
        resp = client.patch(
            f"/api/v1/cuppings/{cupping['id']}",
            json={"dry_fragrance": 8.0, "notes": "Adjusted"},
        )
        assert resp.status_code == 200
        assert resp.json()["dry_fragrance"] == 8.0
        assert resp.json()["notes"] == "Adjusted"

    def test_delete_cupping(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        cupping = client.post("/api/v1/cuppings", json={
            "bag_id": bag_id, "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
        }).json()
        resp = client.delete(f"/api/v1/cuppings/{cupping['id']}")
        assert resp.status_code == 200
        assert resp.json()["is_retired"] is True

    def test_cannot_delete_bag_with_active_cupping(self, client):
        bag_id = _setup_bag(client)
        person_id = _setup_person(client)
        client.post("/api/v1/cuppings", json={
            "bag_id": bag_id, "person_id": person_id,
            "cupped_at": "2026-03-21T10:00:00",
        })
        # Get bean_id from bag
        bags_resp = client.get("/api/v1/bags")
        bean_id = None
        for b in bags_resp.json()["items"]:
            if b["id"] == bag_id:
                bean_id = b["bean_id"]
                break
        resp = client.delete(f"/api/v1/bags/{bag_id}")
        assert resp.status_code == 409
