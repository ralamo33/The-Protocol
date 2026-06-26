from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from engine.game_state import EndingType


class EndScreen(Screen):
    """Shown when an end condition triggers."""

    def __init__(self, ending: EndingType) -> None:
        super().__init__()
        self._ending = ending

    def compose(self) -> ComposeResult:
        yield Static(self._ending_text())

    def _ending_text(self) -> str:
        match self._ending:
            case EndingType.INHUMAN:
                return "INHUMAN ENDING\n\nThe Foundation is indistinguishable from the anomalies it contains."
            case EndingType.BREACH:
                return "CONTAINMENT FAILURE\n\nThe last report was filed by no one."
            case EndingType.WIN:
                return "FULL CONTAINMENT\n\nThe world is safe. You know what it cost."
