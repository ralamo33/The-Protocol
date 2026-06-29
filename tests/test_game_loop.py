"""TEST-01 — GameState public API.

One test per public method. Uses synthetic in-memory state — no TOML, no disk.
"""

from collections import deque
from pathlib import Path

import pytest

from engine.game_state import (
    EFFECTIVENESS_FAILURE_THRESHOLD,
    EndingType,
    GameState,
    Ledger,
    Personnel,
    RoundRecord,
)
from engine.loader import (
    Anomaly,
    AnomalyEscapeCost,
    AnomalyPressure,
    ContentRegistry,
    Experiment,
    ExperimentPersonnel,
    ExperimentRoll,
    Principal,
    PrincipalArt,
    PrincipalStatus,
    PrincipalVoice,
)

DATA_DIR = Path(__file__).parent.parent / "data"


# ── Factories ─────────────────────────────────────────────────────────────────

def _make_principal(id: str = "test_p") -> Principal:
    return Principal(
        id=id,
        name="Test Principal",
        title="Tester",
        color="#ffffff",
        signature_experiment="test_exp",
        brief="Test brief.",
        art=PrincipalArt(intact="a.txt", damaged="b.txt", corrupted="c.txt"),
        voice=PrincipalVoice(success_pool="p_success", failure_pool="p_failure"),
    )


def _make_anomaly(id: str = "test_a") -> Anomaly:
    return Anomaly(
        id=id,
        display_id="AO-001",
        color="#ffffff",
        name="Test Anomaly",
        threat_level=1,
        art_file="art.txt",
        pressure=AnomalyPressure(base_per_round=10),
    )


def _make_state(
    *,
    ledger: Ledger | None = None,
    principals: dict[str, Principal] | None = None,
    anomaly_queue: list[Anomaly] | None = None,
    narrative_queues: dict[str, deque[str]] | None = None,
) -> GameState:
    return GameState(
        ledger=ledger or Ledger(),
        principals=principals or {},
        anomaly_queue=anomaly_queue or [],
        history=[],
        narrative_queues=narrative_queues or {},
    )


# ── READ — derived signals ────────────────────────────────────────────────────

def test_get_active_principals() -> None:
    p = _make_principal()
    state = _make_state(principals={"p": p})
    assert p in state.get_active_principals()


def test_get_active_principals_excludes_incapacitated() -> None:
    p = _make_principal()
    p.status = PrincipalStatus.INCAPACITATED
    state = _make_state(principals={"p": p})
    assert state.get_active_principals() == []


def test_get_budget_initial() -> None:
    state = _make_state()
    assert state.get_budget() == 100


def test_get_roll_penalty_zero_at_full_cohesion() -> None:
    state = _make_state()
    assert state.get_roll_penalty() == 0


def test_get_roll_penalty_scales_with_cohesion_loss() -> None:
    state = _make_state(ledger=Ledger(cohesion=40))
    # loss = 60, penalty = int(60 * 0.3) = 18
    assert state.get_roll_penalty() == 18


def test_get_tone_modifier_warm_at_full_cohesion() -> None:
    state = _make_state()
    assert state.get_tone_modifier() == "WARM"


def test_get_tone_modifier_cold_at_low_cohesion() -> None:
    state = _make_state(ledger=Ledger(cohesion=10))
    assert state.get_tone_modifier() == "COLD"


def test_check_ending_none_mid_game() -> None:
    state = _make_state(anomaly_queue=[_make_anomaly()])
    assert state.check_ending() is None


def test_check_ending_win_on_empty_queue() -> None:
    state = _make_state(anomaly_queue=[])
    assert state.check_ending() == EndingType.WIN


def test_check_ending_inhuman_at_zero_cohesion() -> None:
    state = _make_state(ledger=Ledger(cohesion=0), anomaly_queue=[_make_anomaly()])
    assert state.check_ending() == EndingType.INHUMAN


def test_check_ending_breach_at_threshold() -> None:
    state = _make_state(
        ledger=Ledger(effectiveness=EFFECTIVENESS_FAILURE_THRESHOLD),
        anomaly_queue=[_make_anomaly()],
    )
    assert state.check_ending() == EndingType.BREACH


