# The Protocol — Schema Plan

Read `01-architecture.md` and `02-technical.md` first for game design and technical context.

This document records all data schema decisions made in the design session. Everything here is **locked** unless noted as provisional.

---

## Core Architecture Principle

**Anomaly** and **Principal** are the two load-bearing data entities. All other data — Experiments, Management protocols, Communications — attaches to one or both of them. GameState holds resources. Personnel are derived counts, not a stored value.

---

## Core Game Loop (per Cycle)

```
New Anomaly arrives (title + brief only shown)
  → Assign Principal
  → Choose Management Protocol (1 standard, 1 principal's, 1 anomaly-specific)
  → Choose Experiment (1 principal signature, 2 anomaly-specific)
  → Event Roll (may fire — neutral, not inherently good or bad)
  → Experiment Resolves (personnel pool depletes)
  → End State Check
      Cohesion = 0       → INHUMAN ENDING
      Effectiveness = 0  → CONTAINMENT FAILURE
      All resolved       → FULL CONTAINMENT (good ending)
      Otherwise          → Next cycle
```

Key constraint: **Management Protocol is chosen before the Experiment**, not after. It shapes experiment conditions and outcomes.

Anomalies persist in the facility across cycles. Their Profile (knowledge) also persists. New anomalies are added each cycle alongside existing ones.

---

## Final Terminology

All names below are locked. In-game display name listed first; code name in `code_style`.

### Resources (GameState values)

| Concept | Final Name | Code Name | Visibility |
|---|---|---|---|
| Humanity / Morale (merged) | COHESION | `cohesion` | hidden |
| Pressure / Fear (merged) | EFFECTIVENESS | `effectiveness` | hidden |
| Budget | BUDGET | `budget` | **shown** |
| Tech Level | CAPABILITY | `capability` | hidden |
| Knowledge (per-anomaly) | PROFILE | `profile` | hidden |
| Round Counter | CYCLE | `cycle` | hidden |
| Director degradation | DIRECTOR INTEGRITY | `director_integrity` | hidden |
| Personnel pools | (see below) | derived | derived |

**COHESION** — Combined moral erosion + supernatural decay. At 0 → INHUMAN ENDING. Drives narrative tone (reports become cold, names become IDs) and a hidden roll penalty. "Are you still recognisable as human?"

**EFFECTIVENESS** — How well containment is working. Starts high, decays toward 0. Merges external fear and internal pressure into one clinical number. At 0 → CONTAINMENT FAILURE.

**BUDGET** — The only resource shown to the player. Spent on management protocols. Creates hard choices: spend now or save.

**CAPABILITY** — Accumulated research. Expressed as a sliding number with distinct tiers (not a raw count). Unlocks new experiments and management protocols silently — player discovers by seeing options appear, never receives a notification.

**PROFILE** — Entity-specific knowledge expressed as a percentage. 100% = file complete. Per-anomaly, persists across cycles alongside the anomaly itself. Earned by running study experiments on that specific entity. Unlocks better management options for that anomaly.

**CYCLE** — Internal counter. Hidden. Used to gate certain anomaly appearances (e.g. KETER class only appears in cycles 5–6). Player infers time passing from context, never sees a number.

**DIRECTOR INTEGRITY** — The Director's own degradation, parallel to Principal integrity. At low levels, log language becomes bureaucratically cold: "3 personnel resources lost" instead of "3 people died." The player may not notice it shifting until it's already happened.

### Data Entities (TOML files, loaded at startup)

| Concept | Final Name | Code Name | Notes |
|---|---|---|---|
| Anomaly | ANOMALY | `anomaly` | |
| Scientist / Lead | PRINCIPAL | `principal` | "Principal Scientist" at intro; "Principal" in-game & code |
| Experiment | EXPERIMENT | `experiment` | |
| Containment Protocol | MANAGEMENT | `management` | chosen *before* experiment |
| Incident | EVENT | `event` | neutral; may branch into subtypes |
| Narrative Bank | COMMUNICATIONS | `comms` | |
| Equipment | ASSET | `asset` | provisional |

