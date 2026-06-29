from __future__ import annotations

import tomllib
from collections import deque
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field


class PrincipalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INCAPACITATED = "INCAPACITATED"
    DEAD = "DEAD"
    TRANSFORMED = "TRANSFORMED"


# ── Principal ──────────────────────────────────────────────────────────────────

class PrincipalArt(BaseModel):
    intact: str
    damaged: str
    corrupted: str


class PrincipalVoice(BaseModel):
    success_pool: str
    failure_pool: str
    incident_pool: str = ""


class Principal(BaseModel):
    # TOML-sourced fields
    id: str
    name: str
    title: str
    color: str
    signature_experiment: str
    brief: str
    art: PrincipalArt
    voice: PrincipalVoice

    # Runtime state carried on Principal (100–70 intact · 69–35 damaged · 34–1 corrupted · 0 absent)
    integrity: int = 100
    status: PrincipalStatus = PrincipalStatus.ACTIVE
    rounds_incapacitated: int = 0

    # Resolved at load time
    art_paths: dict[str, Path] = Field(default_factory=dict)

    def art_state(self) -> str:
        if self.integrity >= 70:
            return "intact"
        if self.integrity >= 35:
            return "damaged"
        if self.integrity >= 1:
            return "corrupted"
        return "absent"

    def load(self, registry: ContentRegistry) -> None:
        """Validate cross-references and file paths. Raises ValueError on missing refs."""
        if self.signature_experiment and self.signature_experiment not in registry.experiments:
            raise ValueError(
                f"Principal '{self.id}': signature_experiment '{self.signature_experiment}' "
                f"not in registry"
            )
        for pool in (self.voice.success_pool, self.voice.failure_pool):
            if pool and pool not in registry.comms:
                raise ValueError(
                    f"Principal '{self.id}': comms pool '{pool}' not in registry"
                )
        if self.voice.incident_pool and self.voice.incident_pool not in registry.comms:
            raise ValueError(
                f"Principal '{self.id}': incident_pool '{self.voice.incident_pool}' "
                f"not in registry"
            )
        for state_name, path in self.art_paths.items():
            if not path.exists():
                raise ValueError(
                    f"Principal '{self.id}': art file for '{state_name}' missing: {path}"
                )


# ── Anomaly ────────────────────────────────────────────────────────────────────

class AnomalyPressure(BaseModel):
    base_per_round: int


class AnomalyEscapeCost(BaseModel):
    security: int = 0
    effectiveness: int = 0


class Anomaly(BaseModel):
    id: str
    display_id: str
    color: str
    name: str
    descriptors: list[str] = []
    threat_level: int
    art_file: str
    experiments: list[str] = []
    management_methods: list[str] = []
    pressure: AnomalyPressure
    brief: str = ""
    escape_cost: AnomalyEscapeCost = Field(default_factory=AnomalyEscapeCost)
    art_path: Path | None = None

    def load(self, registry: ContentRegistry) -> None:
        for eid in self.experiments:
            if eid not in registry.experiments:
                raise ValueError(
                    f"Anomaly '{self.id}': experiment '{eid}' not in registry"
                )
        for mid in self.management_methods:
            if mid not in registry.management:
                raise ValueError(
                    f"Anomaly '{self.id}': management '{mid}' not in registry"
                )
        if self.art_path and not self.art_path.exists():
            raise ValueError(
                f"Anomaly '{self.id}': art file missing: {self.art_path}"
            )


# ── Experiment ─────────────────────────────────────────────────────────────────

class ExperimentPersonnel(BaseModel):
    researcher: int = 0


class ExperimentRoll(BaseModel):
    base_difficulty: int


class Experiment(BaseModel):
    id: str
    name: str
    brief: str
    personnel: ExperimentPersonnel = Field(default_factory=ExperimentPersonnel)
    roll: ExperimentRoll
    pressure_on_success: int = 0
    pressure_on_failure: int = 0

    def load(self, registry: ContentRegistry) -> None:
        pass


# ── Management ─────────────────────────────────────────────────────────────────

class ManagementCost(BaseModel):
    cohesion: int = 0
    budget: int = 0
    security: int = 0
    engineer: int = 0


class ManagementNarrative(BaseModel):
    success: str = ""
    failure: str = ""


class Management(BaseModel):
    id: str
    name: str
    brief: str
    cost: ManagementCost = Field(default_factory=ManagementCost)
    narrative: ManagementNarrative = Field(default_factory=ManagementNarrative)

    def load(self, registry: ContentRegistry) -> None:
        pass


# ── Content Registry ───────────────────────────────────────────────────────────

class ContentRegistry:
    """Loaded once at startup. All content validated through Pydantic."""

    def __init__(self) -> None:
        self.principals: dict[str, Principal] = {}
        self.anomalies: dict[str, Anomaly] = {}
        self.experiments: dict[str, Experiment] = {}
        self.management: dict[str, Management] = {}
        self.comms: dict[str, list[str]] = {}

    @classmethod
    def load_from_dir(cls, data_dir: str | Path) -> ContentRegistry:
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
            p.art_paths = {
                "intact": principal_dir / p.art.intact,
                "damaged": principal_dir / p.art.damaged,
                "corrupted": principal_dir / p.art.corrupted,
            }
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
