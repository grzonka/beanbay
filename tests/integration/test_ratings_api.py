"""Integration tests for the BeanRating and BeanTaste CRUD endpoints.

Tests cover append-only rating creation, taste sub-resource CRUD,
person_id filtering, soft-delete, and nested person_name in reads.
"""

import uuid
from datetime import datetime, timezone

BEANS = "/api/v1/beans"
PEOPLE = "/api/v1/people"
FLAVOR_TAGS = "/api/v1/flavor-tags"
BEAN_RATINGS = "/api/v1/bean-ratings"


# ======================================================================
# Helpers
# ======================================================================


def _create_person(client, name):
    """Create a person and return its id."""
    resp = client.post(PEOPLE, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_bean(client, name):
    """Create a bean and return its id."""
    resp = client.post(BEANS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_flavor_tag(client, name):
    """Create a flavor tag and return its id."""
    resp = client.post(FLAVOR_TAGS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_rating(client, bean_id, person_id, taste=None, rated_at=None):
    """Create a bean rating and return the full response body."""
    payload = {"person_id": person_id}
    if taste is not None:
        payload["taste"] = taste
    if rated_at is not None:
        payload["rated_at"] = rated_at
    resp = client.post(f"{BEANS}/{bean_id}/ratings", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ======================================================================
# 1. Create rating with taste for a bean → 201
# ======================================================================


class TestCreateRatingWithTaste:
    """POST /api/v1/beans/{bean_id}/ratings with inline taste."""

    def test_create_rating_with_taste_returns_201(self, client):
        """Create a rating with inline taste and verify response."""
        person_id = _create_person(client, "Rater1")
        bean_id = _create_bean(client, "RatingBean1")
        tag_id = _create_flavor_tag(client, "chocolate-r1")

        taste_data = {
            "score": 8.5,
            "acidity": 6.0,
            "sweetness": 7.5,
            "notes": "Great coffee",
            "flavor_tag_ids": [tag_id],
        }
        body = _create_rating(client, bean_id, person_id, taste=taste_data)

        assert body["bean_id"] == bean_id
        assert body["person_id"] == person_id
        assert body["is_retired"] is False
        assert body["taste"] is not None
        assert body["taste"]["score"] == 8.5
        assert body["taste"]["acidity"] == 6.0
        assert body["taste"]["sweetness"] == 7.5
        assert body["taste"]["notes"] == "Great coffee"
        assert len(body["taste"]["flavor_tags"]) == 1
        assert body["taste"]["flavor_tags"][0]["id"] == tag_id


# ======================================================================
# 2. Create second rating for same bean+person → 201 (append-only)
# ======================================================================


class TestAppendOnlyRating:
    """Multiple ratings for the same bean+person are allowed."""

    def test_second_rating_for_same_bean_person_returns_201(self, client):
        """Append-only: second rating for same bean+person succeeds."""
        person_id = _create_person(client, "Rater2")
        bean_id = _create_bean(client, "RatingBean2")

        r1 = _create_rating(client, bean_id, person_id)
        r2 = _create_rating(client, bean_id, person_id)

        assert r1["id"] != r2["id"]
        assert r1["bean_id"] == r2["bean_id"] == bean_id
        assert r1["person_id"] == r2["person_id"] == person_id


# ======================================================================
# 3. GET ratings for bean ordered by rated_at desc
# ======================================================================


class TestListRatingsOrdering:
    """GET /api/v1/beans/{bean_id}/ratings ordered by rated_at desc."""

    def test_ratings_ordered_by_rated_at_desc(self, client):
        """Ratings are returned newest first."""
        person_id = _create_person(client, "Rater3")
        bean_id = _create_bean(client, "RatingBean3")

        older_time = "2025-01-01T10:00:00"
        newer_time = "2025-06-15T10:00:00"

        _create_rating(
            client, bean_id, person_id, rated_at=older_time
        )
        _create_rating(
            client, bean_id, person_id, rated_at=newer_time
        )

        resp = client.get(f"{BEANS}/{bean_id}/ratings")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        items = body["items"]
        # Newest first
        assert items[0]["rated_at"] >= items[1]["rated_at"]


# ======================================================================
# 4. Filter by person_id
# ======================================================================


class TestFilterByPerson:
    """GET /api/v1/beans/{bean_id}/ratings?person_id=..."""

    def test_filter_ratings_by_person_id(self, client):
        """Filter returns only ratings for the given person."""
        person_a = _create_person(client, "RaterA")
        person_b = _create_person(client, "RaterB")
        bean_id = _create_bean(client, "RatingBean4")

        _create_rating(client, bean_id, person_a)
        _create_rating(client, bean_id, person_b)

        resp = client.get(
            f"{BEANS}/{bean_id}/ratings",
            params={"person_id": person_a},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["person_id"] == person_a


# ======================================================================
# 5. PUT taste on rating
# ======================================================================


class TestPutTaste:
    """PUT /api/v1/bean-ratings/{id}/taste creates or replaces taste."""

    def test_put_taste_on_rating(self, client):
        """PUT creates taste on a rating that had none."""
        person_id = _create_person(client, "Rater5")
        bean_id = _create_bean(client, "RatingBean5")
        tag_id = _create_flavor_tag(client, "fruity-r5")

        rating = _create_rating(client, bean_id, person_id)
        assert rating["taste"] is None

        resp = client.put(
            f"{BEAN_RATINGS}/{rating['id']}/taste",
            json={
                "score": 9.0,
                "body": 8.0,
                "notes": "Excellent",
                "flavor_tag_ids": [tag_id],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 9.0
        assert body["body"] == 8.0
        assert body["notes"] == "Excellent"
        assert len(body["flavor_tags"]) == 1
        assert body["flavor_tags"][0]["id"] == tag_id

    def test_put_taste_replaces_existing(self, client):
        """PUT replaces an existing taste entirely."""
        person_id = _create_person(client, "Rater5b")
        bean_id = _create_bean(client, "RatingBean5b")

        taste_data = {"score": 5.0, "notes": "Initial"}
        rating = _create_rating(
            client, bean_id, person_id, taste=taste_data
        )
        original_taste_id = rating["taste"]["id"]

        resp = client.put(
            f"{BEAN_RATINGS}/{rating['id']}/taste",
            json={"score": 9.0, "notes": "Replaced"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 9.0
        assert body["notes"] == "Replaced"
        assert body["id"] != original_taste_id


# ======================================================================
# 6. PATCH taste (partial update)
# ======================================================================


class TestPatchTaste:
    """PATCH /api/v1/bean-ratings/{id}/taste partially updates."""

    def test_patch_taste_partial_update(self, client):
        """PATCH updates only provided fields."""
        person_id = _create_person(client, "Rater6")
        bean_id = _create_bean(client, "RatingBean6")

        taste_data = {
            "score": 7.0,
            "acidity": 5.0,
            "notes": "Original notes",
        }
        rating = _create_rating(
            client, bean_id, person_id, taste=taste_data
        )

        resp = client.patch(
            f"{BEAN_RATINGS}/{rating['id']}/taste",
            json={"score": 8.5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 8.5
        # Unchanged fields preserved
        assert body["acidity"] == 5.0
        assert body["notes"] == "Original notes"


# ======================================================================
# 7. DELETE taste → 204
# ======================================================================


class TestDeleteTaste:
    """DELETE /api/v1/bean-ratings/{id}/taste removes taste."""

    def test_delete_taste_returns_204(self, client):
        """DELETE taste returns 204 and rating no longer has taste."""
        person_id = _create_person(client, "Rater7")
        bean_id = _create_bean(client, "RatingBean7")

        taste_data = {"score": 6.0}
        rating = _create_rating(
            client, bean_id, person_id, taste=taste_data
        )
        assert rating["taste"] is not None

        resp = client.delete(
            f"{BEAN_RATINGS}/{rating['id']}/taste"
        )
        assert resp.status_code == 204

        # Verify taste is gone
        detail = client.get(f"{BEAN_RATINGS}/{rating['id']}")
        assert detail.status_code == 200
        assert detail.json()["taste"] is None


# ======================================================================
# 8. DELETE rating (soft-delete)
# ======================================================================


class TestDeleteRating:
    """DELETE /api/v1/bean-ratings/{id} soft-deletes."""

    def test_delete_rating_soft_deletes(self, client):
        """DELETE sets retired_at and is_retired=True."""
        person_id = _create_person(client, "Rater8")
        bean_id = _create_bean(client, "RatingBean8")

        rating = _create_rating(client, bean_id, person_id)
        assert rating["is_retired"] is False

        resp = client.delete(f"{BEAN_RATINGS}/{rating['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["retired_at"] is not None
        assert body["is_retired"] is True


# ======================================================================
# 9. Rating read includes person_name
# ======================================================================


class TestRatingIncludesPersonName:
    """BeanRatingRead includes person_name from the nested Person."""

    def test_rating_read_includes_person_name(self, client):
        """person_name is populated from the related Person."""
        person_id = _create_person(client, "NamedRater9")
        bean_id = _create_bean(client, "RatingBean9")

        rating = _create_rating(client, bean_id, person_id)
        assert rating["person_name"] == "NamedRater9"

        # Also verify via GET detail
        resp = client.get(f"{BEAN_RATINGS}/{rating['id']}")
        assert resp.status_code == 200
        assert resp.json()["person_name"] == "NamedRater9"


class TestBeanTasteAxisRework:
    """Verify BeanTaste uses the new axis set (complexity, clean_cup)."""

    def test_taste_has_new_axes(self, client):
        """Create a rating with taste including complexity and clean_cup axes."""
        person_id = _create_person(client, "AxisRater")
        bean_id = _create_bean(client, "AxisBean")

        taste_data = {
            "score": 8.0,
            "acidity": 6.0,
            "sweetness": 7.0,
            "body": 7.5,
            "aroma": 6.5,
            "complexity": 7.5,
            "clean_cup": 8.0,
        }
        body = _create_rating(client, bean_id, person_id, taste=taste_data)

        taste = body["taste"]
        assert taste["complexity"] == 7.5
        assert taste["clean_cup"] == 8.0
        assert "bitterness" not in taste
        assert "intensity" not in taste
