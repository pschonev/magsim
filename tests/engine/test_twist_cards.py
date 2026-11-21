from magsim.core.types import TwistName
from magsim.engine.abilities import add_racer_modifier
from magsim.engine.board import BOARD_DEFINITIONS, Board, TripTile, WarpTile
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.engine.twist import (
    ConveyorBeltBonus,
    FixedDie,
    ScryingPoolRule,
    WeremouthPiece,
)
from magsim.racers.bite_mark import WeremouthRampage


def twisty(*forced: TwistName) -> Board:
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = list(forced)
    return board


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "ReRunner", start_pos=start_pos)


def test_forced_twist_overrides_the_random_deck(scenario: type[GameScenario]):
    """Tests need deterministic cards, so a forced card must bypass the rng."""
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.state.board.twists == ["Time Imp"]
    assert game.mock_rng is not None
    assert game.mock_rng.choice.call_count == 0


def test_forced_twists_are_consumed_in_order(scenario: type[GameScenario]):
    """Several forced cards model multi-card draws and must come out in order."""
    game = scenario(
        [plain(0), plain(1)],
        dice_rolls=[1],
        board=twisty("Roast Chicken", "Time Imp"),
    )

    board = game.state.board
    assert board.draw_twist(game.engine) == "Roast Chicken"
    assert board.draw_twist(game.engine) == "Time Imp"
    assert board.forced_twists == []


def test_unforced_draw_uses_the_rng_once(scenario: type[GameScenario]):
    """Without forced cards the deck is sampled exactly once, so seeds stay reproducible."""
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty(),
    )

    game.run_turns(1)

    assert game.mock_rng is not None
    assert game.mock_rng.choice.call_count == 1
    assert len(game.state.board.twists) == 1


def test_roast_chicken_moves_the_last_racer_seven(scenario: type[GameScenario]):
    """Core rule: only the racer in last place moves 7."""
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 14
    assert game.get_racer(1).position == 12
    assert game.get_racer(2).position == 9


