from __future__ import annotations

import tomllib
from collections import deque
from pathlib import Path

from pydantic import BaseModel, Field


# ── Principal schema ───────────────────────────────────────────────────────────

class PrincipalSkills(BaseModel):
    containment: int
    research: int
    risk_tolerance: int


class PrincipalArt(BaseModel):
    intact: str
    damaged: str
    corrupted: str
    absent: str = ""


class PrincipalVoice(BaseModel):
    success_pool: str
    failure_pool: str
    incident_pool: str = ""


class Principal(BaseModel):
    id: str
    name: str
    title: str
    color: str
    tone: str
    signature_experiment: str
    bio: str = ""
    transforms_into: str = ""
    skills: PrincipalSkills
    art: PrincipalArt
    voice: PrincipalVoice
    # resolved at load time — absolute paths
    art_paths: dict[str, Path] = Field(default_factory=dict)


# ── Anomaly schema ─────────────────────────────────────────────────────────────

class AnomalyPressure(BaseModel):
    base_per_round: int
    max_rounds: int


class AnomalyOutcomeWeights(BaseModel):
    cohesion_cost: list[int] = [-10, -2]
    effectiveness_delta: list[int] = [-5, 5]
    capability_gain: list[int] = [2, 10]
    personnel_risk: float = 0.3


class Anomaly(BaseModel):
    id: str
    display_id: str
    classification: str  # SAFE | EUCLID | KETER
    name: str
    descriptors: list[str] = []
    threat_level: int
    art_file: str
    experiments: list[str]
    management_methods: list[str]
    pressure: AnomalyPressure
    outcome_weights: AnomalyOutcomeWeights = Field(default_factory=AnomalyOutcomeWeights)
    briefing: str = ""
    art_path: Path | None = None


# ── Experiment schema ──────────────────────────────────────────────────────────

class ExperimentRoll(BaseModel):
    base_difficulty: int
    modifier: int = 0


class ExperimentOutcome(BaseModel):
    cohesion_delta: int = 0
    effectiveness_delta: int = 0
    capability_delta: int = 0
    budget_delta: int = 0
    personnel_status: str = "SAFE"
    narrative_key: str


class Experiment(BaseModel):
    id: str
    name: str
    description: str
    risk_level: str  # LOW | MEDIUM | HIGH
    requires_capability: int = 0
    roll: ExperimentRoll
    success: ExperimentOutcome
    failure: ExperimentOutcome


# ── Management schema ──────────────────────────────────────────────────────────

class ManagementCost(BaseModel):
    cohesion_delta: int = 0
    budget_cost: int = 0
    effectiveness_delta: int = 0


class Management(BaseModel):
    id: str
    name: str
    description: str
    requires_capability: int = 0
    requires_experiment: str = ""
    cost: ManagementCost
    narrative_success: str = ""
    narrative_flavor: str = ""


# ── Content Registry ───────────────────────────────────────────────────────────

class ContentRegistry:
    """Loaded once at startup. All content validated through Pydantic."""

    def __init__(self) -> None:
        self.principals: dict[str, Principal] = {}
        self.anomalies: dict[str, Anomaly] = {}
        self.experiments: dict[str, Experiment] = {}
        self.management: dict[str, Management] = {}
        self.comms: dict[str, list[str]] = {}  # pool_key → lines

    @classmethod
    def load_from_dir(cls, data_dir: str | Path) -> "ContentRegistry":
        root = Path(data_dir)
        registry = cls()
        registry._load_principals(root / "principals")
        registry._load_anomalies(root / "anomalies")
        registry._load_experiments(root / "experiments")
        registry._load_management(root / "management")
        registry._load_comms(root / "comms")
        return registry

    def _load_principals(self, path: Path) -> None:
        if not path.exists():
            return
        for principal_dir in path.iterdir():
            if not principal_dir.is_dir():
                continue
            toml_files = list(principal_dir.glob("*.toml"))
            if not toml_files:
                continue
            data = tomllib.loads(toml_files[0].read_text())
            p = Principal(**data["principal"])
            # Resolve art paths relative to principal directory
            p.art_paths = {
                "intact": principal_dir / p.art.intact,
                "damaged": principal_dir / p.art.damaged,
                "corrupted": principal_dir / p.art.corrupted,
            }
            if p.art.absent:
                p.art_paths["absent"] = principal_dir / p.art.absent
            self.principals[p.id] = p

    def _load_anomalies(self, path: Path) -> None:
        if not path.exists():
            return
        for anomaly_dir in path.iterdir():
            if not anomaly_dir.is_dir():
                continue
            toml_files = list(anomaly_dir.glob("*.toml"))
            if not toml_files:
                continue
            data = tomllib.loads(toml_files[0].read_text())
            a = Anomaly(**data["anomaly"])
            a.art_path = anomaly_dir / a.art_file
            self.anomalies[a.id] = a

    def _load_experiments(self, path: Path) -> None:
        if not path.exists():
            return
        for toml_file in path.rglob("*.toml"):
            data = tomllib.loads(toml_file.read_text())
            e = Experiment(**data["experiment"])
            self.experiments[e.id] = e

    def _load_management(self, path: Path) -> None:
        if not path.exists():
            return
        for toml_file in path.rglob("*.toml"):
            data = tomllib.loads(toml_file.read_text())
            m = Management(**data["management"])
            self.management[m.id] = m

    def _load_comms(self, path: Path) -> None:
        if not path.exists():
            return
        for toml_file in path.rglob("*.toml"):
            data = tomllib.loads(toml_file.read_text())
            for pool_key, pool_data in data.items():
                if "lines" in pool_data:
                    self.comms[pool_key] = pool_data["lines"]

    def build_narrative_queues(self) -> dict[str, deque[str]]:
        import random
        queues = {}
        for key, lines in self.comms.items():
            shuffled = lines[:]
            random.shuffle(shuffled)
            queues[key] = deque(shuffled)
        return queues
