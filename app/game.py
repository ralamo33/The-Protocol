from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from app.screens.log_screen import LogScreen


class FoundationApp(App):
    """The Protocol — Foundation Containment Management System."""

    CSS = """
    Screen {
        background: #080c0e;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        self.push_screen(LogScreen())
