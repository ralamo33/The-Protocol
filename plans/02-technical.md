# The Protocol — Technical Plan

Read `01-architecture.md` first for game design context and locked decisions.

---

## Ground Rules

- **No SQL database.** Content lives in TOML files (one file per entity). Runtime state lives in a JSON save file. TOML is human-readable, diff-friendly, and Claude generates it cleanly.
- **Pydantic v2 for schema validation.** Every TOML entity has a Pydantic model. Load = parse TOML → validate → in-memory Python object. Content errors surface at startup, not mid-game.
- **GameState is encapsulated (Encapsulation pattern).** All attributes are private (`_ledger`, `_scientists`). All access goes through public methods. Humanity is never returned as a raw number — only derived signals like `is_humanity_critical()` and `get_tone_modifier()`.

---

## Toolchain

| Tool | Role | Command |
|------|------|---------|
| `uv` | Package manager + venv (replaces pip + virtualenv) | `uv init the_protocol` · `uv add textual pydantic` |
| `ruff` | Linter + formatter (replaces flake8 + black) | `uv run ruff check .` · `uv run ruff format .` |
| `ty` | Type checker (replaces mypy, Astral-native) | `uv run ty check .` |

Require Python 3.11+ in `pyproject.toml` (for stdlib `tomllib`).

---

## Key Packages

### Tier 1 — Essential Core
| Package | Purpose |
|---------|---------|
| `textual` | TUI framework. Widgets, CSS layout, reactive state, keyboard/mouse. Key classes: `App`, `Widget`, `ScrollableContainer`, `Static` |
| `pydantic` | Data validation for all content schemas and game state. Use `model_validate()` from TOML dicts |
| `tomllib` | Built into Python 3.11+. Parses TOML → Python dict → feed to Pydantic. Use `tomli-w` for writing |
| `rich` | Textual dependency. Use directly for `Text` objects with per-character color. `Text.from_markup()` for inline colored spans |

### Tier 2 — Important
| Package | Purpose |
|---------|---------|
| `steamworks.py` | Steamworks SDK bindings. Achievements, cloud saves, overlay. Wrap in `SteamManager` that no-ops when Steam isn't running (dev mode). Init in `try/except`. |
| `pyinstaller` | Bundles app + interpreter into binary. Use `--collect-data textual` for CSS assets. Alternative: Nuitka (compiles to C, smaller binary, slower build). |
| `loguru` | Structured logging to `~/.local/share/the_protocol/logs/`. Use `logger.bind(round=n)` for context. |
| `platformdirs` | Cross-platform user data dirs. `user_data_dir("the_protocol")` returns correct path on Win/Mac/Linux. |

### Tier 3 — Dev/Test
| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Required since Textual is async |

---

## Data Schema

### Content Storage Layout (TOML files, shipped with game)

```
data/
├── scientists/
│   ├── morrow/
│   │   ├── morrow.toml      # schema + metadata
│   │   ├── intact.txt       # ASCII art co-located here
│   │   ├── damaged.txt
│   │   ├── corrupted.txt
│   │   └── absent.txt
│   ├── vasquez/
│   └── redacted/
├── anomalies/
│   ├── scp_031/
│   │   ├── scp_031.toml
│   │   └── art.txt
│   └── ...                  # 5 more
├── experiments/             # 15 flat .toml files
├── containment/             # flat .toml files
└── narrative/               # template banks (.toml)
```

Art files are **co-located with their entity** — not in a separate assets/ directory.

### Scientist TOML Schema

```toml
[scientist]
id          = "morrow"
name        = "Dr. Elara Morrow"
title       = "Senior Containment Specialist"
color       = "#06b6d4"       # hex — all text/art tinted this color
tone        = "CLINICAL"      # CLINICAL | RECKLESS | RESIGNED | PARANOID
signature_experiment = "proximate_analysis"

bio         = "Joined after the Event."  # optional, shown on hover
transforms_into = "anomaly_morrow"       # optional, if scientist transforms

[scientist.skills]  # 1–10, modifies resolution roll
containment    = 8
research       = 6
risk_tolerance = 4   # higher = rolls better under pressure

[scientist.art]
intact    = "intact.txt"      # relative to scientist's directory
damaged   = "damaged.txt"
corrupted = "corrupted.txt"
absent    = "absent.txt"      # optional

[scientist.voice]
success_pool = "morrow_success"   # references narrative template bank
failure_pool = "morrow_failure"
incident_pool = "morrow_incident"  # optional
```

