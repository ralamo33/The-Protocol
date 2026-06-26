from __future__ import annotations

import random
from dataclasses import dataclass

from engine.game_state import GameState, RoundRecord
from engine.loader import Anomaly, Experiment, Management, Principal


@dataclass
class RoundResult:
    success: bool
    cohesion_delta: int
    effectiveness_delta: int
    capability_delta: int
    personnel_status: str
    narrative_key: str
    roll: int
    final: int


def resolve(
    state: GameState,
    anomaly: Anomaly,
    principal: Principal,
    experiment: Experiment,
    management: Management,
    cycle: int,
) -> RoundResult:
    roll = random.randint(0, 100)
    skill_bonus = principal.skills.containment * 2
    roll_penalty = state.get_roll_penalty()
    tech_bonus = state.get_tech_bonus()

    final = roll + skill_bonus + experiment.roll.modifier + tech_bonus - roll_penalty
    success = final >= experiment.roll.base_difficulty

    outcome = experiment.success if success else experiment.failure

    state.apply_deltas(
        cohesion=outcome.cohesion_delta + management.cost.cohesion_delta,
        effectiveness=outcome.effectiveness_delta + management.cost.effectiveness_delta,
        capability=outcome.capability_delta,
        budget=outcome.budget_delta - management.cost.budget_cost,
    )

    result = RoundResult(
        success=success,
        cohesion_delta=outcome.cohesion_delta,
        effectiveness_delta=outcome.effectiveness_delta,
        capability_delta=outcome.capability_delta,
        personnel_status=outcome.personnel_status,
        narrative_key=outcome.narrative_key,
        roll=roll,
        final=final,
    )
    return result
