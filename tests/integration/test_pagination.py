"""Integration tests for pagination, sorting, and filtering across resources.

Uses FlavorTag as the primary test target since it is the simplest lookup model.
Validates that the pagination contract (PaginatedResponse with items/total/limit/offset)
is consistently enforced, including edge cases, sort validation, and soft-delete filtering.
"""

BASE = "/api/v1/flavor-tags"


def _create_tags(client, names: list[str]) -> list[dict]:
    """Create FlavorTag items and return their response bodies.

    Parameters
    ----------
    client
        The FastAPI test client.
    names : list[str]
        Tag names to create.

    Returns
    -------
    list[dict]
        List of created item response bodies.
    """
    items = []
    for name in names:
        resp = client.post(BASE, json={"name": name})
        assert resp.status_code == 201, f"Failed to create tag '{name}': {resp.text}"
        items.append(resp.json())
    return items


class TestPaginationBasics:
    """Verify limit/offset pagination mechanics."""

    def test_pagination_limit_and_offset(self, client):
        """Create 5 items, request limit=2 offset=0 returns 2 items with total=5."""
        _create_tags(client, ["Pg_A", "Pg_B", "Pg_C", "Pg_D", "Pg_E"])

        resp = client.get(BASE, params={"q": "Pg_", "limit": 2, "offset": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_pagination_offset_near_end(self, client):
        """Offset=4 with 5 total items returns 1 item."""
        _create_tags(client, ["PgE_A", "PgE_B", "PgE_C", "PgE_D", "PgE_E"])

        resp = client.get(BASE, params={"q": "PgE_", "limit": 2, "offset": 4})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total"] == 5

    def test_limit_exceeds_max_returns_422(self, client):
        """Requesting limit=201 (exceeds max of 200) returns 422."""
        resp = client.get(BASE, params={"limit": 201})
        assert resp.status_code == 422

    def test_empty_list(self, client):
        """Querying for non-existent items returns items=[] and total=0."""
        resp = client.get(BASE, params={"q": "XYZNONEXISTENT999"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0


class TestSortByName:
    """Verify sorting by name in ascending and descending order."""

    def test_sort_by_name_asc(self, client):
        """Items with names A, C, B sorted asc return A, B, C."""
        _create_tags(client, ["SortAsc_A", "SortAsc_C", "SortAsc_B"])

        resp = client.get(
            BASE, params={"q": "SortAsc_", "sort_by": "name", "sort_dir": "asc"}
        )
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert names == ["SortAsc_A", "SortAsc_B", "SortAsc_C"]

    def test_sort_by_name_desc(self, client):
        """Items with names A, C, B sorted desc return C, B, A."""
        _create_tags(client, ["SortDesc_A", "SortDesc_C", "SortDesc_B"])

        resp = client.get(
            BASE, params={"q": "SortDesc_", "sort_by": "name", "sort_dir": "desc"}
        )
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert names == ["SortDesc_C", "SortDesc_B", "SortDesc_A"]


class TestSortByCreatedAt:
    """Verify sorting by created_at timestamp."""

    def test_sort_by_created_at_asc(self, client):
        """Sorting by created_at asc returns timestamps in non-decreasing order."""
        _create_tags(client, ["CrAt_Alpha", "CrAt_Beta", "CrAt_Gamma"])

        resp = client.get(
            BASE,
            params={"q": "CrAt_", "sort_by": "created_at", "sort_dir": "asc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps)

    def test_sort_by_created_at_desc(self, client):
        """Sorting by created_at desc returns timestamps in non-increasing order."""
        _create_tags(client, ["CrAtD_Alpha", "CrAtD_Beta", "CrAtD_Gamma"])

        resp = client.get(
            BASE,
            params={"q": "CrAtD_", "sort_by": "created_at", "sort_dir": "desc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)


class TestSortValidation:
    """Verify that invalid sort parameters are rejected."""

    def test_invalid_sort_by_returns_422(self, client):
        """sort_by=nonexistent returns 422."""
        resp = client.get(BASE, params={"sort_by": "nonexistent"})
        assert resp.status_code == 422

    def test_invalid_sort_dir_returns_422(self, client):
        """sort_dir=invalid returns 422."""
        resp = client.get(BASE, params={"sort_dir": "invalid"})
        assert resp.status_code == 422


class TestIncludeRetired:
    """Verify soft-delete filtering via include_retired parameter."""

    def test_retired_excluded_by_default(self, client):
        """Retired items are not returned when include_retired is not set."""
        r = client.post(BASE, json={"name": "RetExcl_Active"})
        assert r.status_code == 201

        r = client.post(BASE, json={"name": "RetExcl_Retired"})
        assert r.status_code == 201
        retired_id = r.json()["id"]
        client.delete(f"{BASE}/{retired_id}")

        resp = client.get(BASE, params={"q": "RetExcl_"})
        assert resp.status_code == 200
        body = resp.json()
        names = [item["name"] for item in body["items"]]
        assert "RetExcl_Active" in names
        assert "RetExcl_Retired" not in names
        assert body["total"] == 1

    def test_retired_included_when_requested(self, client):
        """Retired items are returned when include_retired=true."""
        r = client.post(BASE, json={"name": "RetIncl_Active"})
        assert r.status_code == 201

        r = client.post(BASE, json={"name": "RetIncl_Retired"})
        assert r.status_code == 201
        retired_id = r.json()["id"]
        client.delete(f"{BASE}/{retired_id}")

        resp = client.get(BASE, params={"q": "RetIncl_", "include_retired": True})
        assert resp.status_code == 200
        body = resp.json()
        names = [item["name"] for item in body["items"]]
        assert "RetIncl_Active" in names
        assert "RetIncl_Retired" in names
        assert body["total"] == 2
        # Verify the retired item is actually marked as retired
        retired_items = [i for i in body["items"] if i["name"] == "RetIncl_Retired"]
        assert retired_items[0]["is_retired"] is True
