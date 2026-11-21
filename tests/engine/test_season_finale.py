from magsim.core.events import RaceEndedEvent
from magsim.engine.board import BOARD_DEFINITIONS, Board, MoveDeltaTile
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.engine.twist import TWIST_DECK

FIRST_CORNER = 12
SECOND_TURN = 15


def twisty(*forced: str) -> Board:
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = list(forced)  # type: ignore[assignment]
    return board


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def finale_game(
    scenario: type[GameScenario],
    configs: list[RacerConfig],
) -> GameScenario:
    game = scenario(configs, dice_rolls=[6])
    game.state.finale_pending = True
    return game


def test_season_finale_is_in_the_deck():
    assert "Season Finale" in TWIST_DECK


def test_drawing_the_card_marks_the_finale_as_pending(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty("Season Finale"),
    )

    game.run_turns(1)

    assert game.state.finale_pending
    assert game.state.board.twists == ["Season Finale"]


def test_top_two_restart_at_the_second_turn_and_the_rest_are_sidelined(
    scenario: type[GameScenario],
):
    game = finale_game(scenario, [plain(0, 29), plain(1, 28), plain(2), plain(3)])
    game.get_racer(2).victory_points = 5

    game.run_turn()
    assert game.state.race_number == 1
    game.run_turn()

    state = game.state
    assert state.race_number == 2
    assert state.race_active
    assert not state.finale_pending
    assert state.current_racer_idx == 0
    for idx in (0, 1):
        racer = game.get_racer(idx)
        assert racer.position == SECOND_TURN
        assert racer.finish_position is None
        assert racer.victory_points == 0
        assert racer.active
    for idx in (2, 3):
        assert game.get_racer(idx).sidelined
        assert not game.get_racer(idx).active
    assert game.get_racer(2).victory_points == 5


def test_second_race_pays_the_whole_winner_pool_to_the_winner(
    scenario: type[GameScenario],
):
    game = finale_game(scenario, [plain(0, 29), plain(1, 28), plain(2)])
    game.run_turn()
    game.run_turn()

    while game.state.race_active:
        game.run_turn()

    assert game.get_racer(0).victory_points == 6
    assert game.get_racer(1).victory_points == 0
    assert game.get_racer(2).victory_points == 0
    assert game.state.race_number == 2


def test_race_end_fires_once_per_race(scenario: type[GameScenario]):
    game = finale_game(scenario, [plain(0, 29), plain(1, 28), plain(2)])
    ends: list[int] = []

    def record(engine, event):
        if isinstance(event, RaceEndedEvent):
            ends.append(engine.state.race_number)

    game.engine.on_event_processed = record
    game.run_turn()
    game.run_turn()
    while game.state.race_active:
        game.run_turn()

    assert ends == [1, 2]


def test_no_second_race_with_a_single_finisher(scenario: type[GameScenario]):
    game = finale_game(scenario, [plain(0, 29), plain(1), plain(2)])
    game.state.racers[1].eliminated = True
    game.state.racers[2].eliminated = True

    game.run_turn()

    assert game.state.race_number == 1
    assert not game.state.race_active
    assert not game.state.finale_pending


def test_finalists_get_their_start_of_race_setup_again(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "NepoBaby"),
            plain(1, 29),
            plain(2),
        ],
        dice_rolls=[6],
    )
    game.state.finale_pending = True

    while game.state.race_number == 1:
        game.run_turn()

    assert game.state.race_active
    assert game.get_racer(0).position == FIRST_CORNER
    assert game.get_racer(1).position == SECOND_TURN


def test_mirror_world_keeps_the_flipped_second_turn_for_the_restart(
    scenario: type[GameScenario],
):
    board = Board(length=30, static_features={}, second_turn=8)
    board.mirror()
    game = scenario(
        [plain(0, 29), plain(1, 28), plain(2)],
        dice_rolls=[6],
        board=board,
    )
    game.state.finale_pending = True

    game.run_turn()
    game.run_turn()

    assert board.second_turn == 22
    assert game.state.race_number == 2
    assert game.get_racer(0).position == 22


def test_open_question_board_modifiers_persist_into_race_two(
    scenario: type[GameScenario],
):
    """Pinned, to confirm with the designers: the board survives the finale, racer modifiers do not."""
    game = finale_game(scenario, [plain(0, 29), plain(1, 28), plain(2)])
    board = game.state.board
    board.mirror()
    board.register_modifier(5, MoveDeltaTile(None, delta=-5), game.engine)
    second_turn = board.second_turn

    game.run_turn()
    game.run_turn()

    assert game.state.race_number == 2
    assert any(isinstance(m, MoveDeltaTile) for m in board.dynamic_modifiers[5])
    assert board.second_turn == second_turn