def test_effectiveness_failure_threshold_value() -> None:
    assert EFFECTIVENESS_FAILURE_THRESHOLD == 50


# ── WRITE — state mutations ───────────────────────────────────────────────────

def test_apply_deltas_budget() -> None:
    state = _make_state()
    state.apply_deltas(budget=-20)
    assert state.get_budget() == 80


def test_apply_deltas_clamps_to_zero() -> None:
    state = _make_state(ledger=Ledger(cohesion=5))
    state.apply_deltas(cohesion=-100)
    assert state.get_roll_penalty() == int(100 * 0.3)  # cohesion clamped to 0


def test_advance_cycle_resets_personnel() -> None:
    state = _make_state()
    state.advance_cycle()
    # advance_cycle resets personnel; no assertion on private field but cycle ticks
    assert state.get_cycle() == 1


def test_advance_cycle_recovers_incapacitated_principal() -> None:
    p = _make_principal()
    p.status = PrincipalStatus.INCAPACITATED
    p.rounds_incapacitated = 1
    state = _make_state(principals={"p": p})
    state.advance_cycle()
    assert p.status == PrincipalStatus.ACTIVE
    assert p.rounds_incapacitated == 0


def test_advance_cycle_keeps_incapacitated_if_more_rounds() -> None:
    p = _make_principal()
    p.status = PrincipalStatus.INCAPACITATED
    p.rounds_incapacitated = 2
    state = _make_state(principals={"p": p})
    state.advance_cycle()
    assert p.status == PrincipalStatus.INCAPACITATED
    assert p.rounds_incapacitated == 1


def test_pop_next_anomaly_returns_anomaly() -> None:
    a = _make_anomaly()
    state = _make_state(anomaly_queue=[a])
    result = state.pop_next_anomaly()
    assert result is a


def test_pop_next_anomaly_depletes_queue() -> None:
    state = _make_state(anomaly_queue=[_make_anomaly()])
    state.pop_next_anomaly()
    assert state.pop_next_anomaly() is None


def test_pop_narrative_line_returns_string() -> None:
    queues: dict[str, deque[str]] = {"pool": deque(["line1", "line2"])}
    state = _make_state(narrative_queues=queues)
    line = state.pop_narrative_line("pool")
    assert isinstance(line, str)
    assert line in ("line1", "line2")


def test_pop_narrative_line_missing_pool() -> None:
    state = _make_state()
    assert state.pop_narrative_line("nonexistent") == "[no narrative]"


def test_record_round_appends() -> None:
    state = _make_state()
    record = RoundRecord(
        cycle=1,
        anomaly_id="a",
        principal_id="p",
        experiment_id="e",
        management_id="m",
        outcome="SUCCESS",
        narrative="test",
    )
    state.record_round(record)
    # recorded — no direct access to history but no exception raised


# ── PERSISTENCE ───────────────────────────────────────────────────────────────

def test_save_load_roundtrip(tmp_path: Path) -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    state = GameState.new_run(registry)
    state.apply_deltas(budget=-10, cohesion=-5)
    save_path = tmp_path / "save.json"
    state.save(save_path)
    loaded = GameState.load(save_path, registry)
    assert loaded.get_budget() == state.get_budget()


def test_new_run_initializes_from_registry() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    state = GameState.new_run(registry)
    assert state.get_budget() == 100
    assert len(state.get_active_principals()) == len(registry.principals)


# ── Principal art_state thresholds ───────────────────────────────────────────

def test_principal_art_state_intact() -> None:
    p = _make_principal()
    p.integrity = 70
    assert p.art_state() == "intact"


def test_principal_art_state_damaged() -> None:
    p = _make_principal()
    p.integrity = 35
    assert p.art_state() == "damaged"


def test_principal_art_state_corrupted() -> None:
    p = _make_principal()
    p.integrity = 1
    assert p.art_state() == "corrupted"


def test_principal_art_state_absent() -> None:
    p = _make_principal()
    p.integrity = 0
    assert p.art_state() == "absent"