### Anomaly TOML Schema

```toml
[anomaly]
id              = "scp_031"
display_id      = "SCP-031"
classification  = "EUCLID"    # SAFE | EUCLID | KETER
name            = "[DATA EXPUNGED]"
descriptors     = ["crystalline", "resonant"]
threat_level    = 3           # 1–5, affects base roll difficulty
art_file        = "art.txt"   # relative to anomaly's directory

experiments     = ["proximate_study", "resonance_test"]   # the 2 anomaly-specific experiments
containment_methods = ["standard_lock", "resonance_cage"]

[anomaly.pressure]
base_per_round  = 8           # pressure added each round while uncontained
max_rounds      = 3           # forced failure if not resolved within N rounds

[anomaly.outcome_weights]
humanity_cost   = [-15, -3]   # [min, max] range on success
tech_gain       = [5, 20]
personnel_risk  = 0.4         # probability of personnel incident on failure

[anomaly.narrative]
briefing        = "Anomaly text shown in the briefing log"
success_pool    = "scp_031_success"
failure_pool    = "scp_031_failure"
incident_pool   = "scp_031_incident"  # optional
```

### Experiment TOML Schema

```toml
[experiment]
id           = "resonance_test"
name         = "Resonance Frequency Test"
description  = "Expose the anomaly to calibrated sound frequencies."
risk_level   = "HIGH"         # LOW | MEDIUM | HIGH — shown to player
requires_tech = 0             # minimum tech_level to unlock

[experiment.roll]             # hidden from player
base_difficulty = 55          # roll must beat this
modifier        = -10         # added to roll (+good, -bad)

[experiment.success]
humanity_delta   = -8
tech_delta       = 18
pressure_delta   = -25        # reduces anomaly pressure
personnel_status = "SAFE"
narrative_key    = "resonance_success"

[experiment.failure]
humanity_delta   = -15
tech_delta       = 3
pressure_delta   = 10         # increases pressure on failure
personnel_status = "INCIDENT" # triggers fate roll (death/transform/incapacitate)
narrative_key    = "resonance_failure"
```

### Containment TOML Schema

```toml
[containment]
id           = "resonance_cage"
name         = "Resonance Isolation Cage"
description  = "Dampens frequency emissions."
requires_tech  = 20           # locked until tech_level >= 20
requires_experiment = "resonance_test"  # must run experiment first

[containment.cost]
humanity_delta   = -5
tech_cost        = 0          # some advanced containment spends tech
pressure_resolve = -40        # fully resolves anomaly pressure

[containment.narrative]
success  = "Containment narrative text"
flavor   = "Short flavor shown in log"  # optional
```

Containment does **not** have a success/failure roll — it always works if selected. The risk was already borne by the experiment.

### Save State (JSON)

```json
{
  "run_id": "a3f7c2d1",
  "round": 4,
  "anomaly_queue": ["scp_031", "scp_047", "scp_012"],

  "scientists": {
    "morrow": { "integrity": 74, "status": "ACTIVE", "rounds_incapacitated": 0 },
    "vasquez": { "integrity": 45, "status": "INCAPACITATED", "rounds_incapacitated": 2 }
  },

  "ledger": {
    "humanity": 42,
    "tech_level": 31,
    "anomaly_pressure": 67
  },

  "history": [
    {
      "round": 1,
      "anomaly_id": "scp_031",
      "scientist_id": "morrow",
      "experiment_id": "resonance_test",
      "containment_id": "resonance_cage",
      "outcome": "SUCCESS",
      "narrative": "Rendered text stored here for scroll history"
    }
  ]
}
```

Save location (via `platformdirs`):
- Linux: `~/.local/share/the_protocol/saves/`
- Windows: `%APPDATA%\the_protocol\saves\`
- Mac: `~/Library/the_protocol/saves/`

---

## Project Structure

```
the_protocol/                   # repo root
├── main.py                     # entry point: App() + Steam init
├── pyproject.toml              # managed by uv

├── app/
│   ├── game.py                 # FoundationApp(textual.App)
│   ├── screens/
│   │   ├── log_screen.py       # main scrollable log
│   │   └── end_screen.py       # ending sequence
│   └── widgets/
│       ├── art_panel.py        # renders ASCII art inline
│       ├── choice_row.py       # selectable option widget
│       └── log_entry.py        # a single log line/block

