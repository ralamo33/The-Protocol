from __future__ import annotations

import random
from dataclasses import dataclass

from engine.game_state import GameState, RoundRecord
from engine.loader import Anomaly, Experiment, Management, Principal


@dataclass
class RoundResult:
    success: bool
    effectiveness_delta: int
    roll: int
    final: int
    narrative_pool: str


def resolve(
    state: GameState,
    anomaly: Anomaly,
    principal: Principal,
    experiment: Experiment,
    management: Management,
    cycle: int,
) -> RoundResult:
    roll = random.randint(0, 100)
    roll_penalty = state.get_roll_penalty()
    final = roll - roll_penalty
    success = final >= experiment.roll.base_difficulty

    effectiveness_delta = (
        experiment.pressure_on_success if success else experiment.pressure_on_failure
    )

    state.apply_deltas(
        effectiveness=effectiveness_delta,
        cohesion=management.cost.cohesion,
        budget=-management.cost.budget,
    )

    narrative_pool = principal.voice.success_pool if success else principal.voice.failure_pool

    return RoundResult(
        success=success,
        effectiveness_delta=effectiveness_delta,
        roll=roll,
        final=final,
        narrative_pool=narrative_pool,
    )
