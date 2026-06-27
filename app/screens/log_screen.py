from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Static

_P1 = (
    "You are the [bold cyan]Director[/]. You do not get a title beyond that. "
    "The Foundation does not celebrate its leadership — it consumes them."
)
_P2 = (
    "Anomalies arrive. They are [bold cyan]real[/], they are [bold cyan]dangerous[/], "
    "and they are [bold cyan]already here[/]. Your mandate is containment. "
    "Not understanding. Not elimination. [bold #d4a006]Containment.[/]"
)
_SEP = "─" * 62


class LogScreen(Screen):
    DEFAULT_CSS = """
    LogScreen {
        background: #080c0e;
    }
    #scroll {
        padding: 0 4;
    }
    .header {
        color: #06b6d4;
        padding: 1 0 0 0;
        text-style: bold;
    }
    .sep {
        color: #1e3040;
    }
    .briefing {
        color: #c8e8f0;
        padding: 1 0;
    }
    .hint {
        color: #2a4050;
        padding: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="scroll"):
            yield Static(
                "THE PROTOCOL  ·  FOUNDATION CONTAINMENT MANAGEMENT SYSTEM",
                classes="header",
            )
            yield Static(_SEP, classes="sep")
            yield Static(_P1, classes="briefing", markup=True)
            yield Static(_P2, classes="briefing", markup=True)
            yield Static(_SEP, classes="sep")
            yield Static("q · quit", classes="hint")