├── engine/
│   ├── game_state.py           # GameState (encapsulated, private attrs)
│   ├── resolution.py           # ResolutionEngine.resolve()
│   ├── narrative.py            # NarrativeEngine.render()
│   └── loader.py               # ContentRegistry, loads all TOML at startup

└── data/                       # all content shipped with game
    ├── scientists/              # entity directories with co-located art
    ├── anomalies/
    ├── experiments/
    ├── containment/
    └── narrative/               # template banks (.toml)

# User data (NOT in repo, persisted to user filesystem)
# ~/.local/share/the_protocol/
#   ├── saves/
#   │   ├── run_current.json
#   │   └── run_history/
#   ├── logs/the_protocol.log
#   └── config.json
```

---

## GameState — Encapsulation Interface

```python
class GameState:
    # Private — no direct access from outside
    _ledger: Ledger
    _scientists: dict[str, ScientistState]
    _history: list[RoundRecord]
    _narrative_queues: dict[str, deque[str]]  # no-repeat pools

    # Public read interface
    def get_scientist(self, id: str) -> ScientistState: ...
    def get_active_scientists(self) -> list[ScientistState]: ...
    def get_tech_level(self) -> int: ...
    def get_round(self) -> int: ...

    # Derived signals — humanity NEVER returned raw
    def is_humanity_critical(self) -> bool: ...
    def get_tone_modifier(self) -> float: ...  # used by narrative engine
    def get_roll_penalty(self) -> int: ...     # used by resolution engine

    # Public write interface — controlled mutations only
    def apply_outcome(self, result: RoundResult) -> None: ...
    def tick_pressure(self, delta: int) -> None: ...
    def tick_incapacitation(self) -> None: ...  # called each round start

    # Persistence
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "GameState": ...
    @classmethod
    def new_run(cls, registry: ContentRegistry) -> "GameState": ...
```

---

## Resolution Engine

```python
def resolve(state, anomaly, scientist, experiment, containment):
    roll = random.randint(0, 100)
    skill_bonus = scientist.skills.containment * 2
    humanity_penalty = state.get_roll_penalty()        # hidden
    tech_bonus = state.get_tech_level() // 10

    final = roll + skill_bonus + experiment.roll.modifier + tech_bonus - humanity_penalty
    success = final >= experiment.roll.base_difficulty

    # Apply outcome (mutates state via public methods only)
    outcome = experiment.success if success else experiment.failure
    state.apply_outcome(RoundResult(
        success=success,
        humanity_delta=outcome.humanity_delta,
        tech_delta=outcome.tech_delta,
        pressure_delta=outcome.pressure_delta,
        personnel_status=outcome.personnel_status
    ))
    # Apply containment (always succeeds)
    state.tick_pressure(containment.cost.pressure_resolve)

    return RoundResult(success=success, ...)
```

---

## Narrative Engine

```python
def render(template_key: str, context: dict, state: GameState) -> str:
    # Get next line from no-repeat queue
    line = state.pop_narrative_line(template_key)

    # Fill template variables via str.format_map
    return line.format_map(context)

# context dict example:
context = {
    "scientist_name": "Dr. Morrow",
    "anomaly_descriptor": "crystalline",
    "experiment_verb": "subjected",
    "outcome_text": "minimal casualties reported",
}
```

Templates in TOML (narrative/morrow_voice.toml):
```toml
[morrow_success]
lines = [
    "{scientist_name} completed {experiment_verb} of the {anomaly_descriptor} entity. {outcome_text}.",
    "SCP file updated. {scientist_name}: containment achieved via {experiment_verb}. {outcome_text}.",
]
```

---

## Textual Widget Architecture

```
FoundationApp (textual.App)
└── LogScreen (Screen) — the only screen during play
    └── ScrollableContainer — single scrollable log
        ├── LogEntry (Static) — past round text, read-only
        ├── ArtPanel (Static, styled with scientist.color) — ASCII art inline
        └── ChoiceRow (Widget) — active selection interface
            └── SelectionWidget (focusable) — posts SelectionMade message on press

