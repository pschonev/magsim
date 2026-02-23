from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magsim.core.modifiers import RacerModifier
    from magsim.engine.game_engine import GameEngine


def add_racer_modifier(engine: GameEngine, target_idx: int, modifier: RacerModifier):
    racer = engine.get_racer(target_idx)
    if modifier not in racer.modifiers:
        racer.modifiers.append(modifier)
        engine.log_debug(f"ENGINE: Added {modifier.name} to {racer.repr}")


def remove_racer_modifier(engine: GameEngine, target_idx: int, modifier: RacerModifier):
    racer = engine.get_racer(target_idx)
    if modifier in racer.modifiers:
        racer.modifiers.remove(modifier)

        engine.log_debug(f"ENGINE: Removed {modifier.name} from {racer.repr}")
