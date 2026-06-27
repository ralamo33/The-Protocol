from textual.app import App

from app.screens.log_screen import LogScreen


class FoundationApp(App):
    """The Protocol — Foundation Containment Management System."""

    TITLE = "The Protocol"

    CSS = """
    Screen {
        background: #080c0e;
        color: #8ab8c8;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(LogScreen())
