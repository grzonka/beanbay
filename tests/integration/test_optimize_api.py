"""Tests for optimization seed data, campaign CRUD, and recommendation endpoints."""

import uuid
from datetime import datetime, timezone

import pandas as pd
from baybe import Campaign as BaybeCampaign
from sqlmodel import select

from beanbay.models.optimization import (
    BeanParameterOverride,
    Campaign,
    MethodParameterDefault,
)
from beanbay.models.tag import BrewMethod
from beanbay.seed import seed_brew_methods
from beanbay.seed_optimization import seed_method_parameter_defaults
from beanbay.services.optimizer import OptimizerService
from beanbay.services.parameter_ranges import compute_effective_ranges


def test_seed_espresso_defaults(session):
    """Espresso defaults are seeded with the correct parameters."""
    seed_brew_methods(session)
    session.commit()
    seed_method_parameter_defaults(session)
    session.commit()

    espresso = session.exec(
        select(BrewMethod).where(BrewMethod.name == "espresso")
    ).one()

    defaults = session.exec(
        select(MethodParameterDefault).where(
            MethodParameterDefault.brew_method_id == espresso.id
        )
    ).all()

    param_names = {d.parameter_name for d in defaults}
    assert len(defaults) == 12
    assert param_names == {
        "temperature",
        "dose",
        "yield_amount",
        "pre_infusion_time",
        "preinfusion_pressure",
        "pressure",
        "flow_rate",
        "saturation",
        "bloom_pause",
        "pressure_profile",
        "brew_mode",
        "temp_profile",
    }
    # grind_setting must never be seeded
    assert "grind_setting" not in param_names

    # Spot-check a numeric parameter
    temp = next(d for d in defaults if d.parameter_name == "temperature")
    assert temp.min_value == 85.0
    assert temp.max_value == 105.0
    assert temp.step == 0.5
    assert temp.requires is None
    assert temp.allowed_values is None

    # Spot-check a categorical parameter
    pp = next(d for d in defaults if d.parameter_name == "pressure_profile")
    assert pp.min_value is None
    assert pp.max_value is None
    assert pp.step is None
    assert pp.allowed_values == "ramp_up,flat,decline,custom"
    assert pp.requires == "pressure_control_type in (manual_profiling, programmable)"


def test_seed_method_parameter_defaults_idempotent(session):
    """Running the seed function twice does not duplicate rows."""
    seed_brew_methods(session)
    session.commit()

    seed_method_parameter_defaults(session)
    session.commit()
    seed_method_parameter_defaults(session)
    session.commit()

    all_defaults = session.exec(select(MethodParameterDefault)).all()
    # 12 espresso + 4 pour-over + 4 french-press + 5 aeropress
    # + 3 turkish + 3 moka-pot + 3 cold-brew = 34 total
    assert len(all_defaults) == 34


def test_seed_all_methods_have_defaults(session):
    """Every brew method gets at least one parameter default."""
    seed_brew_methods(session)
    session.commit()
    seed_method_parameter_defaults(session)
    session.commit()

    methods = session.exec(select(BrewMethod)).all()
    for method in methods:
        defaults = session.exec(
            select(MethodParameterDefault).where(
                MethodParameterDefault.brew_method_id == method.id
            )
        ).all()
        assert len(defaults) > 0, f"No defaults seeded for {method.name}"


def test_seed_skips_missing_method(session):
    """If a brew method does not exist, seeding does not fail."""
    # Don't seed brew methods first — the function should silently skip
    seed_method_parameter_defaults(session)
    session.commit()

    all_defaults = session.exec(select(MethodParameterDefault)).all()
    assert len(all_defaults) == 0


# ---------------------------------------------------------------------------
# Helpers for campaign endpoint tests
# ---------------------------------------------------------------------------

CAMPAIGNS = "/api/v1/optimize/campaigns"
BEANS = "/api/v1/beans"
BREW_SETUPS = "/api/v1/brew-setups"
BREW_METHODS = "/api/v1/brew-methods"
DEFAULTS = "/api/v1/optimize/defaults"