def test_roast_chicken_moves_every_racer_tied_for_last(scenario: type[GameScenario]):
    """Ties for last all count as last place and move together."""
    game = scenario(
        [plain(0, 13), plain(1, 3), plain(2, 3), plain(3, 8)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(1).position == 10
    assert game.get_racer(2).position == 10
    assert game.get_racer(3).position == 8


def test_roast_chicken_can_boost_the_triggering_racer_when_it_is_last(
    scenario: type[GameScenario],
):
    """The racer that drew the card is not exempt when it ends the move in last place."""
    game = scenario(
        [plain(0, 13), plain(1, 20), plain(2, 18)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 21


def test_roast_chicken_ignores_finished_and_eliminated_racers(
    scenario: type[GameScenario],
):
    """An eliminated racer on a low tile must not count as last place."""
    game = scenario(
        [plain(0, 13), plain(1, 4), plain(2, 9), plain(3, 11)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )
    game.engine.get_racer(1).eliminate()

    game.run_turns(1)

    assert game.get_racer(2).position == 16
    assert game.get_racer(3).position == 11


def test_time_imp_eliminates_the_triggering_racer(scenario: type[GameScenario]):
    """Core rule: the racer whose move drew the card is eliminated, others are safe."""
    game = scenario(
        [plain(0, 13), plain(1, 2), plain(2, 6)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.get_racer(0).eliminated
    assert not game.get_racer(1).eliminated
    assert not game.get_racer(2).eliminated


def test_time_imp_only_hits_the_racer_that_crossed(scenario: type[GameScenario]):
    """The victim is the crosser, not whoever is taking the turn when later racers move."""
    game = scenario(
        [plain(0, 5), plain(1, 13), plain(2, 0)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(2)

    assert not game.get_racer(0).eliminated
    assert game.get_racer(1).eliminated


def test_time_imp_leaves_the_last_two_racers_one_survivor_who_wins(
    scenario: type[GameScenario],
):
    """Eliminating down to one racer must end the race with that racer as winner."""
    game = scenario(
        [plain(0, 13), plain(1, 2)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.get_racer(0).eliminated
    assert game.get_racer(1).finish_position == 1
    assert not game.state.race_active


def chip_tiles(game: GameScenario) -> set[int]:
    board = game.state.board
    return {
        tile
        for tile in range(board.length)
        if any(m.name == "VictoryPointTile" for m in board.get_modifiers_at(tile))
    }


def test_pinata_puts_a_chip_on_every_empty_space_after_the_first_corner(
    scenario: type[GameScenario],
):
    """Chips cover tile 13 onward except spaces occupied by racers."""
    game = scenario(
        [plain(0, 13), plain(1, 20)],
        dice_rolls=[1],
        board=twisty("Pinata"),
    )

    game.run_turns(1)

    assert chip_tiles(game) == set(range(13, 30)) - {14, 20}


def test_pinata_skips_spaces_that_already_have_a_feature(scenario: type[GameScenario]):
    """Only empty spaces get a chip, so existing board features are not overwritten."""
    board = twisty("Pinata")
    board.static_features[20] = [TripTile(None)]
    game = scenario([plain(0, 13), plain(1)], dice_rolls=[1], board=board)

    game.run_turns(1)

    assert 20 not in chip_tiles(game)
    assert 21 in chip_tiles(game)


def test_pinata_chip_is_taken_by_the_first_racer_who_stops_on_it(
    scenario: type[GameScenario],
):
    """Chips are one-shot: the second racer stopping on the same space gets nothing."""
    game = scenario(
        [plain(0, 13), plain(1, 15), plain(2, 15)],
        dice_rolls=[1],
        board=twisty("Pinata"),
    )

    game.run_turns(3)

    assert game.get_racer(1).victory_points == 1
    assert game.get_racer(2).victory_points == 0
    assert 16 not in chip_tiles(game)


def test_pinata_chips_are_not_taken_by_passing(scenario: type[GameScenario]):
    """Only stopping on a chip counts; moving over it leaves it on the board."""
    game = scenario(
        [plain(0, 13), plain(1, 12)],
        dice_rolls=[1, 2],
        board=twisty("Pinata"),
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 14
    assert game.get_racer(1).victory_points == 0
    assert 13 in chip_tiles(game)


def test_bonkbug_sends_racers_stopping_on_the_last_two_spaces_back_five(
    scenario: type[GameScenario],
):
    """Core rule, checked on both of the last two spaces."""
    game = scenario(
        [plain(0, 13), plain(1, 27), plain(2, 27)],
        dice_rolls=[1, 1, 2],
        board=twisty("Bonkbug"),
    )

    game.run_turns(3)

    assert game.get_racer(1).position == 23
    assert game.get_racer(2).position == 24


def test_bonkbug_leaves_the_third_to_last_space_alone(scenario: type[GameScenario]):
    """Boundary: the effect covers exactly two spaces, not three."""
    game = scenario(
        [plain(0, 13), plain(1, 26)],
        dice_rolls=[1],
        board=twisty("Bonkbug"),
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 27


def test_bonkbug_does_not_stop_a_racer_from_finishing(scenario: type[GameScenario]):
    """Crossing the finish line is not stopping on a space, so it is not penalised."""
    game = scenario(
        [plain(0, 13), plain(1, 27), plain(2, 0)],
        dice_rolls=[1, 6],
        board=twisty("Bonkbug"),
    )

    game.run_turns(2)

    assert game.get_racer(1).finish_position == 1


def test_bonkbug_applies_to_warps_onto_the_last_spaces(scenario: type[GameScenario]):
    """Landing by warp counts as stopping there, so the tile fires for warps too."""
    board = twisty("Bonkbug")
    board.static_features[5] = [WarpTile(None, target=29)]
    game = scenario([plain(0, 13), plain(1, 4)], dice_rolls=[1], board=board)

    game.run_turns(2)

    assert game.get_racer(1).position == 24


def test_conveyor_belt_warps_every_racer_to_the_space_after_start(
    scenario: type[GameScenario],
):
    """Core rule: all racers, including the one that drew the card, go to tile 1."""
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1],
        board=twisty("Conveyor Belt"),
    )

    game.run_turns(1)

    assert [game.get_racer(i).position for i in range(3)] == [1, 1, 1]


def test_conveyor_belt_adds_three_to_later_main_moves(scenario: type[GameScenario]):
    """The +3 is global, so every racer that rolls after the draw gets it."""
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1, 2, 1],
        board=twisty("Conveyor Belt"),
    )

    game.run_turns(3)

    assert game.get_racer(1).position == 6
    assert game.get_racer(2).position == 5


def test_conveyor_belt_does_not_add_to_the_drawing_move(scenario: type[GameScenario]):
    """The drawing move is already resolved; the bonus only applies to later rolls."""
    game = scenario(
        [plain(0, 13), plain(1, 5)],
        dice_rolls=[1, 2],
        board=twisty("Conveyor Belt"),
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 1


def test_scrying_pool_eliminates_a_racer_moving_six(scenario: type[GameScenario]):
    """Core rule: a main move of 6 eliminates instead of moving, and play continues."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1, 6, 4],
        board=twisty("Scrying Pool"),
    )

    game.run_turns(3)

    assert game.get_racer(1).eliminated
    assert game.get_racer(2).position == 4


def test_scrying_pool_spares_a_racer_moving_five(scenario: type[GameScenario]):
    """Boundary: 5 is below the limit and moves normally."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1, 5, 4],
        board=twisty("Scrying Pool"),
    )

    game.run_turns(3)

    assert not game.get_racer(1).eliminated
    assert game.get_racer(1).position == 5


def test_scrying_pool_counts_the_distance_after_modifiers(
    scenario: type[GameScenario],
):
    """A roll of 3 plus the Conveyor Belt's +3 is a 6-space move and is eliminated."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1, 3, 1],
        board=twisty(),
    )
    for r in game.state.racers:
        add_racer_modifier(game.engine, r.idx, ConveyorBeltBonus(owner_idx=None))
        add_racer_modifier(game.engine, r.idx, ScryingPoolRule(owner_idx=None))

    game.run_turns(3)

    assert game.get_racer(1).eliminated
    assert game.get_racer(2).position == 4


def test_randomness_ceased_fixes_every_later_roll_to_the_drawn_value(
    scenario: type[GameScenario],
):
    """Core rule: each racer rolls once at the draw and then rolls that value forever."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1, 2, 3, 4],
        board=twisty("Randomness Ceased"),
    )

    game.run_turns(6)

    assert game.get_racer(0).position == 14 + 2
    assert game.get_racer(1).position == 3 * 2
    assert game.get_racer(2).position == 4 * 2


def test_randomness_ceased_stunner_still_forces_a_one(scenario: type[GameScenario]):
    """Twists are track powers, so Stunner's aura wins over the stored value."""
    game = scenario(
        [plain(0), RacerConfig(1, "Stunner")],
        dice_rolls=[3],
    )
    add_racer_modifier(game.engine, 0, FixedDie(owner_idx=None, value=4))

    game.run_turns(1)

    assert game.get_racer(0).position == 1


def test_randomness_ceased_stored_value_is_final_for_party_pooper(
    scenario: type[GameScenario],
):
    """A stored 6 is not rerolled, so Party Pooper neither loops nor moves."""
    game = scenario(
        [RacerConfig(0, "PartyPooper"), plain(1)],
        dice_rolls=[2],
    )
    add_racer_modifier(game.engine, 1, FixedDie(owner_idx=None, value=6))

    game.run_turns(2)

    assert game.get_racer(0).position == 2
    assert game.get_racer(1).position == 6


def test_curse_wands_skip_as_many_seats_as_rolled(scenario: type[GameScenario]):
    """Core rule: after a turn the racer rolls and the turn order jumps that many seats."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2), plain(3)],
        dice_rolls=[1, 1, 2, 1],
        board=twisty("Curse Wands"),
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 0
    assert game.get_racer(2).position == 2
    assert game.state.current_racer_idx == 0


def test_curse_wands_count_eliminated_seats(scenario: type[GameScenario]):
    """Eliminated racers still occupy a seat when counting, so a skip of 2 lands on seat 3."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2), plain(3)],
        dice_rolls=[1, 2],
        board=twisty("Curse Wands"),
    )
    game.get_racer(1).eliminate()

    game.run_turns(1)

    assert game.state.current_racer_idx == 3


def test_curse_wands_landing_on_an_inactive_seat_moves_on(
    scenario: type[GameScenario],
):
    """Open question pinned: a skip ending on an eliminated seat goes to the next active one."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2), plain(3)],
        dice_rolls=[1, 4],
        board=twisty("Curse Wands"),
    )
    game.get_racer(1).eliminate()

    game.run_turns(1)

    assert game.state.current_racer_idx == 2


def test_curse_wands_still_roll_when_a_turn_override_applies(
    scenario: type[GameScenario],
):
    """Open question pinned: the override picks the next racer, but the skip die is still rolled."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2), plain(3)],
        dice_rolls=[1, 1],
        board=twisty("Curse Wands"),
    )
    game.engine.run_turn()
    game.state.next_turn_override = 3

    game.engine.advance_turn()

    assert game.state.current_racer_idx == 3
    assert game.mock_rng is not None
    assert game.mock_rng.randint.call_count == 2


def piece_of(game: GameScenario) -> WeremouthPiece:
    return next(
        m
        for r in game.state.racers
        for m in r.modifiers
        if isinstance(m, WeremouthPiece)
    )


def test_alchemy_lab_piece_eliminates_racers_it_passes(scenario: type[GameScenario]):
    """Core rule: the piece rolls after the turn and eliminates racers strictly between old and new position."""
    game = scenario(
        [plain(0, 13), plain(1, 3), plain(2)],
        dice_rolls=[1, 4],
        board=twisty("Alchemy Lab"),
    )

    game.run_turns(1)

    assert piece_of(game).position == 4
    assert game.get_racer(1).eliminated
    assert not game.get_racer(2).eliminated


def test_alchemy_lab_piece_spares_the_racer_it_lands_on(scenario: type[GameScenario]):
    """Open question pinned: only passed racers die, so landing on one or standing on the Start is safe."""
    game = scenario(
        [plain(0, 13), plain(1, 4), plain(2)],
        dice_rolls=[1, 4],
        board=twisty("Alchemy Lab"),
    )

    game.run_turns(1)

    assert not game.get_racer(1).eliminated
    assert not game.get_racer(2).eliminated


def test_alchemy_lab_piece_rolls_after_every_turn(scenario: type[GameScenario]):
    """The piece keeps its position between turns and rolls again after each one."""
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1, 2, 3, 4],
        board=twisty("Alchemy Lab"),
    )

    game.run_turns(2)

    assert piece_of(game).position == 6


def test_alchemy_lab_piece_stops_rolling_past_the_finish(
    scenario: type[GameScenario],
):
    """Past the board length the piece is done and no longer rolls."""
    game = scenario([plain(0), plain(1)], dice_rolls=[1])
    add_racer_modifier(game.engine, 0, WeremouthPiece(owner_idx=None, position=30))

    game.run_turns(1)

    assert game.mock_rng is not None
    assert game.mock_rng.randint.call_count == 1


def test_alchemy_lab_bite_mark_warps_to_start_and_adds_no_piece(
    scenario: type[GameScenario],
):
    """Bite Mark racing as W.E.R.E.M.O.U.T.H. goes back to the Start and gets the extra move instead of a piece."""
    game = scenario(
        [plain(0, 13), RacerConfig(1, "BiteMark", start_pos=8)],
        dice_rolls=[1, 3],
        board=twisty("Alchemy Lab"),
    )
    game.engine.grant_ability(1, WeremouthRampage())

    game.run_turns(1)

    assert game.get_racer(1).position == 3
    assert not any(
        isinstance(m, WeremouthPiece) for r in game.state.racers for m in r.modifiers
    )


def test_alchemy_lab_bite_mark_extra_move_eliminates_passed_racers(
    scenario: type[GameScenario],
):
    """The extra move is a normal move, so Bite Mark's passing elimination applies."""
    game = scenario(
        [
            plain(0, 13),
            RacerConfig(1, "BiteMark", start_pos=8),
            plain(2, 2),
        ],
        dice_rolls=[1, 4],
        board=twisty("Alchemy Lab"),
    )
    game.engine.grant_ability(1, WeremouthRampage())

    game.run_turns(1)

    assert game.get_racer(2).eliminated
