from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from textual.containers import ScrollableContainer


class LogScreen(Screen):
    """Main game screen — a single scrollable log of all events."""

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Static("THE PROTOCOL — FOUNDATION MANAGEMENT SYSTEM\n\nAwaiting anomaly assignment.")