def _create_brew_method(client, name: str = "espresso") -> str:
    """Create a brew method and return its id."""
    resp = client.post(BREW_METHODS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_bean(client, name: str = "Test Bean") -> str:
    """Create a bean and return its id."""
    resp = client.post(BEANS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_brew_setup(client, brew_method_id: str, **kwargs) -> str:
    """Create a brew setup and return its id."""
    payload = {"brew_method_id": brew_method_id, **kwargs}
    resp = client.post(BREW_SETUPS, json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Campaign CRUD tests
# ---------------------------------------------------------------------------


class TestCampaignCreate:
    """Tests for POST /api/v1/optimize/campaigns."""

    def test_create_campaign(self, client, session):
        """POST creates a new campaign for a valid bean + setup pair -> 201."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_camp1")
        bean_id = _create_bean(client, "Campaign Bean 1")
        setup_id = _create_brew_setup(client, method_id)

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["bean_id"] == bean_id
        assert data["brew_setup_id"] == setup_id
        assert data["phase"] == "random"
        assert data["measurement_count"] == 0
        assert data["best_score"] is None
        assert "effective_ranges" in data

    def test_create_campaign_idempotent(self, client, session):
        """POST with same bean+setup returns existing campaign -> 200."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_camp2")
        bean_id = _create_bean(client, "Idempotent Bean")
        setup_id = _create_brew_setup(client, method_id)

        resp1 = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        assert resp1.status_code == 201
        campaign_id = resp1.json()["id"]

        resp2 = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["id"] == campaign_id

    def test_create_campaign_invalid_bean(self, client):
        """POST with non-existent bean_id -> 404."""
        method_id = _create_brew_method(client, "espresso_camp3")
        setup_id = _create_brew_setup(client, method_id)
        fake_bean = str(uuid.uuid4())

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": fake_bean, "brew_setup_id": setup_id},
        )
        assert resp.status_code == 404
        assert "Bean" in resp.json()["detail"]

    def test_create_campaign_invalid_setup(self, client):
        """POST with non-existent brew_setup_id -> 404."""
        bean_id = _create_bean(client, "No Setup Bean")
        fake_setup = str(uuid.uuid4())

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": fake_setup},
        )
        assert resp.status_code == 404
        assert "BrewSetup" in resp.json()["detail"]


class TestCampaignList:
    """Tests for GET /api/v1/optimize/campaigns."""

    def test_list_campaigns(self, client, session):
        """GET returns all campaigns."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_list1")
        bean_id = _create_bean(client, "List Bean")
        setup_id = _create_brew_setup(client, method_id)

        client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )

        resp = client.get(CAMPAIGNS)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_campaigns_filter_bean(self, client, session):
        """GET with bean_id filter narrows results."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_flt1")
        bean1_id = _create_bean(client, "Filter Bean A")
        bean2_id = _create_bean(client, "Filter Bean B")
        setup_id = _create_brew_setup(client, method_id)

        client.post(
            CAMPAIGNS,
            json={"bean_id": bean1_id, "brew_setup_id": setup_id},
        )
        client.post(
            CAMPAIGNS,
            json={"bean_id": bean2_id, "brew_setup_id": setup_id},
        )

        resp = client.get(CAMPAIGNS, params={"bean_id": bean1_id})
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["bean_name"] == "Filter Bean A" for c in data)

    def test_list_campaigns_filter_setup(self, client, session):
        """GET with brew_setup_id filter narrows results."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_flt2")
        bean_id = _create_bean(client, "Setup Filter Bean")
        setup1_id = _create_brew_setup(client, method_id, name="Setup A")
        setup2_id = _create_brew_setup(client, method_id, name="Setup B")

        client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup1_id},
        )
        client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup2_id},
        )

        resp = client.get(CAMPAIGNS, params={"brew_setup_id": setup1_id})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestCampaignDetail:
    """Tests for GET /api/v1/optimize/campaigns/{id}."""

    def test_get_campaign_detail(self, client, session):
        """GET returns campaign with effective_ranges."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_det1")
        bean_id = _create_bean(client, "Detail Bean")
        setup_id = _create_brew_setup(client, method_id)

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        campaign_id = resp.json()["id"]

        resp = client.get(f"{CAMPAIGNS}/{campaign_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == campaign_id
        assert "effective_ranges" in data

    def test_get_campaign_not_found(self, client):
        """GET with invalid id -> 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{CAMPAIGNS}/{fake_id}")
        assert resp.status_code == 404


class TestCampaignReset:
    """Tests for DELETE /api/v1/optimize/campaigns/{id}."""

    def test_reset_campaign(self, client, session):
        """DELETE resets campaign state."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_rst1")
        bean_id = _create_bean(client, "Reset Bean")
        setup_id = _create_brew_setup(client, method_id)

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        campaign_id = resp.json()["id"]

        resp = client.delete(f"{CAMPAIGNS}/{campaign_id}")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Campaign reset."

    def test_reset_campaign_not_found(self, client):
        """DELETE with invalid id -> 404."""
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{CAMPAIGNS}/{fake_id}")
        assert resp.status_code == 404


class TestMethodDefaults:
    """Tests for GET /api/v1/optimize/defaults/{brew_method_id}."""

    def test_get_method_defaults(self, client, session):
        """GET returns parameter defaults for a brew method."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        # Find espresso method id
        espresso = session.exec(
            select(BrewMethod).where(BrewMethod.name == "espresso")
        ).one()

        resp = client.get(f"{DEFAULTS}/{espresso.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 12
        param_names = {d["parameter_name"] for d in data}
        assert "temperature" in param_names

    def test_get_method_defaults_not_found(self, client):
        """GET with invalid brew_method_id -> 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{DEFAULTS}/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Helpers for recommendation endpoint tests
# ---------------------------------------------------------------------------

