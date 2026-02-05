from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, get_args, override

from rich.highlighter import Highlighter
from rich.logging import RichHandler

from magical_athlete_simulator.core.palettes import get_racer_color
from magical_athlete_simulator.core.types import (
    AbilityName,
    BoardModifierName,
    RacerModifierName,
    RacerName,
)

if TYPE_CHECKING:
    from rich.text import Text

    from magical_athlete_simulator.engine.game_engine import GameEngine

RACER_NAMES = set(get_args(RacerName))
ABILITY_NAMES = set(get_args(AbilityName))
RACER_MODIFIER_NAMES = set(get_args(RacerModifierName))
BOARD_MODIFIER_NAMES = set(get_args(BoardModifierName))

# --- PATTERNS ---
ABILITY_PATTERN = re.compile(rf"\b({'|'.join(map(re.escape, ABILITY_NAMES))})\b")
RACER_MODIFIER_PATTERN = re.compile(
    rf"\b({'|'.join(map(re.escape, RACER_MODIFIER_NAMES))})\b",
)
BOARD_MODIFIER_PATTERN = re.compile(
    rf"\b({'|'.join(map(re.escape, BOARD_MODIFIER_NAMES))})\b",
)

# Regex to capture the prefix (numbers/dots/separators) AND the name
# Captures: "0.1:Banana" or "1•Banana" or "0:Banana"
# Group 1 (prefix): "0.1:" or "1•"
# Group 2 (name): "Banana"
RACER_COMPOSITE_PATTERN = re.compile(
    rf"(?P<prefix>[\d\.]*[:•])(?P<name>{'|'.join(map(re.escape, RACER_NAMES))})\b",
)

COLOR = {
    "move": "bold #23d18b",  # light green
    "warp": "bold #87d700",  # yellow-ish green
    "main_move": "bold #319e31",  # mid green
    "warning": "bold bright_red",
    "ability": "bold #29b8db",  # cyan
    "prefix": "grey50",
    "level": "bold",
    "modifier": "bold #ffaf00",  # orange
    "board": "bold #d670d6",  # magenta
    "dice_roll": "bold #f5f543",  # yellow
}


class ContextFilter(logging.Filter):
    """Inject per-engine runtime context into every log record."""

    def __init__(self, engine: GameEngine, name: str = "") -> None:
        super().__init__(name)
        self.engine: GameEngine = engine

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        logctx = self.engine.log_context
        record.total_turn = logctx.total_turn
        record.turn_log_count = logctx.turn_log_count
        record.racer_repr = logctx.current_racer_repr
        record.engine_id = logctx.engine_id
        record.engine_level = logctx.engine_level
        logctx.inc_log_count()
        return True


class RichMarkupFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        total_turn = getattr(record, "total_turn", 0)
        turn_log_count = getattr(record, "turn_log_count", 0)
        racer_repr = getattr(record, "racer_repr", "_")
        engine_level = getattr(record, "engine_level", 0)
        engine_id = getattr(record, "engine_id", 0)

        # We construct the prefix string here
        prefix = (
            f"{engine_level}:{engine_id} {total_turn}.{racer_repr}.{turn_log_count}"
        )
        message = record.getMessage()

        # Apply the base grey color to the prefix.
        # The Highlighter will apply stronger colors on top of this.
        return f"[{COLOR['prefix']}]{prefix:<19}[/{COLOR['prefix']}]  {message}"


class GameLogHighlighter(Highlighter):
    @override
    def highlight(self, text: Text) -> None:
        # 1. Standard Regex Highlighting
        text.highlight_regex(r"\bMove\b", COLOR["move"])
        text.highlight_regex(r"\bMoving\b", COLOR["move"])
        text.highlight_regex(r"\bPushing\b", COLOR["warp"])
        text.highlight_regex(r"\bMainMove\b", COLOR["main_move"])
        text.highlight_regex(r"\bWarp\b", COLOR["warp"])
        text.highlight_regex(r"\bBOARD\b", COLOR["board"])
        text.highlight_regex(r"\bDice Roll\b", COLOR["dice_roll"])
        text.highlight_regex(ABILITY_PATTERN, COLOR["ability"])
        text.highlight_regex(RACER_MODIFIER_PATTERN, COLOR["modifier"])
        text.highlight_regex(BOARD_MODIFIER_PATTERN, COLOR["board"])

        text.highlight_regex(r"!!!", COLOR["warning"])
        text.highlight_regex(r"\bVP:\b", "bold yellow")
        text.highlight_regex(r"\b\+1 VP\b", "bold green")
        text.highlight_regex(r"\b-1 VP\b", "bold red")

        # 2. Dynamic Racer Highlighting
        # We iterate over matches to apply specific colors per racer
        for match in RACER_COMPOSITE_PATTERN.finditer(text.plain):
            prefix_span = match.span("prefix")  # e.g., "0.1:" or "1•"
            name_span = match.span("name")  # e.g., "Banana"
            racer_name = match.group("name")

            # Get the Hex Color (e.g., "#FFE135")
            hex_color = get_racer_color(racer_name)

            # A. Color the Prefix (Index/Bullet) with the Racer's specific color
            # We assume the color is a hex string. Rich accepts matching hex style.
            if prefix_span[0] != -1:
                text.stylize(hex_color, start=prefix_span[0], end=prefix_span[1])

            # B. Color the Name itself Bold White (as requested)
            text.stylize("bold white", start=name_span[0], end=name_span[1])


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = RichHandler(
        markup=True,
        show_path=False,
        show_time=False,
        highlighter=GameLogHighlighter(),
    )
    handler.setFormatter(RichMarkupFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
