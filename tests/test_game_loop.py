"""TEST-01 — Game loop integration tests.

Each test runs a complete game without the TUI by driving GameState and
ContentRegistry directly. No mocks — uses real TOML data.
"""

from collections import deque
from pathlib import Path

import pytest

from engine.game_state import (
    EFFECTIVENESS_FAILURE_THRESHOLD,
    EndingType,
    GameState,
    Ledger,
    PrincipalState,
)
from engine.loader import ContentRegistry

DATA_DIR = Path(__file__).parent.parent / "data"


def _make_state(registry: ContentRegistry, anomaly_order: list[str]) -> GameState:
    """Build a fresh GameState with a deterministic anomaly queue."""
    ledger = Ledger()
    principals = {pid: PrincipalState() for pid in registry.principals}
    queues = registry.build_narrative_queues()
    return GameState(ledger, principals, list(anomaly_order), [], queues)


def _run(
    registry: ContentRegistry,
    anomaly_order: list[str],
    choices: dict[str, str],
) -> tuple[EndingType, int]:
    """Run a full game loop and return (ending, final_effectiveness).

    Processes anomalies in order, applying the chosen management protocol for
    each, and stops as soon as check_ending() returns a non-None result.
    """
    state = _make_state(registry, anomaly_order)

    while True:
        anomaly_id = state.pop_next_anomaly()
        if anomaly_id is None:
            break
        anomaly = registry.anomalies[anomaly_id]
        mgmt = registry.management[choices[anomaly_id]]
        net = mgmt.cost.effectiveness_delta - anomaly.pressure.base_per_round
        state.apply_deltas(effectiveness=net)
        state.advance_cycle()
        ending = state.check_ending()
        if ending is not None:
            return ending, state.get_budget()  # budget as a proxy for any public int

    ending = state.check_ending()
    assert ending is not None, "Game ended with no ending — anomaly queue exhausted but no WIN"
    return ending, state.get_budget()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    return ContentRegistry.load_from_dir(DATA_DIR)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_optimal_choices_full_containment(registry: ContentRegistry) -> None:
    """Matching each anomaly to its correct Management Protocol drains no EFFECTIVENESS.
    The queue empties with effectiveness well above threshold → FULL CONTAINMENT."""
    ending, _ = _run(
        registry,
        anomaly_order=["the_dreamer", "hunger", "book"],
        choices={
            "the_dreamer": "standard_cage",   # net: +20 − 20 = 0
            "hunger":       "max_suppress",    # net: +50 − 50 = 0
            "book":         "soft_watch",      # net:  +0 −  0 = 0
        },
    )
    assert ending == EndingType.WIN


def test_hunger_mismanaged_triggers_containment_failure(registry: ContentRegistry) -> None:
    """Assigning Soft Watch to the KETER anomaly drains 50 EFFECTIVENESS with no offset.
    Starting at 100, landing at 50 hits the <= threshold → CONTAINMENT FAILURE."""
    ending, _ = _run(
        registry,
        anomaly_order=["the_dreamer", "hunger", "book"],
        choices={
            "the_dreamer": "standard_cage",  # net: 0 — safe
            "hunger":      "soft_watch",     # net: 0 − 50 = −50 → effectiveness = 50 → BREACH
            "book":        "soft_watch",
        },
    )
    assert ending == EndingType.BREACH


def test_euclid_mistake_is_recoverable(registry: ContentRegistry) -> None:
    """Mismanaging The Dreamer (−20) still leaves enough headroom when Hunger
    is handled correctly. Effectiveness ends at 80 → FULL CONTAINMENT."""
    ending, _ = _run(
        registry,
        anomaly_order=["the_dreamer", "hunger", "book"],
        choices={
            "the_dreamer": "soft_watch",    # net: 0 − 20 = −20 → effectiveness = 80
            "hunger":      "max_suppress",  # net: 0          → effectiveness = 80
            "book":        "soft_watch",    # net: 0          → effectiveness = 80
        },
    )
    assert ending == EndingType.WIN


def test_effectiveness_failure_threshold_value() -> None:
    """Sanity check: the threshold constant is exactly 50."""
    assert EFFECTIVENESS_FAILURE_THRESHOLD == 50


def test_anomalies_load(registry: ContentRegistry) -> None:
    """All three MVP anomalies are present in the registry."""
    assert "the_dreamer" in registry.anomalies
    assert "hunger" in registry.anomalies
    assert "book" in registry.anomalies


def test_management_protocols_load(registry: ContentRegistry) -> None:
    """All three shared Management Protocols load with correct effectiveness_delta."""
    assert registry.management["soft_watch"].cost.effectiveness_delta == 0
    assert registry.management["standard_cage"].cost.effectiveness_delta == 20
    assert registry.management["max_suppress"].cost.effectiveness_delta == 50


def test_anomaly_pressure_values(registry: ContentRegistry) -> None:
    """Pressure values match the designed drain amounts."""
    assert registry.anomalies["the_dreamer"].pressure.base_per_round == 20
    assert registry.anomalies["hunger"].pressure.base_per_round == 50
    assert registry.anomalies["book"].pressure.base_per_round == 0
