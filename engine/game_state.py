from __future__ import annotations

import json
import random
from collections import deque
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from engine.loader import Anomaly, Principal, PrincipalStatus

if TYPE_CHECKING:
    from engine.loader import ContentRegistry


EFFECTIVENESS_FAILURE_THRESHOLD = 50

_DEFAULT_RESEARCHER = 5
_DEFAULT_SECURITY = 3
_DEFAULT_ENGINEER = 2


class EndingType(str, Enum):
    INHUMAN = "INHUMAN"
    BREACH = "BREACH"
    WIN = "WIN"


class Ledger(BaseModel):
    cohesion: int = 100
    effectiveness: int = 100
    budget: int = 100
    capability: int = 0
    cycle: int = 0
    director_integrity: int = 100


class Personnel(BaseModel):
    researcher: int = _DEFAULT_RESEARCHER
    security: int = _DEFAULT_SECURITY
    engineer: int = _DEFAULT_ENGINEER


class RoundRecord(BaseModel):
    cycle: int
    anomaly_id: str
    principal_id: str
    experiment_id: str
    management_id: str
    outcome: str
    narrative: str


class GameState:
    """All raw ledger values are private. Only derived signals are public."""

    def __init__(
        self,
        ledger: Ledger,
        principals: dict[str, Principal],
        anomaly_queue: list[Anomaly],
        history: list[RoundRecord],
        narrative_queues: dict[str, deque[str]],
        personnel: Personnel | None = None,
    ) -> None:
        self._ledger = ledger
        self._principals = principals
        self._anomaly_queue = anomaly_queue
        self._history = history
        self._narrative_queues = narrative_queues
        self._personnel = personnel or Personnel()

    # ── Public read — derived signals only ───────────────────────────────

    def get_active_principals(self) -> list[Principal]:
        return [p for p in self._principals.values() if p.status == PrincipalStatus.ACTIVE]

    def get_budget(self) -> int:
        return self._ledger.budget

    def get_cycle(self) -> int:
        return self._ledger.cycle

    def get_roll_penalty(self) -> int:
        loss = 100 - self._ledger.cohesion
        return int(loss * 0.3)

    def get_tone_modifier(self) -> str:
        if self._ledger.cohesion >= 70:
            return "WARM"
        if self._ledger.cohesion >= 40:
            return "NEUTRAL"
        return "COLD"

    def is_cohesion_critical(self) -> bool:
        return self._ledger.cohesion <= 20

    def is_effectiveness_critical(self) -> bool:
        return self._ledger.effectiveness <= 20

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
            lines = list(self._narrative_queues[pool_key])
            random.shuffle(lines)
            self._narrative_queues[pool_key] = deque(lines)
        return line

    # ── Public write ──────────────────────────────────────────────────────

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
        self._ledger.director_integrity = max(
            0, min(100, self._ledger.director_integrity + director_integrity)
        )

    def advance_cycle(self) -> None:
        self._ledger.cycle += 1
        self._personnel = Personnel()
        for principal in self._principals.values():
            if principal.status == PrincipalStatus.INCAPACITATED:
                principal.rounds_incapacitated -= 1
                if principal.rounds_incapacitated <= 0:
                    principal.status = PrincipalStatus.ACTIVE
                    principal.rounds_incapacitated = 0

    def pop_next_anomaly(self) -> Anomaly | None:
        if self._anomaly_queue:
            return self._anomaly_queue.pop(0)
        return None

    def record_round(self, record: RoundRecord) -> None:
        self._history.append(record)

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "ledger": self._ledger.model_dump(),
            "principals": {
                pid: {
                    "integrity": p.integrity,
                    "status": p.status.value,
                    "rounds_incapacitated": p.rounds_incapacitated,
                }
                for pid, p in self._principals.items()
            },
            "anomaly_queue": [a.id for a in self._anomaly_queue],
            "history": [r.model_dump() for r in self._history],
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path, registry: ContentRegistry) -> GameState:
        data = json.loads(path.read_text())
        ledger = Ledger(**data["ledger"])
        principals: dict[str, Principal] = {}
        for pid, state in data["principals"].items():
            p = registry.principals[pid].model_copy(deep=True)
            p.integrity = state["integrity"]
            p.status = PrincipalStatus(state["status"])
            p.rounds_incapacitated = state["rounds_incapacitated"]
            principals[pid] = p
        anomaly_queue = [registry.anomalies[aid] for aid in data["anomaly_queue"]]
        history = [RoundRecord(**r) for r in data["history"]]
        queues = registry.build_narrative_queues()
        return cls(ledger, principals, anomaly_queue, history, queues)

    @classmethod
    def new_run(cls, registry: ContentRegistry) -> GameState:
        anomaly_ids = list(registry.anomalies.keys())
        random.shuffle(anomaly_ids)
        anomaly_queue = [registry.anomalies[aid] for aid in anomaly_ids]
        principals = {pid: p.model_copy(deep=True) for pid, p in registry.principals.items()}
        queues = registry.build_narrative_queues()
        return cls(Ledger(), principals, anomaly_queue, [], queues)
