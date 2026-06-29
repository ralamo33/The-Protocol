"""TEST-00 — Startup schema gate.

Loads all TOML via ContentRegistry.load_from_dir(). Validates Pydantic.
Checks cross-references and file paths via entity.load(registry).

Bump EXPECTED_* counts as content is authored — these are the single source
of truth for what has been authored and validated.
"""

from pathlib import Path

import pytest

from engine.loader import ContentRegistry

DATA_DIR = Path(__file__).parent.parent / "data"

# Bump as content is authored — MVP targets in comments
EXPECTED_PRINCIPALS  = 1   # MVP target: 3
EXPECTED_ANOMALIES   = 3   # MVP target: 6
EXPECTED_EXPERIMENTS = 1   # MVP target: 15
EXPECTED_MANAGEMENT  = 3   # MVP target: ~9


def test_content_registry_counts() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    assert len(registry.principals)  == EXPECTED_PRINCIPALS
    assert len(registry.anomalies)   == EXPECTED_ANOMALIES
    assert len(registry.experiments) == EXPECTED_EXPERIMENTS
    assert len(registry.management)  == EXPECTED_MANAGEMENT


def test_all_entities_load() -> None:
    """Each entity resolves its dependencies — passes if no exception is raised."""
    registry = ContentRegistry.load_from_dir(DATA_DIR)

    for principal in registry.principals.values():
        principal.load(registry)  # resolves signature_experiment, voice pools, art files

    for anomaly in registry.anomalies.values():
        anomaly.load(registry)    # resolves experiments, management_methods, art file

    for experiment in registry.experiments.values():
        experiment.load(registry) # resolves comms pool keys

    for mgmt in registry.management.values():
        mgmt.load(registry)       # no-op for now; extends naturally as deps are added
