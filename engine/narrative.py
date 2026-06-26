from __future__ import annotations

from engine.game_state import GameState


def render(pool_key: str, context: dict, state: GameState) -> str:
    """Draw the next line from a no-repeat pool, fill template variables."""
    line = state.pop_narrative_line(pool_key)
    try:
        return line.format_map(context)
    except KeyError:
        return line
