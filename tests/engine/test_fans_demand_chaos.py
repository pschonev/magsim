from magsim.core.types import TwistName
from magsim.engine.board import BOARD_DEFINITIONS, Board, MoveDeltaTile
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.engine.twist import FANS_CARD, TWIST_DECK, WeremouthPiece
from magsim.simulation.config import GameConfig

BANNED_SAMPLE = 200


def twisty(*forced: TwistName) -> Board:
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = list(forced)
    return board


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "ReRunner", start_pos=start_pos)


def positions(game: GameScenario) -> list[int | None]:
    return [r.position for r in game.state.racers]


def test_fans_is_in_the_deck():
    assert FANS_CARD in TWIST_DECK


def test_fans_draws_two_distinct_cards_after_itself_in_order(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Scrying Pool", "Pinata"),
    )

    game.run_turns(1)

    assert game.state.board.twists == [FANS_CARD, "Scrying Pool", "Pinata"]


def test_sub_cards_are_never_fans_never_equal_and_never_banned(
    scenario: type[GameScenario],
):
    banned: frozenset[TwistName] = frozenset({"Time Imp", "Season Finale"})
    game = scenario([plain(0), plain(1)], dice_rolls=[1], board=twisty())
    board = game.state.board
    board.banned_twists = banned

    for _ in range(BANNED_SAMPLE):
        board.twists.clear()
        first = board.draw_twist(game.engine, exclude=(FANS_CARD,))
        second = board.draw_twist(game.engine, exclude=(FANS_CARD, first))  # type: ignore[arg-type]
        assert first not in {FANS_CARD, *banned}
        assert second not in {FANS_CARD, first, *banned}


def test_a_banned_card_is_never_drawn_at_all(scenario: type[GameScenario]):
    game = scenario([plain(0), plain(1)], dice_rolls=[1], board=twisty())
    board = game.state.board
    board.banned_twists = frozenset(TWIST_DECK) - {"Pinata"}

    assert board.draw_twist(game.engine) == "Pinata"
    assert board.draw_twist(game.engine, exclude=("Pinata",)) is None


def test_roast_chicken_then_conveyor_belt_leaves_everyone_on_tile_one(
    scenario: type[GameScenario],
):
    """The chicken move resolves first, then the belt warps everybody."""
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Roast Chicken", "Conveyor Belt"),
    )

    game.run_turns(1)

    assert positions(game) == [1, 1, 1]


def test_conveyor_belt_then_roast_chicken_moves_the_tied_pack_seven(
    scenario: type[GameScenario],
):
    """Everyone is tied for last on tile 1, so everyone moves 7."""
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Conveyor Belt", "Roast Chicken"),
    )

    game.run_turns(1)

    assert positions(game) == [8, 8, 8]


def test_mirror_then_alchemy_puts_the_piece_on_the_mirrored_board(
    scenario: type[GameScenario],
):
    """Cards after Mirror World take effect after the flip, so the piece is a normal piece at the Start."""
    game = scenario(
        [plain(0, 13), plain(1, 3)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Mirror World", "Alchemy Lab"),
    )

    game.run_turns(1)

    piece = next(
        m
        for r in game.state.racers
        for m in r.modifiers
        if isinstance(m, WeremouthPiece)
    )
    assert piece.position == 0
    assert positions(game) == [16, 27]


def test_alchemy_then_mirror_flips_the_piece_after_it_has_rolled(
    scenario: type[GameScenario],
):
    """Pinned: the piece rolls at the turn end before the flip (hook order), so 1 becomes 29."""
    game = scenario(
        [plain(0, 13), plain(1, 3)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Alchemy Lab", "Mirror World"),
    )

    game.run_turns(1)

    piece = next(
        m
        for r in game.state.racers
        for m in r.modifiers
        if isinstance(m, WeremouthPiece)
    )
    assert piece.position == 29


def test_bonkbug_then_mirror_moves_the_chips_to_tiles_one_and_two(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Bonkbug", "Mirror World"),
    )

    game.run_turns(1)

    chips = {
        tile
        for tile, mods in game.state.board.dynamic_modifiers.items()
        if any(isinstance(m, MoveDeltaTile) for m in mods)
    }
    assert chips == {1, 2}


def test_mirror_then_bonkbug_puts_the_chips_on_the_original_end(
    scenario: type[GameScenario],
):
    """Bonkbug resolves after the flip, so its last-two-spaces rule uses the mirrored board."""
    game = scenario(
        [plain(0, 13), plain(1, 3)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Mirror World", "Bonkbug"),
    )

    game.run_turns(1)

    chips = {
        tile
        for tile, mods in game.state.board.dynamic_modifiers.items()
        if any(isinstance(m, MoveDeltaTile) for m in mods)
    }
    assert chips == {28, 29}


def test_second_card_still_plays_after_time_imp_eliminates_the_mover(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1), plain(2)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Time Imp", "Pinata"),
    )

    game.run_turns(1)

    assert game.get_racer(0).eliminated
    assert any(
        mods for tile, mods in game.state.board.dynamic_modifiers.items() if tile > 12
    )


def test_second_card_is_skipped_once_the_race_is_over(scenario: type[GameScenario]):
    """Time Imp leaves one racer, who auto-finishes; nothing more is played."""
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty(FANS_CARD, "Time Imp", "Pinata"),
    )

    game.run_turns(1)

    assert not game.state.race_active
    assert not game.state.board.dynamic_modifiers


def test_game_config_hash_and_encoding_include_banned_twists():
    base = GameConfig(racers=("ReRunner", "Centaur"), board="TwistyTwirl", seed=1)
    banned = GameConfig(
        racers=base.racers,
        board=base.board,
        seed=1,
        exclude_twists=("Time Imp",),
    )

    assert base.compute_hash() != banned.compute_hash()
    assert GameConfig.from_encoded(banned.encoded) == banned
    assert GameConfig.from_encoded(base.encoded) == base
