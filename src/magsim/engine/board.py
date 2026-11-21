from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from magsim.core.mixins import (
    ApproachHookMixin,
    LandingHookMixin,
    PositionRemapMixin,
)
from magsim.core.modifiers import SpaceModifier
from magsim.engine.movement import push_move, push_warp
from magsim.engine.twist import TWIST_DECK, TWIST_HANDLERS

if TYPE_CHECKING:
    from magsim.core.events import GameEvent, Phase
    from magsim.core.state import RacerState
    from magsim.core.types import (
        AbilityName,
        BoardName,
        ModifierName,
        Source,
        TwistName,
    )
    from magsim.engine.game_engine import GameEngine

TWISTY_TWIRL_TILE = 13


@dataclass(slots=True)
class Board:
    length: int
    static_features: dict[int, list[SpaceModifier]]
    first_corner: int = 12
    second_turn: int = 15
    twist_after_tile: int | None = None
    dynamic_modifiers: defaultdict[int, list[SpaceModifier]] = field(
        init=False,
        default_factory=lambda: defaultdict(list),
    )
    forced_twists: list[TwistName] = field(default_factory=list)
    banned_twists: frozenset[TwistName] = frozenset()
    twists: list[TwistName] = field(init=False, default_factory=list)

    def draw_twist(
        self,
        engine: GameEngine,
        exclude: tuple[TwistName, ...] = (),
    ) -> TwistName | None:
        """Draw one card; forced cards (tests) are consumed before the random deck.

        Banned and excluded cards are never drawn; None when no card is left.
        """
        if self.forced_twists:
            card = self.forced_twists.pop(0)
        else:
            deck = [
                c
                for c in TWIST_DECK
                if c not in self.banned_twists and c not in exclude
            ]
            if not deck:
                engine.log_info("TWIST: no card left to draw.")
                return None
            card = engine.rng.choice(deck)
        self.twists.append(card)
        engine.log_info(f"TWIST: card drawn: {card}")
        return card

    def draw_twist_on_crossing(
        self,
        start_tile: int,
        end_tile: int,
        engine: GameEngine,
        triggering_idx: int,
        phase: Phase,
    ) -> None:
        """Draw the twist card once, when a move crosses from twist_after_tile to the next."""
        if (
            self.twist_after_tile is None
            or self.twists
            or not start_tile <= self.twist_after_tile < end_tile
        ):
            return
        if (card := self.draw_twist(engine)) is not None:
            TWIST_HANDLERS[card](engine, triggering_idx, phase)

    def mirror(self) -> None:
        """Renumber every tile p -> length - p: tile keys, corners and positions stored in tiles."""

        def flip(tile: int) -> int:
            return self.length - tile

        self.static_features = {
            flip(tile): mods for tile, mods in self.static_features.items()
        }
        self.dynamic_modifiers = defaultdict(
            list,
            {flip(tile): mods for tile, mods in self.dynamic_modifiers.items()},
        )
        for mods in (*self.static_features.values(), *self.dynamic_modifiers.values()):
            for mod in mods:
                if isinstance(mod, PositionRemapMixin):
                    mod.remap_positions(flip)
        self.first_corner = flip(self.first_corner)
        self.second_turn = flip(self.second_turn)

    def register_modifier(
        self,
        tile: int,
        modifier: SpaceModifier,
        engine: GameEngine,
    ) -> None:
        modifiers = self.dynamic_modifiers[tile]

        # Manual deduplication for lists
        # Because eq=True, this prevents adding a second "identical" blocker
        if modifier not in modifiers:
            modifiers.append(modifier)
            engine.log_debug(
                f"BOARD: Registered {modifier.name} (owner={modifier.owner_idx}) at tile {tile}",
            )

    def unregister_modifier(
        self,
        tile: int,
        modifier: SpaceModifier,
        engine: GameEngine,
    ) -> None:
        modifiers = self.dynamic_modifiers.get(tile)

        # eq=True makes "in" work even for new instances
        if not modifiers or modifier not in modifiers:
            engine.log_warning(
                f"BOARD: Failed to unregister {modifier.name} from {tile} - not found.",
            )
            return

        modifiers.remove(modifier)
        engine.log_debug(
            f"BOARD: Unregistered {modifier.name} (owner={modifier.owner_idx}) from tile {tile}",
        )

        if not modifiers:
            self.dynamic_modifiers.pop(tile, None)

    def get_modifiers_at(self, tile: int) -> list[SpaceModifier]:
        static = self.static_features.get(tile, ())
        dynamic = self.dynamic_modifiers.get(tile, ())
        return sorted((*static, *dynamic), key=lambda m: m.priority)

    def resolve_position(
        self,
        target: int,
        moving_racer_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        visited: set[int] = set()
        current = target

        while current not in visited:
            visited.add(current)
            new_target = current

            for mod in (
                mod
                for mod in self.get_modifiers_at(current)
                if isinstance(mod, ApproachHookMixin)
            ):
                redirected = mod.on_approach(current, moving_racer_idx, engine, event)
                if redirected != current:
                    engine.log_info(
                        "%s redirected %s from %s -> %s",
                        mod.name,
                        engine.get_racer(moving_racer_idx).repr,
                        current,
                        redirected,
                    )
                    new_target = redirected
                    break

            if new_target == current:
                return current

            current = new_target

        engine.log_warning("resolve_position loop detected, settling on %s", current)
        return current

    def trigger_on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
        arrived_by: Source | None = None,
    ) -> None:
        for mod in (
            mod
            for mod in self.get_modifiers_at(tile)
            if isinstance(mod, LandingHookMixin)
            and not (arrived_by == "WarpTile" and isinstance(mod, WarpTile))
        ):
            if not engine.get_racer(racer_idx).active:
                return
            current_pos = engine.get_racer_pos(racer_idx)
            if current_pos != tile:
                break
            mod.on_land(tile, racer_idx, phase, engine)

    def dump_state(self, engine: GameEngine):
        """Log the location of all dynamic modifiers currently on the board.

        Useful for debugging test failures.
        """
        engine.log_info("=== BOARD STATE DUMP ===")
        if not self.dynamic_modifiers:
            engine.log_info("  (Board is empty of dynamic modifiers)")
            return

        # Sort by tile index for readability
        active_tiles = sorted(self.dynamic_modifiers.keys())
        for tile in active_tiles:
            mods = self.dynamic_modifiers[tile]
            if mods:
                # Format each modifier as "Name(owner=ID)"
                mod_strs = [f"{m.name}(owner={m.owner_idx})" for m in mods]
                engine.log_info(f"  Tile {tile:02d}: {', '.join(mod_strs)}")
        engine.log_info("========================")