RECOMMEND = "/api/v1/optimize/campaigns/{campaign_id}/recommend"
JOBS = "/api/v1/optimize/jobs"
RECOMMENDATIONS = "/api/v1/optimize/recommendations"
CAMPAIGN_RECS = "/api/v1/optimize/campaigns/{campaign_id}/recommendations"
PEOPLE = "/api/v1/people"
BREWS = "/api/v1/brews"


def _setup_campaign(client, session):
    """Seed data and create a campaign with a pour-over setup.

    Uses the seeded 'pour-over' method which has 4 parameters
    (temperature, dose, yield_amount, bloom_weight) -- none with
    ``requires`` gates, so no brewer is needed.

    Returns
    -------
    dict
        Keys: campaign_id, bean_id, brew_setup_id, brew_method_id.
    """
    seed_brew_methods(session)
    session.commit()
    seed_method_parameter_defaults(session)
    session.commit()

    # Look up the seeded pour-over method
    pour_over = session.exec(
        select(BrewMethod).where(BrewMethod.name == "pour-over")
    ).one()
    method_id = str(pour_over.id)

    bean_id = _create_bean(client, "Rec Bean")
    setup_id = _create_brew_setup(client, method_id)

    resp = client.post(
        CAMPAIGNS,
        json={"bean_id": bean_id, "brew_setup_id": setup_id},
    )
    assert resp.status_code == 201
    campaign_id = resp.json()["id"]

    return {
        "campaign_id": campaign_id,
        "bean_id": bean_id,
        "brew_setup_id": setup_id,
        "brew_method_id": method_id,
    }