**ANOMALY** — Title and brief only shown to player. "Brief" is the canonical term for description in this game — clinical, not narrative. Persists in facility across cycles. Owns 2 unique experiments and 1 unique management protocol.

**PRINCIPAL** — Named lead characters. Major leaders and genius researchers. Introduced as "Principal Scientist" at game start; referred to as "Principal" for brevity in all in-game text and code. Owns 1 signature experiment and 1 management protocol. Can be killed, transformed, or incapacitated.

**EXPERIMENT** — Title and a hint-only description shown to player. Risk level, difficulty, roll modifiers, and outcome consequences are all hidden. Implementation: data in `.toml`, outcome logic in co-located `.py`. File structure: `experiment/<slug>/<name>.toml` and `experiment/<slug>/<name>.py`.

**MANAGEMENT** — The containment approach, chosen before the experiment runs. Three options per cycle: 1 standard (always available), 1 tied to the assigned Principal, 1 unique to the current anomaly. Choice shapes experiment conditions and outcomes — it is not a post-experiment cleanup step.

**EVENT** — A conditional game-loop interruption. Not inherently positive or negative. Fires based on game state conditions. May branch into typed subtypes in future development.

**COMMUNICATIONS** — Template line pools per context (Principal voice, anomaly flavor, outcome text). Drawn in no-repeat queues; reshuffled when exhausted. One TOML file per pool.

**ASSET** *(provisional)* — Obtained obscurely through experiment outcomes. Description is intentionally cryptic. Effects manifest as new options appearing — player discovers rather than receives. No tech tree, no upgrade screen.

### Personnel Categories

Three separate pool counts. Derived from assignment and incident state — not stored as a single number. Player sees absences (fewer options available), never counts.

| Name | Code Name | Depleted by |
|---|---|---|
| Researcher | `researcher` | Assignment to study/analysis experiments |
| Security | `security` | Assignment to management protocols involving physical threat |
| Engineer | `engineer` | Assignment to advanced management protocols (infrastructure) |

Personnel start unassigned each cycle and are assigned to experiments or management protocols as part of the round setup. Assignment depletes the pool for that cycle even when the outcome is a success. Incidents from failed experiments can permanently reduce pool size.

### Endings

| Ending | Code Name | Trigger | Tone |
|---|---|---|---|
| INHUMAN ENDING | `ending_inhuman` | Cohesion = 0 | The Foundation is monstrous. You are indistinguishable from them. Final file is the Director's own anomaly entry. |
| CONTAINMENT FAILURE | `ending_breach` | Effectiveness = 0 | Containment failed. The last report is filed by no one. |
| FULL CONTAINMENT | `ending_win` | All anomalies resolved | Genuine good ending. Thanks to your sacrifices and good judgement — the world is safe. Player should feel accomplished. |

---

## Open / Provisional Items

- **ASSET** effects list: directionally confirmed (cryptic acquisition, discovered not received) but specific effects not locked. Do not commit to an effect list until content authoring begins.
- **CAPABILITY tiers**: number of tiers and threshold values not set. Design alongside experiment content so unlocks feel earned, not arbitrary.
- **EVENT subtypes**: neutral for MVP. May branch into typed categories (positive, negative, anomalous, personnel) in post-MVP.
- **Personnel starting counts**: pool sizes per cycle not set. Tune against experiment and management authoring.

---

## What Has NOT Changed From 02-technical.md

- TOML + Pydantic validation for all data entities
- No SQL; runtime state in JSON save file
- Co-located art files per Principal and Anomaly
- No-repeat shuffle queues for Communications pools
- `GameState` encapsulation: resources never returned as raw numbers, only derived signals
- `str.format_map()` for template rendering
- Textual TUI framework, Python 3.11+, uv/ruff/ty toolchain
