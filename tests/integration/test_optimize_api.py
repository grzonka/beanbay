"""Tests for optimization seed data (MethodParameterDefault)."""

from sqlmodel import select

from beanbay.models.optimization import MethodParameterDefault
from beanbay.models.tag import BrewMethod
from beanbay.seed import seed_brew_methods
from beanbay.seed_optimization import seed_method_parameter_defaults


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
