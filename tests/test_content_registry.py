"""TEST-00 — Startup smoke test. All content loads and validates."""

from pathlib import Path

import pytest

from engine.loader import ContentRegistry

DATA_DIR = Path(__file__).parent.parent / "data"


def test_content_registry_loads() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    assert isinstance(registry, ContentRegistry)


def test_principals_load() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    assert len(registry.principals) >= 1
    assert "morrow" in registry.principals


def test_morrow_principal_valid() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    morrow = registry.principals["morrow"]
    assert morrow.name == "Dr. Elara Morrow"
    assert morrow.color == "#06b6d4"
    assert morrow.tone == "CLINICAL"
    assert morrow.skills.containment == 8


def test_morrow_art_files_exist() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    morrow = registry.principals["morrow"]
    for state, art_path in morrow.art_paths.items():
        assert art_path.exists(), f"Missing art file for state '{state}': {art_path}"


def test_comms_pools_load() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    assert "morrow_success" in registry.comms
    assert "morrow_failure" in registry.comms
    assert len(registry.comms["morrow_success"]) >= 1


def test_narrative_queues_build() -> None:
    registry = ContentRegistry.load_from_dir(DATA_DIR)
    queues = registry.build_narrative_queues()
    assert "morrow_success" in queues
    assert len(queues["morrow_success"]) >= 1