EndScreen (Screen) — shown when end condition triggers
```

**Key Textual pattern:** When a player makes a selection, `ChoiceRow` posts a `SelectionMade(choice_id)` message. `LogScreen` handles it, calls `ResolutionEngine.resolve()`, receives a `RoundResult`, mounts new `LogEntry` + `ArtPanel` widgets into the `ScrollableContainer`, and scrolls to bottom.

---

## Window Mode

Self-contained terminal window — not the user's existing terminal. Steam launch commands:
- Windows: `wt.exe -e python main.py`
- Linux: `xterm -e python main.py` (or `kitty python main.py`)
- Mac: bundled via pyinstaller with a terminal launcher

Art column width: 44 chars. Minimum window: 80×24. Textual enforces this with a startup size check.

---

## Testing Strategy

### TEST-00 — Startup Smoke Test (run first in CI)
Validates all content loads successfully through Pydantic. Catches schema breaks before anything else runs.

```python
def test_content_registry_loads_all():
    registry = ContentRegistry.load_from_dir("data/")

    assert len(registry.scientists) == 3
    assert len(registry.anomalies) == 6
    assert len(registry.experiments) == 15

    # All cross-references resolve
    for anomaly in registry.anomalies.values():
        for exp_id in anomaly.experiments:
            assert exp_id in registry.experiments

    # All art files exist on disk
    for sci in registry.scientists.values():
        for art_path in [sci.art.intact, sci.art.damaged, sci.art.corrupted]:
            assert Path(art_path).exists()
```

### TEST-01 — Unit Tests with `pytest.mark.parametrize`
Critical isolated logic: resolution engine roll computation, integrity → art state thresholds, ledger mutations, save/load round-trips.

```python
@pytest.mark.parametrize("humanity,expected_max_roll", [
    (100, 110),  # full humanity → no penalty
    (50,  100),  # mid → small penalty
    (0,    80),  # zero humanity → -30 penalty
])
def test_humanity_penalty(humanity, expected_max_roll): ...

@pytest.mark.parametrize("integrity,expected_art", [
    (100, "intact"), (70, "intact"),
    (69, "damaged"), (35, "damaged"),
    (34, "corrupted"), (1, "corrupted"),
    (0, "absent"),
])
def test_art_state_thresholds(integrity, expected_art): ...
```

### TEST-02 — Integration Tests
Full round and run simulations using real content files. Tests the complete pipeline: load → create state → simulate round → assert ledger changes and narrative output. Also tests that a run can reach all three end conditions.

### TEST-03 — `/review` Claude Code Skill

Defined in `.claude/skills/review.md`. Invoked with `/review` in Claude Code CLI.

**Steps in order:**
1. **Code review** — reads `git diff` against main, checks for bugs, over-complexity, bad patterns, violations of project conventions (encapsulation, hidden ledger contract, etc.)
2. **Run all tests** — `uv run pytest` (TEST-00, TEST-01, TEST-02 must all pass)
3. **Agent playthrough + recording** — Claude plays the headless game on 3 strategies (cautious/reckless/random), records with `asciinema`, converts to GIF via `agg`, confirms all 3 runs reach a valid end condition
4. **Create PR** with:
   - 3–5 word title
   - Description explaining what changed
   - "Key Files" section pointing reviewers to relevant code
   - GIF recording embedded in PR body

**PR template:**
```markdown
## Add resonance containment option

**What changed**
Added resonance_cage containment method for crystalline anomalies.
Unlocks at tech_level 20.

**Key files for review**
- `data/containment/resonance_cage.toml` — new schema
- `engine/resolution.py:L82` — containment unlock logic
- `tests/test_resolution.py` — new parametrize cases

**Playthrough recording**
![cautious run GIF](playthroughs/latest.gif)
Cautious → Full Containment ✓
Reckless → Transformation ✓
Random → completed without crash ✓

🤖 /review — The Protocol
```

---

## All Architecture Decisions — Final State

| Decision | Choice |
|----------|--------|
| ARCH-01 Template engine | `str.format_map()`. Upgrade to Jinja2 only if conditional branches needed. |
| ARCH-02 Content loading | Eager load at startup into `ContentRegistry` singleton. |
| ARCH-03 Scientist color | Tint both the ASCII art panel and all attributed log text. |
| ARCH-04 Narrative pool | No-repeat shuffle queue per pool. Reset when exhausted. |
| ARCH-05 Window mode | Self-contained terminal window (xterm/Windows Terminal subprocess). |