@dataclass
class MoveDeltaTile(SpaceModifier, LandingHookMixin):
    """On landing, queue a move of +delta (forward) or -delta (backward)."""

    delta: int = 0
    priority: int = 5
    owner_idx: int | None = None
    name: AbilityName | ModifierName = "MoveDeltaTile"

    @property
    @override
    def display_name(self) -> str:
        return f"MoveDeltaTile({self.delta})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        if self.delta == 0:
            return
        racer: RacerState = engine.get_racer(
            racer_idx,
        )  # uses existing GameEngine API.[file:1]
        engine.log_debug(
            f"{self.display_name}: Queuing {self.delta} move for {racer.repr}",
        )
        # New move is a separate event, not part of the original main move.[file:1]
        push_move(
            engine,
            self.delta,
            phase=phase,
            moved_racer_idx=racer_idx,
            source=self.name,
            responsible_racer_idx=None,
        )


@dataclass
class WarpTile(SpaceModifier, LandingHookMixin, PositionRemapMixin):
    """On landing, warp to the paired tile. Arriving by warp does not warp back."""

    target: int = 0
    priority: int = 5
    owner_idx: int | None = None
    name: AbilityName | ModifierName = "WarpTile"

    @override
    def remap_positions(self, remap: Callable[[int], int]) -> None:
        self.target = remap(self.target)

    @property
    @override
    def display_name(self) -> str:
        return f"WarpTile(->{self.target})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        push_warp(
            engine,
            self.target,
            phase=phase,
            warped_racer_idx=racer_idx,
            source=self.name,
            responsible_racer_idx=None,
        )


@dataclass
class TripTile(SpaceModifier, LandingHookMixin):
    """On landing, trip the racer (they skip their next main move)."""

    name: AbilityName | ModifierName = "TripTile"
    priority: int = 5
    owner_idx: int | None = None

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        racer = engine.get_racer(racer_idx)
        if racer.tripped:
            return
        racer.tripped = True
        engine.log_info(f"{self.name}: {racer.repr} is now tripped.")


@dataclass
class VictoryPointTile(SpaceModifier, LandingHookMixin):
    """On landing, grant +1 VP (or a configured amount)."""

    amount: int = 1
    priority: int = 5
    owner_idx: int | None = None
    name: AbilityName | ModifierName = "VictoryPointTile"
    consumable: bool = False

    @property
    @override
    def display_name(self) -> str:
        return f"VP(+{self.amount})"

    @override
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        racer = engine.get_racer(racer_idx)
        racer.victory_points += self.amount
        engine.log_info(
            f"{self.display_name}: {racer.repr} gains +{self.amount} VP (now {racer.victory_points}).",
        )
        if self.consumable:
            engine.state.board.unregister_modifier(tile, self, engine)


def build_wild_wilds() -> Board:
    return Board(
        length=30,
        static_features={
            1: [VictoryPointTile(None, amount=1)],
            5: [TripTile(None)],
            7: [MoveDeltaTile(None, delta=3)],
            11: [MoveDeltaTile(None, delta=1)],
            13: [VictoryPointTile(None, amount=1)],
            16: [MoveDeltaTile(None, delta=-4)],
            17: [TripTile(None)],
            23: [MoveDeltaTile(None, delta=2)],
            24: [MoveDeltaTile(None, delta=-2)],
            26: [TripTile(None)],
        },
    )


WHIRL_PAIRS = ((4, 6), (8, 12), (11, 15), (17, 22), (20, 23), (24, 28))


def build_whirly_world() -> Board:
    return Board(
        length=30,
        static_features={
            tile: [WarpTile(None, target=other)]
            for a, b in WHIRL_PAIRS
            for tile, other in ((a, b), (b, a))
        },
    )


BoardFactory = Callable[[], Board]

BOARD_DEFINITIONS: dict[BoardName, BoardFactory] = {
    "Standard": lambda: Board(
        length=30,
        static_features={},
    ),
    "WildWilds": build_wild_wilds,
    "WhirlyWorld": build_whirly_world,
    "TwistyTwirl": lambda: Board(
        length=30,
        static_features={},
        twist_after_tile=TWISTY_TWIRL_TILE,
    ),
}