def _create_person(client, name: str = "Tester") -> str:
    """Create a person and return its id."""
    resp = client.post(PEOPLE, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_bag(client, bean_id: str) -> str:
    """Create a bag for a bean and return its id."""
    resp = client.post(
        f"{BEANS}/{bean_id}/bags", json={"weight": 250.0}
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_brew(client, bag_id: str, setup_id: str, person_id: str) -> str:
    """Create a brew and return its id."""
    resp = client.post(
        BREWS,
        json={
            "bag_id": bag_id,
            "brew_setup_id": setup_id,
            "person_id": person_id,
            "dose": 18.0,
            "brewed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Recommendation & Job tests
# ---------------------------------------------------------------------------

# These tests use the recommend_client / recommend_session fixtures from
# the integration conftest.  Those fixtures share a StaticPool SQLite
# engine so the taskiq broker task can see the same data.


class TestRequestRecommendation:
    """Tests for POST /optimize/campaigns/{id}/recommend."""

    def test_recommend_returns_202_with_job_id(
        self, recommend_client, recommend_session
    ):
        """POST /recommend -> 202, returns job_id and status."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        resp = recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        # job_id should be a valid UUID string
        uuid.UUID(data["job_id"])

    def test_recommend_nonexistent_campaign_404(
        self, recommend_client, recommend_session
    ):
        """POST /recommend for a non-existent campaign -> 404."""
        fake_id = str(uuid.uuid4())
        resp = recommend_client.post(
            RECOMMEND.format(campaign_id=fake_id)
        )
        assert resp.status_code == 404


class TestGetJob:
    """Tests for GET /optimize/jobs/{job_id}."""

    def test_get_job_after_recommend(
        self, recommend_client, recommend_session
    ):
        """GET /jobs/{id} returns job; with InMemoryBroker it may be completed."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        rec_resp = recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )
        job_id = rec_resp.json()["job_id"]

        resp = recommend_client.get(f"{JOBS}/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["campaign_id"] == ids["campaign_id"]
        assert data["job_type"] == "recommend"
        # InMemoryBroker runs tasks inline, so job should be completed
        assert data["status"] in ("pending", "completed")


class TestListRecommendations:
    """Tests for GET /optimize/campaigns/{id}/recommendations."""

    def test_list_recommendations_after_recommend(
        self, recommend_client, recommend_session
    ):
        """After requesting a recommendation, listing returns it."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )

        resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        rec = data[0]
        assert rec["campaign_id"] == ids["campaign_id"]
        assert isinstance(rec["parameter_values"], dict)
        assert rec["status"] == "pending"

    def test_list_recommendations_nonexistent_campaign(
        self, recommend_client, recommend_session
    ):
        """GET recommendations for non-existent campaign -> 404."""
        fake_id = str(uuid.uuid4())
        resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=fake_id)
        )
        assert resp.status_code == 404


class TestGetRecommendation:
    """Tests for GET /optimize/recommendations/{id}."""

    def test_get_recommendation_detail(
        self, recommend_client, recommend_session
    ):
        """GET recommendation detail has parameter_values as dict."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )

        # List to get the recommendation id
        list_resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=ids["campaign_id"])
        )
        rec_id = list_resp.json()[0]["id"]

        resp = recommend_client.get(f"{RECOMMENDATIONS}/{rec_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rec_id
        assert isinstance(data["parameter_values"], dict)
        # Pour-over parameters: temperature, dose, yield_amount, bloom_weight
        param_names = set(data["parameter_values"].keys())
        expected = {"temperature", "dose", "yield_amount", "bloom_weight"}
        assert param_names == expected


class TestSkipRecommendation:
    """Tests for POST /optimize/recommendations/{id}/skip."""

    def test_skip_sets_status(
        self, recommend_client, recommend_session
    ):
        """POST /skip -> status becomes 'skipped'."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )

        list_resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=ids["campaign_id"])
        )
        rec_id = list_resp.json()[0]["id"]

        resp = recommend_client.post(
            f"{RECOMMENDATIONS}/{rec_id}/skip"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "skipped"
        assert data["id"] == rec_id


class TestLinkRecommendation:
    """Tests for POST /optimize/recommendations/{id}/link."""

    def test_link_with_valid_brew(
        self, recommend_client, recommend_session
    ):
        """POST /link with valid brew_id -> status 'brewed', brew_id set."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )

        list_resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=ids["campaign_id"])
        )
        rec_id = list_resp.json()[0]["id"]

        # Create a brew to link
        person_id = _create_person(recommend_client)
        bag_id = _create_bag(recommend_client, ids["bean_id"])
        brew_id = _create_brew(
            recommend_client, bag_id, ids["brew_setup_id"], person_id
        )

        resp = recommend_client.post(
            f"{RECOMMENDATIONS}/{rec_id}/link",
            json={"brew_id": brew_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "brewed"
        assert data["brew_id"] == brew_id

    def test_link_with_invalid_brew_404(
        self, recommend_client, recommend_session
    ):
        """POST /link with non-existent brew_id -> 404."""
        ids = _setup_campaign(
            recommend_client, recommend_session
        )

        recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )

        list_resp = recommend_client.get(
            CAMPAIGN_RECS.format(campaign_id=ids["campaign_id"])
        )
        rec_id = list_resp.json()[0]["id"]

        fake_brew = str(uuid.uuid4())
        resp = recommend_client.post(
            f"{RECOMMENDATIONS}/{rec_id}/link",
            json={"brew_id": fake_brew},
        )
        assert resp.status_code == 404
        assert "Brew" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Helpers for person preferences tests
# ---------------------------------------------------------------------------

PREFERENCES = "/api/v1/optimize/people/{person_id}/preferences"
FLAVOR_TAGS = "/api/v1/flavor-tags"
ORIGINS = "/api/v1/origins"
BAGS = "/api/v1/beans/{bean_id}/bags"
TASTES = "/api/v1/brews/{brew_id}/taste"


def _create_flavor_tag(client, name: str) -> str:
    """Create a flavor tag and return its id."""
    resp = client.post(FLAVOR_TAGS, json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_origin(client, name: str, country: str | None = None) -> str:
    """Create an origin and return its id."""
    payload: dict = {"name": name}
    if country is not None:
        payload["country"] = country
    resp = client.post(ORIGINS, json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_bean_with_details(
    client,
    name: str,
    roast_degree: float | None = None,
    origin_ids: list[str] | None = None,
) -> str:
    """Create a bean with optional roast_degree and origins, return its id."""
    payload: dict = {"name": name}
    if roast_degree is not None:
        payload["roast_degree"] = roast_degree
    if origin_ids is not None:
        payload["origin_ids"] = origin_ids
    resp = client.post(BEANS, json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_brew_with_taste(
    client,
    bag_id: str,
    setup_id: str,
    person_id: str,
    score: float,
    flavor_tag_ids: list[str] | None = None,
) -> str:
    """Create a brew with an inline taste and return the brew id."""
    taste_payload: dict = {"score": score}
    if flavor_tag_ids:
        taste_payload["flavor_tag_ids"] = flavor_tag_ids
    resp = client.post(
        BREWS,
        json={
            "bag_id": bag_id,
            "brew_setup_id": setup_id,
            "person_id": person_id,
            "dose": 18.0,
            "brewed_at": datetime.now(timezone.utc).isoformat(),
            "taste": taste_payload,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Person Preferences tests
# ---------------------------------------------------------------------------


class TestPersonPreferences:
    """Tests for GET /api/v1/optimize/people/{person_id}/preferences."""

    def test_person_with_brews(self, client):
        """Person with brews returns populated preference data."""
        # Create prerequisite entities
        method_id = _create_brew_method(client, "espresso_pref1")
        setup_id = _create_brew_setup(client, method_id)
        person_id = _create_person(client, "Pref Tester")

        # Create flavor tags
        tag1_id = _create_flavor_tag(client, "chocolate_pref")
        tag2_id = _create_flavor_tag(client, "fruity_pref")

        # Create origin
        origin_id = _create_origin(client, "Ethiopia Pref", country="Ethiopia")

        # Create beans with roast degree and origin
        bean1_id = _create_bean_with_details(
            client, "Pref Bean 1", roast_degree=2.0, origin_ids=[origin_id]
        )
        bean2_id = _create_bean_with_details(
            client, "Pref Bean 2", roast_degree=7.5, origin_ids=[origin_id]
        )

        # Create bags
        bag1_id = _create_bag(client, bean1_id)
        bag2_id = _create_bag(client, bean2_id)

        # Create brews with taste scores and flavor tags
        _create_brew_with_taste(
            client, bag1_id, setup_id, person_id, score=8.5,
            flavor_tag_ids=[tag1_id, tag2_id],
        )
        _create_brew_with_taste(
            client, bag1_id, setup_id, person_id, score=7.0,
            flavor_tag_ids=[tag1_id],
        )
        _create_brew_with_taste(
            client, bag2_id, setup_id, person_id, score=9.0,
        )

        # Fetch preferences
        resp = client.get(PREFERENCES.format(person_id=person_id))
        assert resp.status_code == 200
        data = resp.json()

        # person
        assert data["person"]["id"] == person_id
        assert data["person"]["name"] == "Pref Tester"

        # brew_stats
        assert data["brew_stats"]["total_brews"] == 3
        assert data["brew_stats"]["avg_score"] is not None
        avg = data["brew_stats"]["avg_score"]
        assert abs(avg - (8.5 + 7.0 + 9.0) / 3) < 0.01

        # top_beans — should have both beans, sorted by avg score
        assert len(data["top_beans"]) == 2
        # Bean 2 (9.0 avg) should be first
        assert data["top_beans"][0]["name"] == "Pref Bean 2"
        assert data["top_beans"][0]["brew_count"] == 1
        assert abs(data["top_beans"][0]["avg_score"] - 9.0) < 0.01
        # Bean 1 (7.75 avg)
        assert data["top_beans"][1]["name"] == "Pref Bean 1"
        assert data["top_beans"][1]["brew_count"] == 2

        # flavor_profile — chocolate_pref appears 2x, fruity_pref 1x
        assert len(data["flavor_profile"]) >= 1
        tags_by_name = {f["tag"]: f["frequency"] for f in data["flavor_profile"]}
        assert tags_by_name["chocolate_pref"] == 2
        assert tags_by_name["fruity_pref"] == 1

        # roast_preference
        assert "avg_degree" in data["roast_preference"]
        assert "distribution" in data["roast_preference"]
        dist = data["roast_preference"]["distribution"]
        # Bean 1 (2.0) = light, Bean 2 (7.5) = dark
        assert dist["light"] >= 1
        assert dist["dark"] >= 1

        # origin_preferences
        assert len(data["origin_preferences"]) >= 1
        assert data["origin_preferences"][0]["origin"] == "Ethiopia"

        # method_breakdown
        assert len(data["method_breakdown"]) >= 1
        assert data["method_breakdown"][0]["method"] == "espresso_pref1"
        assert data["method_breakdown"][0]["brew_count"] == 3

    def test_person_with_no_brews(self, client):
        """Person with no brews returns empty/zero preference data."""
        person_id = _create_person(client, "Empty Pref Tester")

        resp = client.get(PREFERENCES.format(person_id=person_id))
        assert resp.status_code == 200
        data = resp.json()

        assert data["person"]["id"] == person_id
        assert data["brew_stats"]["total_brews"] == 0
        assert data["brew_stats"]["avg_score"] is None
        assert data["top_beans"] == []
        assert data["flavor_profile"] == []
        assert data["roast_preference"] == {}
        assert data["origin_preferences"] == []
        assert data["method_breakdown"] == []

    def test_invalid_person_id(self, client):
        """Non-existent person_id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(PREFERENCES.format(person_id=fake_id))
        assert resp.status_code == 404
        assert "Person" in resp.json()["detail"]


class TestAutoCampaignOnBrew:
    """Verify campaigns are auto-created when brews are logged."""

    def test_brew_creates_campaign(self, recommend_client, recommend_session):
        """Creating a brew auto-creates a campaign for the bean+setup."""
        seed_brew_methods(recommend_session)
        recommend_session.commit()
        seed_method_parameter_defaults(recommend_session)
        recommend_session.commit()

        method_id = _create_brew_method(recommend_client, "espresso_auto1")
        bean_id = _create_bean(recommend_client, "Auto Bean")
        setup_id = _create_brew_setup(recommend_client, method_id)
        person_id = _create_person(recommend_client, "Auto Tester")
        bag_id = _create_bag(recommend_client, bean_id)

        # Before brew: no campaign should exist
        resp = recommend_client.get(
            CAMPAIGNS, params={"bean_id": bean_id}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # Create a brew
        _create_brew_with_taste(
            recommend_client, bag_id, setup_id, person_id, score=7.5,
        )

        # After brew: campaign should exist
        resp = recommend_client.get(
            CAMPAIGNS, params={"bean_id": bean_id}
        )
        assert resp.status_code == 200
        campaigns = resp.json()
        assert len(campaigns) >= 1
        campaign = campaigns[0]
        assert campaign["bean_name"] is not None
        assert campaign["brew_setup_name"] is not None

    def test_second_brew_same_campaign(self, recommend_client, recommend_session):
        """A second brew for the same bean+setup does not create a second campaign."""
        seed_brew_methods(recommend_session)
        recommend_session.commit()
        seed_method_parameter_defaults(recommend_session)
        recommend_session.commit()

        method_id = _create_brew_method(recommend_client, "espresso_auto2")
        bean_id = _create_bean(recommend_client, "Auto Bean 2")
        setup_id = _create_brew_setup(recommend_client, method_id)
        person_id = _create_person(recommend_client, "Auto Tester 2")
        bag_id = _create_bag(recommend_client, bean_id)

        _create_brew_with_taste(
            recommend_client, bag_id, setup_id, person_id, score=7.0,
        )
        _create_brew_with_taste(
            recommend_client, bag_id, setup_id, person_id, score=8.0,
        )

        resp = recommend_client.get(
            CAMPAIGNS, params={"bean_id": bean_id}
        )
        campaigns = resp.json()
        matching = [c for c in campaigns if c["brew_setup_name"] is not None]
        assert len(matching) == 1  # Only one campaign, not two


# ---------------------------------------------------------------------------
# Campaign Progress tests
# ---------------------------------------------------------------------------

PROGRESS = "/api/v1/optimize/campaigns/{campaign_id}/progress"


class TestCampaignProgress:
    """Tests for GET /api/v1/optimize/campaigns/{campaign_id}/progress."""

    def test_campaign_no_brews(self, client, session):
        """Campaign with no brews returns getting_started and empty score_history."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_prog1")
        bean_id = _create_bean(client, "Progress Bean 1")
        setup_id = _create_brew_setup(client, method_id)

        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        resp = client.get(PROGRESS.format(campaign_id=campaign_id))
        assert resp.status_code == 200
        data = resp.json()

        assert data["phase"] == "random"
        assert data["measurement_count"] == 0
        assert data["best_score"] is None
        assert data["convergence"]["status"] == "getting_started"
        assert data["convergence"]["improvement_rate"] is None
        assert data["score_history"] == []

    def test_campaign_with_scored_brews(self, client, session):
        """Campaign with brews that have taste scores returns score_history."""
        seed_brew_methods(session)
        session.commit()
        seed_method_parameter_defaults(session)
        session.commit()

        method_id = _create_brew_method(client, "espresso_prog2")
        setup_id = _create_brew_setup(client, method_id)
        person_id = _create_person(client, "Progress Tester")
        bean_id = _create_bean(client, "Progress Bean 2")
        bag_id = _create_bag(client, bean_id)

        # Create campaign for this bean+setup
        resp = client.post(
            CAMPAIGNS,
            json={"bean_id": bean_id, "brew_setup_id": setup_id},
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        # Create several brews with taste scores
        scores = [6.5, 7.0, 8.0, 7.5]
        for score in scores:
            _create_brew_with_taste(
                client, bag_id, setup_id, person_id, score=score,
            )

        resp = client.get(PROGRESS.format(campaign_id=campaign_id))
        assert resp.status_code == 200
        data = resp.json()

        assert data["score_history"] != []
        assert len(data["score_history"]) == len(scores)

        # Verify shot_number is sequential
        for i, entry in enumerate(data["score_history"], 1):
            assert entry["shot_number"] == i
            assert entry["score"] is not None
            assert entry["is_failed"] is False

    def test_campaign_progress_not_found(self, client):
        """Non-existent campaign_id returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(PROGRESS.format(campaign_id=fake_id))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Helpers for posterior prediction tests
# ---------------------------------------------------------------------------

POSTERIOR = "/api/v1/optimize/campaigns/{campaign_id}/posterior"


def _setup_trained_campaign(client, session, measurement_count=3):
    """Seed data, create a pour-over campaign, add brews, and train BayBE.

    Creates a campaign with ``measurement_count`` brews that have taste
    scores, builds a BayBE campaign, adds measurements, and stores the
    serialized ``campaign_json`` on the DB row.

    Parameters
    ----------
    client : TestClient
        FastAPI test client.
    session : Session
        Database session (must share the same engine as the client).
    measurement_count : int
        Number of brews with taste scores to create.

    Returns
    -------
    dict
        Keys: campaign_id, bean_id, brew_setup_id, param_names.
    """
    # Seed brew methods and method parameter defaults
    seed_brew_methods(session)
    session.commit()
    seed_method_parameter_defaults(session)
    session.commit()

    # Look up seeded pour-over method
    pour_over = session.exec(
        select(BrewMethod).where(BrewMethod.name == "pour-over")
    ).one()
    method_id = str(pour_over.id)

    bean_id = _create_bean(client, "Posterior Bean")
    setup_id = _create_brew_setup(client, method_id)

    # Create campaign via API
    resp = client.post(
        CAMPAIGNS,
        json={"bean_id": bean_id, "brew_setup_id": setup_id},
    )
    assert resp.status_code == 201
    campaign_id = resp.json()["id"]

    # Create a person and bag for brews
    person_id = _create_person(client, "Posterior Tester")
    bag_id = _create_bag(client, bean_id)

    # Create brews with taste scores and pour-over parameter values
    param_sets = [
        {"temperature": 90.0, "dose": 15.0, "yield_amount": 250.0, "bloom_weight": 40.0},
        {"temperature": 93.0, "dose": 18.0, "yield_amount": 300.0, "bloom_weight": 50.0},
        {"temperature": 96.0, "dose": 20.0, "yield_amount": 350.0, "bloom_weight": 60.0},
        {"temperature": 88.0, "dose": 16.0, "yield_amount": 280.0, "bloom_weight": 45.0},
        {"temperature": 95.0, "dose": 22.0, "yield_amount": 400.0, "bloom_weight": 70.0},
    ]
    scores = [7.0, 8.0, 8.5, 6.5, 9.0]

    for i in range(measurement_count):
        params = param_sets[i % len(param_sets)]
        score = scores[i % len(scores)]
        resp = client.post(
            BREWS,
            json={
                "bag_id": bag_id,
                "brew_setup_id": setup_id,
                "person_id": person_id,
                "dose": params["dose"],
                "temperature": params["temperature"],
                "yield_amount": params["yield_amount"],
                "bloom_weight": params["bloom_weight"],
                "brewed_at": datetime.now(timezone.utc).isoformat(),
                "taste": {"score": score},
            },
        )
        assert resp.status_code == 201

    # Build a trained BayBE campaign
    campaign_row = session.get(Campaign, uuid.UUID(campaign_id))

    # Load method defaults for effective ranges
    defaults = session.exec(
        select(MethodParameterDefault).where(
            MethodParameterDefault.brew_method_id == pour_over.id
        )
    ).all()
    overrides = session.exec(
        select(BeanParameterOverride).where(
            BeanParameterOverride.bean_id == uuid.UUID(bean_id)
        )
    ).all()
    effective_ranges = compute_effective_ranges(list(defaults), None, None, list(overrides))
    param_names = [r.parameter_name for r in effective_ranges]

    baybe_campaign = OptimizerService.build_campaign(effective_ranges)

    # Build measurements DataFrame
    rows = []
    for i in range(measurement_count):
        params = param_sets[i % len(param_sets)]
        score = scores[i % len(scores)]
        row = {name: params[name] for name in param_names}
        row["score"] = score
        rows.append(row)
    measurements_df = pd.DataFrame(rows)
    baybe_campaign.add_measurements(measurements_df)

    # Store serialized campaign on the DB row
    campaign_row.campaign_json = baybe_campaign.to_json()
    campaign_row.measurement_count = measurement_count
    campaign_row.best_score = max(scores[:measurement_count])
    session.add(campaign_row)
    session.commit()

    return {
        "campaign_id": campaign_id,
        "bean_id": bean_id,
        "brew_setup_id": setup_id,
        "param_names": param_names,
    }


# ---------------------------------------------------------------------------
# Posterior Prediction tests
# ---------------------------------------------------------------------------


class TestPosteriorPredictions:
    """Tests for GET /api/v1/optimize/campaigns/{campaign_id}/posterior."""

    def test_posterior_1d(self, recommend_client, recommend_session):
        """1D posterior returns grid, mean, std of correct length."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=3
        )
        campaign_id = ids["campaign_id"]
        points = 20

        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=campaign_id),
            params={"params": "temperature", "points": points},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["params"] == ["temperature"]
        assert len(data["grid"]) == 1
        assert len(data["grid"][0]) == points
        assert len(data["mean"]) == points
        assert len(data["std"]) == points
        # Mean and std should be numeric
        assert all(isinstance(v, (int, float)) for v in data["mean"])
        assert all(isinstance(v, (int, float)) for v in data["std"])

    def test_posterior_2d(self, recommend_client, recommend_session):
        """2D posterior returns nested arrays (points x points)."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=3
        )
        campaign_id = ids["campaign_id"]
        points = 10

        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=campaign_id),
            params={"params": "temperature,dose", "points": points},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["params"] == ["temperature", "dose"]
        assert len(data["grid"]) == 2
        assert len(data["grid"][0]) == points
        assert len(data["grid"][1]) == points
        # Mean and std should be 2D: points x points
        assert len(data["mean"]) == points
        assert all(len(row) == points for row in data["mean"])
        assert len(data["std"]) == points
        assert all(len(row) == points for row in data["std"])

    def test_posterior_includes_measurements(
        self, recommend_client, recommend_session
    ):
        """Response includes measurement overlay data."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=3
        )
        campaign_id = ids["campaign_id"]

        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=campaign_id),
            params={"params": "temperature"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "measurements" in data
        assert len(data["measurements"]) == 3
        for m in data["measurements"]:
            assert "values" in m
            assert "score" in m
            assert isinstance(m["values"], dict)
            assert isinstance(m["score"], (int, float))

    def test_posterior_insufficient_data(
        self, recommend_client, recommend_session
    ):
        """Campaign with <2 measurements returns 422."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=1
        )
        campaign_id = ids["campaign_id"]

        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=campaign_id),
            params={"params": "temperature"},
        )
        assert resp.status_code == 422

    def test_posterior_campaign_not_found(
        self, recommend_client, recommend_session
    ):
        """Non-existent campaign returns 404."""
        fake_id = str(uuid.uuid4())
        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=fake_id),
            params={"params": "temperature"},
        )
        assert resp.status_code == 404

    def test_posterior_invalid_param_name(
        self, recommend_client, recommend_session
    ):
        """Unknown parameter name returns 422."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=3
        )
        campaign_id = ids["campaign_id"]

        resp = recommend_client.get(
            POSTERIOR.format(campaign_id=campaign_id),
            params={"params": "nonexistent_param"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Feature Importance tests
# ---------------------------------------------------------------------------

IMPORTANCE = "/api/v1/optimize/campaigns/{campaign_id}/feature-importance"


class TestFeatureImportance:
    """Tests for GET /optimize/campaigns/{id}/feature-importance."""

    def test_feature_importance_with_enough_data(
        self, recommend_client, recommend_session
    ):
        """Returns sorted parameter importance with >= 3 measurements."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=4
        )
        resp = recommend_client.get(
            IMPORTANCE.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["parameters"]) > 0
        assert len(body["importance"]) == len(body["parameters"])
        assert body["measurement_count"] == 4
        # Verify sorted descending
        for i in range(len(body["importance"]) - 1):
            assert body["importance"][i] >= body["importance"][i + 1]

    def test_feature_importance_insufficient_data(
        self, recommend_client, recommend_session
    ):
        """Returns 422 when campaign has < 3 measurements."""
        ids = _setup_trained_campaign(
            recommend_client, recommend_session, measurement_count=2
        )
        resp = recommend_client.get(
            IMPORTANCE.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 422

    def test_feature_importance_not_found(self, recommend_client):
        """Returns 404 for non-existent campaign."""
        fake_id = str(uuid.uuid4())
        resp = recommend_client.get(
            IMPORTANCE.format(campaign_id=fake_id)
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Predicted Score Population tests
# ---------------------------------------------------------------------------


class TestPredictedScorePopulation:
    """Verify taskiq worker populates predicted_score/predicted_std."""

    def test_recommendation_has_predicted_score_with_measurements(
        self, recommend_client, recommend_session
    ):
        """After recommend with 3 measurements, predicted_score is set."""
        ids = _setup_campaign(recommend_client, recommend_session)
        person_id = _create_person(recommend_client, "Scorer")
        bag_id = _create_bag(recommend_client, ids["bean_id"])

        # Create 3 brews with full pour-over parameter values and taste scores
        param_sets = [
            {"temperature": 90.0, "dose": 15.0, "yield_amount": 250.0, "bloom_weight": 40.0},
            {"temperature": 93.0, "dose": 18.0, "yield_amount": 300.0, "bloom_weight": 50.0},
            {"temperature": 96.0, "dose": 20.0, "yield_amount": 350.0, "bloom_weight": 60.0},
        ]
        for params, score in zip(param_sets, [6.0, 7.0, 8.0]):
            resp = recommend_client.post(
                BREWS,
                json={
                    "bag_id": bag_id,
                    "brew_setup_id": ids["brew_setup_id"],
                    "person_id": person_id,
                    "brewed_at": datetime.now(timezone.utc).isoformat(),
                    "taste": {"score": score},
                    **params,
                },
            )
            assert resp.status_code == 201

        # Request recommendation (InMemoryBroker runs inline)
        resp = recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Get job result
        job_resp = recommend_client.get(f"{JOBS}/{job_id}")
        assert job_resp.json()["status"] == "completed"
        result_id = job_resp.json()["result_id"]

        # Get recommendation detail
        rec_resp = recommend_client.get(f"{RECOMMENDATIONS}/{result_id}")
        assert rec_resp.status_code == 200
        rec = rec_resp.json()
        assert rec["predicted_score"] is not None
        assert rec["predicted_std"] is not None
        assert isinstance(rec["predicted_score"], (int, float))
        assert isinstance(rec["predicted_std"], (int, float))
        assert rec["predicted_std"] >= 0

    def test_recommendation_no_predicted_score_without_measurements(
        self, recommend_client, recommend_session
    ):
        """Recommendation with 0 measurements has null predicted_score."""
        ids = _setup_campaign(recommend_client, recommend_session)

        resp = recommend_client.post(
            RECOMMEND.format(campaign_id=ids["campaign_id"])
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        job_resp = recommend_client.get(f"{JOBS}/{job_id}")
        assert job_resp.json()["status"] == "completed"
        result_id = job_resp.json()["result_id"]

        rec_resp = recommend_client.get(f"{RECOMMENDATIONS}/{result_id}")
        rec = rec_resp.json()
        assert rec["predicted_score"] is None
