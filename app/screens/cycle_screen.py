from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Static

from engine.game_state import EndingType, GameState
from engine.loader import Anomaly, ContentRegistry, Management

_SEP = "─" * 62

_MGMT_ORDER = ["soft_watch", "standard_cage", "max_suppress"]


class CycleScreen(Screen):
    BINDINGS = [
        Binding("1", "select_1", "Option 1", show=False),
        Binding("2", "select_2", "Option 2", show=False),
        Binding("3", "select_3", "Option 3", show=False),
        Binding("space", "advance", "Continue", show=False),
        Binding("enter", "advance", "Continue", show=False),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    CycleScreen {
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
    .anomaly-id {
        color: #2a4050;
        padding: 1 0 0 0;
    }
    .anomaly-name {
        color: #e2e8f0;
        text-style: bold;
    }
    .briefing {
        color: #c8e8f0;
        padding: 1 0;
    }
    .section-label {
        color: #06b6d4;
        text-style: bold;
        padding: 1 0 0 0;
    }
    .option {
        color: #8ab8c8;
        padding: 0 0 0 2;
    }
    .result-ok {
        color: #4ade80;
        padding: 1 0;
        text-style: bold;
    }
    .result-bad {
        color: #f87171;
        padding: 1 0;
        text-style: bold;
    }
    .hint {
        color: #2a4050;
        padding: 1 0;
    }
    """

    def __init__(self, state: GameState, registry: ContentRegistry) -> None:
        super().__init__()
        self._state = state
        self._registry = registry
        self._current_anomaly: Anomaly | None = None
        self._phase = "choosing"
        self._cycle_num = 0
        self._total = len(registry.anomalies)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="scroll"):
            yield Static("", id="header", classes="header", markup=True)
            yield Static(_SEP, classes="sep")
            yield Static("", id="anomaly-id", classes="anomaly-id", markup=True)
            yield Static("", id="anomaly-name", classes="anomaly-name", markup=True)
            yield Static("", id="briefing", classes="briefing")
            yield Static(_SEP, classes="sep")
            yield Static("", id="section-label", classes="section-label")
            yield Static("", id="opt-1", classes="option", markup=True)
            yield Static("", id="opt-2", classes="option", markup=True)
            yield Static("", id="opt-3", classes="option", markup=True)
            yield Static("", id="result", markup=True)
            yield Static(_SEP, classes="sep")
            yield Static("", id="hint", classes="hint")

    def on_mount(self) -> None:
        self._next_anomaly()

    # ── Navigation ────────────────────────────────────────────────────────

    def _next_anomaly(self) -> None:
        anomaly_id = self._state.pop_next_anomaly()
        if anomaly_id is None:
            self._go_to_ending()
            return
        self._current_anomaly = self._registry.anomalies[anomaly_id]
        self._cycle_num += 1
        self._phase = "choosing"
        self._render_choosing()

    def _go_to_ending(self) -> None:
        from app.screens.end_screen import EndScreen

        ending = self._state.check_ending() or EndingType.WIN
        self.app.push_screen(EndScreen(ending))

    # ── Rendering ─────────────────────────────────────────────────────────

    def _render_choosing(self) -> None:
        anomaly = self._current_anomaly
        assert anomaly is not None

        self.query_one("#header", Static).update(
            f"CYCLE {self._cycle_num} OF {self._total}  ·  MANAGEMENT ASSIGNMENT"
        )
        self.query_one("#anomaly-id", Static).update(anomaly.display_id)
        self.query_one("#anomaly-name", Static).update(
            f"[bold {anomaly.color}]{anomaly.name.upper()}[/]"
        )
        self.query_one("#briefing", Static).update(
            anomaly.briefing or "No brief on file."
        )
        self.query_one("#section-label", Static).update("MANAGEMENT PROTOCOL")
        self.query_one("#result", Static).update("")
        self.query_one("#result", Static).remove_class("result-ok", "result-bad")

        for i, mgmt_id in enumerate(_MGMT_ORDER, 1):
            mgmt = self._registry.management.get(mgmt_id)
            label = f"[bold]{mgmt_id}[/]" if mgmt is None else (
                f"[[{i}]  [bold]{mgmt.name}[/bold]\n"
                f"     {mgmt.description}"
            )
            self.query_one(f"#opt-{i}", Static).update(label)

        self.query_one("#hint", Static).update(
            "Press [1], [2], or [3] to assign a Management Protocol."
        )

    def _render_result(self, mgmt: Management, net: int) -> None:
        for i in range(1, 4):
            self.query_one(f"#opt-{i}", Static).update("")
        self.query_one("#section-label", Static).update("")

        result_widget = self.query_one("#result", Static)
        if net >= 0:
            result_widget.set_classes("result-ok")
            result_widget.update(
                f"→ {mgmt.name.upper()} assigned. Containment holding."
            )
        else:
            result_widget.set_classes("result-bad")
            result_widget.update(
                f"→ {mgmt.name.upper()} assigned. Containment degraded."
            )

        ending = self._state.check_ending()
        if ending is not None:
            self.query_one("#hint", Static).update(
                "Press SPACE or ENTER to view the final report."
            )
        else:
            self.query_one("#hint", Static).update(
                "Press SPACE or ENTER to continue."
            )

        self._phase = "result"

    # ── Actions ───────────────────────────────────────────────────────────

    def _apply_selection(self, mgmt_id: str) -> None:
        if self._phase != "choosing":
            return
        anomaly = self._current_anomaly
        if anomaly is None:
            return
        mgmt = self._registry.management.get(mgmt_id)
        if mgmt is None:
            return

        net = mgmt.cost.effectiveness_delta - anomaly.pressure.base_per_round
        self._state.apply_deltas(effectiveness=net)
        self._state.advance_cycle()
        self._render_result(mgmt, net)

    def action_select_1(self) -> None:
        self._apply_selection(_MGMT_ORDER[0])

    def action_select_2(self) -> None:
        self._apply_selection(_MGMT_ORDER[1])

    def action_select_3(self) -> None:
        self._apply_selection(_MGMT_ORDER[2])

    def action_advance(self) -> None:
        if self._phase != "result":
            return
        ending = self._state.check_ending()
        if ending is not None:
            self._go_to_ending()
        else:
            self._next_anomaly()

    def action_quit(self) -> None:
        self.app.exit()
