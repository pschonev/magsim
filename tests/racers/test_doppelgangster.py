from magsim.core.events import GameEvent, Phase, RacerFinishedEvent, WarpCmdEvent
from magsim.engine.scenario import GameScenario, RacerConfig


def cfg(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


def ability_names(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def warp(game: GameScenario, idx: int, tile: int) -> None:
    game.engine.push_event(
        WarpCmdEvent(
            target_racer_idx=idx,
            target_tile=tile,
            source="System",
            phase=Phase.PRE_MAIN,
            responsible_racer_idx=None,
        ),
    )


def base(*extra: RacerConfig, doppel_pos: int = 0) -> list[RacerConfig]:
    return [cfg(0, "Doppelgangster", doppel_pos), *extra]


def test_first_finisher_is_eliminated_instead_of_finishing(
    scenario: type[GameScenario],
):
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    racer = game.get_racer(1)
    assert racer.eliminated
    assert racer.finish_position is None
    assert racer.position is None


def test_eliminated_finisher_gets_no_victory_points(scenario: type[GameScenario]):
    """An eliminated racer does not finish, so it must not collect the 1st place VP."""
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.get_racer(1).victory_points == 0
    assert game.get_racer(0).victory_points == 0


def test_no_finish_event_is_emitted_for_the_eliminated_racer(
    scenario: type[GameScenario],
):
    """Finish powers (e.g. Mastermind, Gloth) react to RacerFinishedEvent, so none may
    be emitted for the dive.
    """
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )
    seen: list[GameEvent] = []
    game.engine.on_event_processed = lambda _engine, evt: seen.append(evt)

    game.run_turns(2)

    assert not any(isinstance(e, RacerFinishedEvent) for e in seen)


def test_doppelgangster_gains_the_eliminated_racers_power(
    scenario: type[GameScenario],
):
    game = scenario(
        base(cfg(1, "Banana", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert ability_names(game, 0) == {"DoppelgangsterTakeADive", "BananaTrip"}


def test_race_continues_after_the_dive(scenario: type[GameScenario]):
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.engine.state.race_active


def test_dive_triggers_when_the_finish_is_reached_by_a_warp(
    scenario: type[GameScenario],
):
    """The finish check also runs after warps, so a racer warped onto the finish line
    first dives as well.
    """
    game = scenario(
        base(cfg(1, "Centaur", 20), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1],
    )
    warp(game, 1, 30)

    game.run_turn()

    assert game.get_racer(1).eliminated
    assert game.get_racer(1).finish_position is None


def test_doppelgangster_finishing_first_is_eliminated_itself(
    scenario: type[GameScenario],
):
    """The rules state that if Doppelgangster finishes first it is eliminated too, so
    it gets no victory points and no finish position.
    """
    game = scenario(
        base(cfg(1, "Centaur"), cfg(2, "Scoocher"), cfg(3, "Hare"), doppel_pos=28),
        dice_rolls=[3],
    )

    game.run_turn()

    doppel = game.get_racer(0)
    assert doppel.eliminated
    assert doppel.finish_position is None
    assert doppel.victory_points == 0
    assert ability_names(game, 0) == set()


def test_dive_only_happens_once_per_race(scenario: type[GameScenario]):
    """After the first crosser dove, nobody has finished yet, but the power is spent:
    the next racer to cross takes 1st place.
    """
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher", 28), cfg(3, "Hare")),
        dice_rolls=[1, 3, 3],
    )

    game.run_turns(3)

    assert game.get_racer(1).eliminated
    assert game.get_racer(2).finish_position == 1
    assert game.get_racer(2).victory_points == 4


def test_next_crosser_wins_after_doppelgangster_dove_on_its_own_finish(
    scenario: type[GameScenario],
):
    """After Doppelgangster eliminates itself its power is gone, so the next racer to
    cross is a normal 1st finisher and is not eliminated.
    """
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare"), doppel_pos=28),
        dice_rolls=[3, 3],
    )

    game.run_turns(2)

    assert game.get_racer(0).eliminated
    assert game.get_racer(1).finish_position == 1
    assert not game.get_racer(1).eliminated


def test_dive_is_not_used_when_a_racer_already_finished(
    scenario: type[GameScenario],
):
    """Mastermind can finish early by prediction; with a finished racer present the
    finish is no longer a 'first' finish.
    """
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )
    game.get_racer(2).finish_position = 1

    game.run_turns(2)

    assert game.get_racer(1).finish_position == 2
    assert not game.get_racer(1).eliminated


def test_eliminated_doppelgangster_does_not_intercept(scenario: type[GameScenario]):
    """An eliminated racer has no abilities, so its power must not fire any more."""
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )
    game.engine.clear_all_abilities(0)
    game.get_racer(0).eliminate()

    game.run_turns(2)

    assert game.get_racer(1).finish_position == 1


def test_dive_leaves_only_doppelgangster_so_it_wins_as_sole_survivor(
    scenario: type[GameScenario],
):
    """With only one other racer left, the elimination leaves a sole survivor who
    auto-finishes 1st and earns the winner VP.
    """
    game = scenario(
        [cfg(0, "Doppelgangster"), cfg(1, "Centaur", 28)],
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.get_racer(0).finish_position == 1
    assert game.get_racer(0).victory_points == 4
    assert not game.engine.state.race_active


def test_gained_power_is_usable_immediately(scenario: type[GameScenario]):
    """Gained Legs lets Doppelgangster skip its roll and move 5 on its next turn."""
    game = scenario(
        base(cfg(1, "Legs", 25), cfg(2, "Centaur"), cfg(3, "Hare")),
        dice_rolls=[1, 1, 1, 1, 1],
    )

    game.run_turns(5)

    assert game.get_racer(0).position == 6


def test_gained_power_survives_core_ability_replacement(
    scenario: type[GameScenario],
):
    """The copied power is granted persistently, so identity swaps (Copy Cat style
    core replacement) must not drop it.
    """
    game = scenario(
        base(cfg(1, "Banana", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )
    game.run_turns(2)

    game.engine.replace_core_abilities(
        0, game.engine.instantiate_racer_abilities("Centaur")
    )

    assert "BananaTrip" in ability_names(game, 0)


def test_eliminated_racer_stops_its_own_turn(scenario: type[GameScenario]):
    """After diving in the middle of its own main move, the racer must not trigger
    landing effects or move again.
    """
    game = scenario(
        base(cfg(1, "Centaur", 28), cfg(2, "Scoocher"), cfg(3, "Hare")),
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.get_racer(1).position is None
    assert game.get_racer(1).main_move_consumed


def test_dive_copies_nothing_from_a_racer_without_abilities(
    scenario: type[GameScenario],
):
    """A finisher whose abilities were stripped (scenario override) still dives, and
    Doppelgangster just keeps its own power.
    """
    game = scenario(
        [
            cfg(0, "Doppelgangster"),
            RacerConfig(1, "Centaur", abilities=set(), start_pos=28),
            cfg(2, "Scoocher"),
            cfg(3, "Hare"),
        ],
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.get_racer(1).eliminated
    assert ability_names(game, 0) >= {"DoppelgangsterTakeADive"}
