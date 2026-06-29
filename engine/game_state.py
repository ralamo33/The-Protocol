from __future__ import annotations

import json
import random
from collections import deque
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from engine.loader import ContentRegistry


EFFECTIVENESS_FAILURE_THRESHOLD = 50


class EndingType(str, Enum):
    INHUMAN = "inhuman"
    BREACH = "breach"
    WIN = "win"


class PrincipalStatus(str, Enum):
    ACTIVE = "active"
    INCAPACITATED = "incapacitated"
    DEAD = "dead"
    TRANSFORMED = "transformed"


class PrincipalState(BaseModel):
    integrity: int = 100  # 100–70 intact, 69–35 damaged, 34–1 corrupted, 0 absent
    status: PrincipalStatus = PrincipalStatus.ACTIVE
    rounds_incapacitated: int = 0

    def art_state(self) -> str:
        if self.integrity >= 70:
            return "intact"
        if self.integrity >= 35:
            return "damaged"
        if self.integrity >= 1:
            return "corrupted"
        return "absent"


class Ledger(BaseModel):
    cohesion: int = 100       # hidden — drives INHUMAN ending at 0
    effectiveness: int = 100  # hidden — drives BREACH ending at 0
    budget: int = 100         # shown to player
    capability: int = 0       # hidden — unlocks experiments/management
    cycle: int = 0            # hidden — internal round counter
    director_integrity: int = 100  # hidden — shapes log language


class RoundRecord(BaseModel):
    cycle: int
    anomaly_id: str
    principal_id: str
    experiment_id: str
    management_id: str
    outcome: str
    narrative: str


class GameState:
    """All game resources are private. Only derived signals are public."""

    def __init__(
        self,
        ledger: Ledger,
        principals: dict[str, PrincipalState],
        anomaly_queue: list[str],
        history: list[RoundRecord],
        narrative_queues: dict[str, deque[str]],
    ) -> None:
        self._ledger = ledger
        self._principals = principals
        self._anomaly_queue = anomaly_queue
        self._history = history
        self._narrative_queues = narrative_queues

    # ── Public read interface ──────────────────────────────────────────────

    def get_principal(self, principal_id: str) -> PrincipalState:
        return self._principals[principal_id]

    def get_active_principals(self) -> list[tuple[str, PrincipalState]]:
        return [
            (pid, state)
            for pid, state in self._principals.items()
            if state.status == PrincipalStatus.ACTIVE
        ]

    def get_budget(self) -> int:
        return self._ledger.budget

    def get_cycle(self) -> int:
        return self._ledger.cycle

    def get_capability(self) -> int:
        return self._ledger.capability

    # ── Derived signals — resources NEVER returned raw ────────────────────

    def is_cohesion_critical(self) -> bool:
        return self._ledger.cohesion <= 20

    def is_effectiveness_critical(self) -> bool:
        return self._ledger.effectiveness <= 20

    def get_tone_modifier(self) -> float:
        """0.0 = warm/human, 1.0 = cold/clinical. Drives narrative selection."""
        return 1.0 - (self._ledger.cohesion / 100.0)

    def get_roll_penalty(self) -> int:
        """Hidden humanity penalty applied to resolution rolls."""
        loss = 100 - self._ledger.cohesion
        return int(loss * 0.3)

    def get_tech_bonus(self) -> int:
        return self._ledger.capability // 10

    def check_ending(self) -> EndingType | None:
        if self._ledger.cohesion <= 0:
            return EndingType.INHUMAN
        if self._ledger.effectiveness <= EFFECTIVENESS_FAILURE_THRESHOLD:
            return EndingType.BREACH
        if not self._anomaly_queue:
            return EndingType.WIN
        return None

    # ── Narrative pool ────────────────────────────────────────────────────

    def pop_narrative_line(self, pool_key: str) -> str:
        q = self._narrative_queues.get(pool_key)
        if not q:
            return "[no narrative]"
        line = q.popleft()
        if not q:
            # Reshuffle when exhausted
            lines = list(self._narrative_queues[pool_key])
            random.shuffle(lines)
            self._narrative_queues[pool_key] = deque(lines)
        return line

    # ── Public write interface ────────────────────────────────────────────

    def apply_deltas(
        self,
        *,
        cohesion: int = 0,
        effectiveness: int = 0,
        budget: int = 0,
        capability: int = 0,
        director_integrity: int = 0,
    ) -> None:
        self._ledger.cohesion = max(0, min(100, self._ledger.cohesion + cohesion))
        self._ledger.effectiveness = max(0, min(100, self._ledger.effectiveness + effectiveness))
        self._ledger.budget = max(0, self._ledger.budget + budget)
        self._ledger.capability = max(0, min(100, self._ledger.capability + capability))
        self._ledger.director_integrity = max(0, min(100, self._ledger.director_integrity + director_integrity))

    def advance_cycle(self) -> None:
        self._ledger.cycle += 1
        for pid, state in self._principals.items():
            if state.status == PrincipalStatus.INCAPACITATED:
                state.rounds_incapacitated -= 1
                if state.rounds_incapacitated <= 0:
                    state.status = PrincipalStatus.ACTIVE
                    state.rounds_incapacitated = 0

    def record_round(self, record: RoundRecord) -> None:
        self._history.append(record)

    def pop_next_anomaly(self) -> str | None:
        if self._anomaly_queue:
            return self._anomaly_queue.pop(0)
        return None

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cycle": self._ledger.cycle,
            "anomaly_queue": self._anomaly_queue,
            "principals": {
                pid: state.model_dump() for pid, state in self._principals.items()
            },
            "ledger": self._ledger.model_dump(),
            "history": [r.model_dump() for r in self._history],
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path, registry: "ContentRegistry") -> "GameState":
        data = json.loads(path.read_text())
        ledger = Ledger(**data["ledger"])
        principals = {pid: PrincipalState(**s) for pid, s in data["principals"].items()}
        history = [RoundRecord(**r) for r in data["history"]]
        queues = registry.build_narrative_queues()
        return cls(ledger, principals, data["anomaly_queue"], history, queues)

    @classmethod
    def new_run(cls, registry: "ContentRegistry") -> "GameState":
        anomaly_ids = list(registry.anomalies.keys())
        random.shuffle(anomaly_ids)
        principals = {pid: PrincipalState() for pid in registry.principals}
        queues = registry.build_narrative_queues()
        return cls(Ledger(), principals, anomaly_ids, [], queues)
