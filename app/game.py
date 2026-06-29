from pathlib import Path

from textual.app import App

from app.screens.cycle_screen import CycleScreen
from engine.game_state import GameState
from engine.loader import ContentRegistry

_DATA_DIR = Path(__file__).parent.parent / "data"


class FoundationApp(App):
    """The Protocol — Foundation Containment Management System."""

    TITLE = "The Protocol"

    CSS = """
    Screen {
        background: #080c0e;
        color: #8ab8c8;
    }
    """

    def on_mount(self) -> None:
        registry = ContentRegistry.load_from_dir(_DATA_DIR)
        state = GameState.new_run(registry)
        self.push_screen(CycleScreen(state, registry))
