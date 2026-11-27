"""Pin the interpretations listed under "Open questions" in docs/second_wind_analysis.md.

Each test documents the current behaviour so a designer ruling shows up as a failing test.
"""

from typing import override

from magsim.core.agent import (
    Agent,
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)
from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.mastermind import AbilityMastermindPredict
from magsim.racers.mr_dice_guy import MrDiceGuyMoreAbility

BUST = [1, 2, 3, 4, 5, 6]


class AlwaysUse(Agent):
    def __init__(self) -> None:
        self.asked: list[str] = []

    @override
    def make_boolean_decision(
        self, engine, ctx: DecisionContext[BooleanInteractive]
    ) -> bool:
        self.asked.append(ctx.source.name)  # pyright: ignore[reportAttributeAccessIssue]
        return True

    @override
    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        self.asked.append(ctx.source.name)  # pyright: ignore[reportAttributeAccessIssue]
        return max(ctx.options, key=lambda o: o.position)  # pyright: ignore[reportAttributeAccessIssue]


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def cfg(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


def positions(game: GameScenario) -> list[int | None]:
    return [r.position for r in game.state.racers]


def test_show_off_counting_die_is_the_first_die(scenario: type[GameScenario]):
    """Open question: Show-Off's roll-triggers (e.g. Magical Athlete's) see only the first die, not the chain total."""
    game = scenario(
        [RacerConfig(0, "ShowOff", start_pos=0), dummy(1, 20)],
        dice_rolls=[1, 2, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_values == (1, 2, 6)
    assert game.state.roll_state.dice_value == 1


def test_mr_dice_guy_counting_die_is_the_picked_duplicate(
    scenario: type[GameScenario],
):
    """Open question: Mr. Dice Guy's single dice_value is the duplicated number he moves by."""
    game = scenario(
        [RacerConfig(0, "MrDiceGuy", start_pos=0), dummy(1, 20)],
        dice_rolls=[4, 4, 1, 2, 3, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_value == 4


def test_mr_dice_guy_bust_has_no_counting_die(scenario: type[GameScenario]):
    """Open question: a no-duplicate bust leaves dice_value None, so telemetry and dice_value readers ignore it."""
    game = scenario(
        [RacerConfig(0, "MrDiceGuy", start_pos=0), dummy(1, 20)],
        dice_rolls=[1, 2, 3, 4, 5, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_value is None
    assert len(game.state.roll_state.dice_values) == 6


def test_dicemonger_reroll_after_bust_gives_a_move(scenario: type[GameScenario]):
    """Open question: a no-duplicate bust can be rerolled; the new duplicate moves him and Dicemonger gains 1."""
    game = scenario(
        [cfg(0, "MrDiceGuy"), cfg(1, "Dicemonger", 10), dummy(2, 20)],
        dice_rolls=[*BUST, 2, 2, 4, 5, 6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 2
    assert game.get_racer(1).position == 11


def test_bust_reroll_is_once_per_turn_so_a_second_bust_ends_the_move(
    scenario: type[GameScenario],
):
    """Open question: only one Dicemonger reroll per turn, so a second bust means no move and no extra profit."""
    game = scenario(
        [cfg(0, "MrDiceGuy"), cfg(1, "Dicemonger", 10), dummy(2, 20)],
        dice_rolls=[*BUST, *BUST],
    )

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 11


def test_bust_without_a_reroll_source_means_no_move(scenario: type[GameScenario]):
    """Open question: without a reroll source the bust skips the main move."""
    game = scenario(
        [cfg(0, "MrDiceGuy"), dummy(1, 20)],
        dice_rolls=[*BUST, 3, 3, 1, 2, 4, 5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_magician_rerolls_a_bust_up_to_twice(scenario: type[GameScenario]):
    """Open question: Magician's two rerolls apply to a Mr. Dice Guy bust."""
    game = scenario(
        [cfg(0, "Magician"), dummy(1, 20)],
        dice_rolls=[1, 1, 2, 3, 4, 5],
    )
    game.engine.grant_ability(0, MrDiceGuyMoreAbility())

    game.run_turn()

    assert game.get_racer(0).position == 1


def test_mr_dice_guy_party_pooper_rerolls_each_six_die(
    scenario: type[GameScenario],
):
    """Open question: every die is a roll, so sixes are rerolled per die and Pooper moves once for it."""
    game = scenario(
        [cfg(0, "MrDiceGuy"), cfg(1, "PartyPooper", 10), dummy(2, 20)],
        dice_rolls=[6, 1, 2, 3, 3, 4, 5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert game.get_racer(1).position == 11


def test_mr_dice_guy_next_to_stunner_forces_all_six_dice_to_one(
    scenario: type[GameScenario],
):
    """Open question: every die is a roll, so all six are forced to 1, a duplicate, and he moves 1."""
    game = scenario(
        [cfg(0, "MrDiceGuy", 10), cfg(1, "Stunner", 10), dummy(2, 30)],
        dice_rolls=[6, 5, 4, 3, 2, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 11


def test_show_off_party_pooper_rerolls_sixes_in_the_chain(
    scenario: type[GameScenario],
):
    """Open question: a 6 in Show-Off's chain is rerolled before he sees it, and Pooper moves 1."""
    game = scenario(
        [cfg(0, "ShowOff"), cfg(1, "PartyPooper", 10), dummy(2, 20)],
        dice_rolls=[6, 4],
    )

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.get_racer(1).position == 11


def test_show_off_next_to_stunner_busts_on_the_second_roll(
    scenario: type[GameScenario],
):
    """Open question: forced 1s, the first is low so he keeps rolling and the next is equal, a bust."""
    game = scenario(
        [cfg(0, "ShowOff", 10), cfg(1, "Stunner", 10), dummy(2, 30)],
        dice_rolls=[5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 10


def test_pooper_moves_at_the_reroll_before_the_roller_moves(
    scenario: type[GameScenario],
):
    """Open question: Pooper moves at the reroll, so he is already 1 ahead when the roller's
    Overtaker bonus is counted, rather than moving after the roller."""
    game = scenario(
        [cfg(0, "Overtaker"), cfg(1, "PartyPooper"), dummy(2)],
        dice_rolls=[6, 2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 1
    assert game.get_racer(0).position == 3


def test_saboteur_does_not_trigger_when_the_main_move_is_replaced(
    scenario: type[GameScenario],
):
    """Open question: Magical Athlete's 3 warps instead of moving, so Scoocher sees only MA's trigger, not Saboteur's."""
    game = scenario(
        [
            cfg(0, "MagicalAthlete"),
            cfg(1, "LeSaboteur"),
            cfg(2, "Scoocher"),
            dummy(3, 20),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(2).position == 1
    assert game.get_racer(0).position == 20


def test_saboteur_reverses_mr_dice_guy_when_the_3_is_not_the_duplicate(
    scenario: type[GameScenario],
):
    """Open question: any 3 among the six dice reverses him, even though he moves by the 5s."""
    game = scenario(
        [cfg(0, "MrDiceGuy", 10), cfg(1, "LeSaboteur")],
        dice_rolls=[3, 5, 5, 1, 2, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_saboteur_sends_show_off_backwards_by_his_whole_total(
    scenario: type[GameScenario],
):
    """Open question: a 3 at any point of the chain reverses the entire summed distance."""
    game = scenario(
        [cfg(0, "ShowOff", 20), cfg(1, "LeSaboteur")],
        dice_rolls=[1, 3, 5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 11


def test_tripped_penguin_passing_banana_mid_move_ends_tripped(
    scenario: type[GameScenario],
):
    """Open question: recovery fires right after his move, so a trip picked up during that move persists."""
    game = scenario(
        [cfg(0, "Penguin", 2), cfg(1, "Banana", 4), dummy(2, 20)],
        dice_rolls=[2],
    )
    game.engine.get_racer(0).tripped = True

    game.run_turn()

    racer = game.get_racer(0)
    assert racer.position == 6
    assert racer.tripped is True


def test_tripped_penguin_landing_on_a_trip_tile_mid_move_ends_tripped(
    scenario: type[GameScenario],
):
    """Open question: a trip tile hit during his doubled move leaves him tripped for the next turn."""
    game = scenario(
        [cfg(0, "Penguin", 1), dummy(1, 20)],
        dice_rolls=[2],
        board=BOARD_DEFINITIONS["WildWilds"](),
    )
    game.engine.get_racer(0).tripped = True

    game.run_turn()

    racer = game.get_racer(0)
    assert racer.position == 5
    assert racer.tripped is True


def test_penguin_re_tripped_mid_move_still_rolls_double_next_turn(
    scenario: type[GameScenario],
):
    """Open question: he is never forced to lose a turn, the re-trip only keeps the doubled roll going."""
    game = scenario(
        [cfg(0, "Penguin", 1), dummy(1, 20)],
        dice_rolls=[2, 1, 4],
        board=BOARD_DEFINITIONS["WildWilds"](),
    )
    game.engine.get_racer(0).tripped = True

    game.run_turns(3)

    racer = game.get_racer(0)
    assert racer.position == 5 + 8
    assert racer.tripped is False


def test_gloth_gets_bonus_when_spoilsport_cancels_race(
    scenario: type[GameScenario],
):
    """Open question: Gloth's race-end bonus also fires when Spoilsport cancels the race."""
    game = scenario(
        [cfg(0, "Spoilsport"), cfg(1, "Gloth", 5)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(1).victory_points == 3


def test_legs_and_mole_trade_main_roll_only_once(scenario: type[GameScenario]):
    """Open question: the first power to claim the main-roll trade wins, so Legs + Mole never combine."""
    agent = AlwaysUse()
    game = scenario(
        [
            RacerConfig(0, "Legs", abilities={"LongLegs", "MoleTunnel"}, agent=agent),
            cfg(1, "Centaur", 20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert len(agent.asked) == 1
    assert (
        game.get_racer(0).position == {"LongLegs": 5, "MoleTunnel": 6}[agent.asked[0]]
    )


def test_legs_and_flip_flop_trade_main_roll_only_once(scenario: type[GameScenario]):
    """Open question: Legs and Flip Flop never swap and then move 5."""
    agent = AlwaysUse()
    game = scenario(
        [
            RacerConfig(0, "Legs", abilities={"LongLegs", "FlipFlopSwap"}, agent=agent),
            cfg(1, "Centaur", 20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert len(agent.asked) == 1
    expected = {"LongLegs": (5, 20), "FlipFlopSwap": (20, 0)}[agent.asked[0]]
    assert (game.get_racer(0).position, game.get_racer(1).position) == expected


def test_mush_with_granted_legs_and_mole_trades_once(scenario: type[GameScenario]):
    """Open question: copied roll-replacing powers also share the single trade per turn."""
    agent = AlwaysUse()
    game = scenario(
        [RacerConfig(0, "Mush", agent=agent), cfg(1, "Centaur", 20)],
        dice_rolls=[1],
    )
    for name in ("Legs", "Mole"):
        for ability in game.engine.instantiate_racer_abilities(name):
            game.engine.grant_ability(0, ability, persistent=True)

    game.run_turn()

    assert len(agent.asked) == 1
    assert (
        game.get_racer(0).position == {"LongLegs": 5, "MoleTunnel": 6}[agent.asked[0]]
    )


def test_centaur_passing_legs_and_null_pushes_nobody_back(
    scenario: type[GameScenario],
):
    """Open question: Centaur lands ahead of Null, so it is stripped before its passes resolve.
    Current behavior: neither Legs nor Null is trampled. Without Null, both would go back 2.
    """
    game = scenario(
        [cfg(0, "Centaur", 1), cfg(1, "Legs", 2), cfg(2, "Null", 3)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert positions(game) == [4, 2, 3]


def test_null_passing_a_stripped_banana_gets_tripped_by_it(
    scenario: type[GameScenario],
):
    """Open question: Banana is stripped while ahead of Null and regains its power the moment Null passes it.
    Current behavior: Banana's passing trip fires on Null.
    """
    game = scenario(
        [cfg(0, "Null", 3), cfg(1, "Banana", 5), cfg(2, "Legs", 20)],
        dice_rolls=[4],
    )
    assert not game.get_racer(1).active_abilities

    game.run_turn()

    assert game.get_racer(0).position == 7
    assert game.get_racer(0).tripped
    assert game.get_racer(1).active_abilities


def test_mastermind_stripped_on_first_turn_predicts_once_he_regains_his_power(
    scenario: type[GameScenario],
):
    """Open question: "at the start of my first turn" vs a Mastermind that skipped that turn while stripped.
    Current behavior: he predicts at the first turn start after Null passes him.
    """
    game = scenario(
        [cfg(0, "Mastermind", 6), cfg(1, "Null", 5), cfg(2, "Legs", 20)],
        dice_rolls=[1, 3, 1, 1],
    )
    assert not game.get_racer(0).active_abilities

    game.run_turns(3)

    mastermind = game.get_racer(0)
    assert game.get_racer(1).position == 8
    stashed = next(
        a
        for a in mastermind.active_abilities
        if isinstance(a, AbilityMastermindPredict)
    )
    assert stashed.prediction is None

    game.run_turn()

    assert stashed.prediction is not None


class PickByName(Agent):
    """Always uses powers and picks the option with the given racer name."""

    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def make_boolean_decision(
        self, engine, ctx: DecisionContext[BooleanInteractive]
    ) -> bool:
        return True

    @override
    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return next(
            o
            for o in ctx.options
            if getattr(o, "racer_name", getattr(o, "name", None)) == self.name
        )


def test_show_off_extra_dice_do_not_make_scoocher_move(scenario: type[GameScenario]):
    """Open question: Show-Off's power never registers as used, so Scoocher ignores his extra dice."""
    game = scenario(
        [
            RacerConfig(0, "ShowOff", agent=BaselineAgent()),
            cfg(1, "Scoocher", 20),
            dummy(2, 25),
        ],
        dice_rolls=[2, 5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 7
    assert game.get_racer(1).position == 20


def test_mr_dice_guy_roll_does_not_make_scoocher_move(scenario: type[GameScenario]):
    """Open question: Mr. Dice Guy's six-dice roll never registers as a power use for Scoocher."""
    game = scenario(
        [cfg(0, "MrDiceGuy"), cfg(1, "Scoocher", 20), dummy(2, 25)],
        dice_rolls=[4, 4, 1, 2, 3, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.get_racer(1).position == 20


def test_stunner_forced_roll_does_not_make_scoocher_move(scenario: type[GameScenario]):
    """Open question: Stunner forcing a 1 never registers as a power use for Scoocher."""
    game = scenario(
        [dummy(0, 10), cfg(1, "Stunner", 11), cfg(2, "Scoocher", 20)],
        dice_rolls=[6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 11
    assert game.get_racer(2).position == 20


def test_understudy_copying_mastermind_and_mastermind_both_claim_second(
    scenario: type[GameScenario],
):
    """Open question: both copies of Mastermind's power predict the winner and both finish 2nd."""
    game = scenario(
        [
            RacerConfig(0, "Understudy", agent=PickByName("Mastermind")),
            RacerConfig(1, "Mastermind", agent=PickByName("Centaur")),
            cfg(2, "Centaur", 29),
        ],
        dice_rolls=[1],
    )
    game.engine.agents[0] = PickByName("Centaur")

    game.run_turns(3)

    assert [r.finish_position for r in game.state.racers] == [2, 2, 1]
    assert [r.victory_points for r in game.state.racers] == [2, 2, 4]
