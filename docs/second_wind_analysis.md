# Second Wind Expansion: Required Changes

Source: `docs/Magical_Athlete_Second_Wind_Rules.pdf`. Target: `src/magsim`.

Status: runner table done. Other sections are placeholders. Racer card text: [racers.md](racers.md).

## Legend

| Emoji | Meaning |
| --- | --- |
| 🟢 | Easy. Existing hooks and analogue racers cover it. |
| 🟡 | Minor adjustment. Small, local engine change or new event field. |
| 🔴 | Big engine change. New engine-wide concept required. |
| ⚪ | Not simulated. Power has no effect on a single race (simulated as a racer without powers, or excluded). |

Gap IDs (`E1`...) refer to [Cross-cutting engine gaps](#cross-cutting-engine-gaps).

Every new racer also needs: module in `src/magsim/racers/`, entries in `core/types.py` (`RacerName`, `AbilityName`), `core/registry.py` (`RACER_ABILITIES`), and `data/racer_stats.json`.

## 1. Runners

Ability text, clarifications and flavor: [racers.md](racers.md). Per-racer code hooks: [Racer notes by milestone](#racer-notes-by-milestone).

| # | Runner | Trigger | Difficulty | Gaps |
| --- | --- | --- | --- | --- |
| 1 | Bite Mark (HUUAARRGGHHH!!!!) | On own main roll result | 🟢 | E13 |
| 2 | Critic (BON MOTS) | Other racer's roll window | 🟢 |  |
| 3 | Gloth (GLORPOR) | Passive roll modifier; race end | 🟡 | E5, E9 |
| 4 | Blunderdog (BLUNDERTRAIL) | Passive roll modifier (self) | 🟡 | E1 |
| 5 | Diva (QUELLE DRAMATIQUE!) | Start of own turn | 🟢 |  |
| 6 | Hog Knight (PIGGYBACK) | Setup; landing; passive roll modifier | 🟡 | E11 |
| 7 | Cheatah (SLEIGHT OF PAW) | Replaces own main roll | 🟡 | E7 |
| 8 | Doppelgängster (TAKE A DIVE) | On first finish | ✅ | E6, E13, E14 |
| 9 | Hopfrog (BOIOIOING) | End of own turn | 🟢 |  |
| 10 | Hotel (MONOPOLIZE) | When another racer stops on my space | 🟢 | E7 |
| 11 | Kraken (GET OVER HERE) | Start of own turn, once per race | 🟢 |  |
| 12 | Mole (TUNNELIN') | Start of own turn | 🟢 |  |
| 13 | Icarus (FLIGHT RISK) | Passive roll modifier; own roll result | 🟢 | E13 |
| 14 | Le Saboteur (TROIS REVOIR) | Other racers' main roll | 🟡 | E1, E2 |
| 15 | Mr. Dice Guy (YES! MORE!) | Replaces own main roll | 🟡 | E2 |
| 16 | Kingtripper (REGISLIDE) | Start of own turn | 🟢 |  |
| 17 | Magical Athlete (FLEXOMANCY) | Own main roll result (per die value) | 🟡 | E12 |
| 18 | Mush (GLOBSTER MASH) | Own main roll result | 🟡 | E14 |
| 19 | Nemesis (GRUDGE MATCH) | Other racers' roll result | 🟢 | E2 |
| 20 | Overtaker (SKULLDIGGERY) | Passive roll modifier | 🟢 |  |
| 21 | Re-Runner (RUN IT BACK) | Between races | ✅ |  |
| 22 | Nepo Baby (HUGELY RICH) | Setup | 🟡 | E9 |
| 23 | Party Pooper (NOISE COMPLAINT) | Any racer's roll (all rolls, not just main) | ✅ | E2 |
| 24 | Show-Off (GUYS, WATCH!) | Own main roll | 🟡 | E2 |
| 25 | <NULL> ([VOID]) | Passive aura (position dependent) | 🟡 | E4 |
| 26 | Penguin (TUMMY TIME) | Another racer passes; own turn while tripped | 🟡 | E1, E10 |
| 27 | Soulmate (TWIN FLAME) | Setup; start of own turn | 🟢 |  |
| 28 | Speed Demon (TERMINAL VELOCITY) | Passive roll modifier; start of own turn | 🟢 | E7, E13 |
| 29 | Streaker (EXHIBIT B) | Own main move passes | 🟡 | E12 |
| 30 | Tail (REAR END) | Start of own turn | 🟢 |  |
| 31 | Spoilsport (CRY FOUL) | Start of own turn | 🟡 | E5 |
| 32 | Stunner (STOP TRAFFIC) | Other racers' rolls | ✅ | E2, E3 |
| 33 | The Hose (POWER WASH) | End of own turn | 🟢 | E2 |
| 34 | Stepdad (STEP UP) | Passive aura; other racer's finish | 🟡 | E7 |
| 35 | Switcharoo (MARSWAPIAL) | End of own turn | 🟡 | E7 |
| 36 | Understudy (THE METHOD) | Setup | 🟢 | E11 |

### Summary

| Difficulty | Count | Runners |
| --- | --- | --- |
| 🟢 | 16 | Bite Mark, Critic, Diva, Hopfrog, Hotel, Kraken, Mole, Icarus, Kingtripper, Nemesis, Overtaker, Soulmate, Speed Demon, Tail, The Hose, Understudy |
| 🟡 | 19 | Gloth, Blunderdog, Hog Knight, Cheatah, Doppelgängster, Le Saboteur, Mr. Dice Guy, Magical Athlete, Mush, Nepo Baby, Party Pooper, Show-Off, <NULL>, Penguin, Streaker, Spoilsport, Stunner, Stepdad, Switcharoo |
| 🔴 | 0 | |
| ⚪ | 1 | Re-Runner (generic racer, no powers) |

## Cross-cutting engine gaps

| ID | Gap | Current state | Needed by |
| --- | --- | --- | --- |
| E1 | Backward main move and non-additive roll modifiers | `MoveDistanceQuery.final_value = max(0, base + sum(modifiers))`; modifiers are additive only; `handle_execute_main_move` skips `dist <= 0`. | Blunderdog, Le Saboteur, Penguin |
| E2 | Central die roll and multi-dice state | `engine.rng.randint` called directly (`roll.py`, `duelist.py`); `RollState` has single `dice_value`. | Mr. Dice Guy, Show-Off, Le Saboteur, Party Pooper, Stunner, Nemesis, The Hose |
| E3 | Base-die override by aura | `racer.roll_override` is set by the roller itself only. | Stunner |
| E4 | Post-position-change hook before subscribers | Abilities can be stripped/restored via `clear_all_abilities`/`_update_abilities`, but nothing runs between a position change and `publish_to_subscribers`. | <NULL> |
| E5 | Race-end event and race cancel | `check_race_over_condition` sets `race_active = False`, emits nothing. | Gloth, Spoilsport |
| E6 | Pre-finish interception | `check_finish` -> `mark_finished` is unconditional. | Doppelgängster |
| E7 | Seat order (`turn_order`) and player-bound points/agent | Turn order and subscriber order are derived from racer idx; points on racer (`victory_points`); one agent per racer idx; no "left"/"right". Minimal fix: a seat list; Switcharoo exchanges two entries and swaps `victory_points` and agents. | Switcharoo (swap), Cheatah, Stepdad (neighbours), Hotel, Speed Demon ("player points" = racer points until a swap happens) |
| E8 | Multi-race game state | Single race per `GameEngine`. Out of scope. | none (Re-Runner simulated as generic racer) |
| E9 | Board corners and tracks | `Board(length=30)`; `BoardName` has only `Standard`, `WildWilds`. | Gloth, Nepo Baby |
| E10 | Roll while tripped | Tripped racers skip the roll in `run_turn` and `handle_perform_main_roll`. | Penguin |
| E11 | Pieces (hogs) | Only racers and `SpaceModifier`s exist. | Hog Knight, Understudy |
| E12 | `is_main` on `PassingEvent` | Only `MoveCmdEvent.is_main` exists; `PassingEvent.source` is `"System"` for any system move. | Streaker, Magical Athlete |
| E13 | Shared elimination helper | Elimination + sole-survivor check inlined in `racers/mouth.py`. | Bite Mark, Doppelgängster, Icarus, Speed Demon |
| E14 | Runtime ability grant from copies/draws | `replace_core_abilities` keeps only `ExternalAbilityMixin` abilities. | Mush, Doppelgängster |
| E15 | Twist card dispatch | `TWIST_DECK = ("Blank",)`; `Board.twist` holds one name; no per-card handler, no "racer that triggered" passed on, no way to keep two cards active. | All twist cards |
| E16 | Global per-race rules in roll/move code | Main-move distance only sees per-racer modifiers; `handle_execute_main_move` has no veto. | Conveyor Belt, Scrying Pool |
| E17 | Consumable space chips | `VictoryPointTile` stays on the board after landing. | Piñata |
| E18 | Fixed die values | `roll_die` asks hooks to force or reject; no per-racer stored value, and a fixed value that gets rejected would loop forever. | Randomness has Randomly Ceased |
| E19 | Turn skipping by count | `advance_turn` handles `next_turn_override` (one racer) or the next active racer; no skip-N over all seats, finished and eliminated included. | Curse Wands |
| E20 | Persistent turn-end piece | No per-race state for a piece that is not a racer. Needs one integer position on engine state (not in the racer list) and a `TurnEndEvent` handler. | Alchemy Lab Containment Breach |
| E21 | In-place racer replacement | Not needed: Swap Meet is not simulated (M26). | none |
| E22 | Direction reversal | Handled by mirroring once, not by changing direction logic. Needs a `Board` mirror (tile keys, corners, tile-internal targets) and a position map for active racers and stored positions, applied after the drawing move completes. | Mirror World Theory Confirmed |
| E23 | Second race inside one game | Single race per `GameEngine` (E8); `end_race` is final. Needs a pending-finale flag, a `sidelined` state for the other racers and a re-initialisation of the two finalists. | Season Finale |

## 2. Twist cards

On Twisty Twirl, the first move from space 13 to 14 (not a warp) draws one twist card, once per game. Implemented so far: the draw (`Board.draw_twist_on_crossing`, `TWIST_DECK`) with a single `Blank` card that changes nothing. The real cards below are not implemented yet.

13 cards, rulebook pages 1-2. Flavor text: none for any card.

| # | Card | Ability | Clarifications | Page |
| --- | --- | --- | --- | --- |
| 1 | Alchemy Lab Containment Breach! | Put the W.E.R.E.M.O.U.T.H. on the Start. Roll for its move after every turn. Any racer it passes is eliminated. | If someone is racing as Bite Mark, they still race as the W.E.R.E.M.O.U.T.H., but go back to the Start and will move more often. It can cross the finish line, but doesn't place or get points (unless controlled by a Bite Mark player). | 1 |
| 2 | The Fans Demand Chaos! | Draw 2 twist cards and do both in order. | none | 1 |
| 3 | Bonkbug Infestation at the Finish Line! | When a racer stops on one of the last 2 spaces, they move backwards 5. | none | 1 |
| 4 | Mirror World Theory Confirmed! | Reverse the direction of the race. | If multiple racers are on the Start when this happens, turn order determines the finish order, e.g. the player closest in turn order would win. | 1 |
| 5 | The Conveyor Belt is On! | Warp all racers to one space after Start. Everybody gets +3 to their main move. | none | 1 |
| 6 | No Running by the Scrying Pool! | Any racer that moves 6+ spaces for their main move is eliminated instead. | none | 1 |
| 7 | Curse Wands for Everyone! | After each player’s turn, they roll a die. Skip that many players in turn order. | Players and racers that are finished or eliminated are still included in counting and still roll for skipping. If players have multiple racers, roll for each. | 1 |
| 8 | The Piñata is Leaking! | Put a point chip on every empty space after the first corner. When a racer stops on a space with one, they take it. | none | 1 |
| 9 | Randomness has Randomly Ceased! | All players roll their die: that’s what they roll for anything for the rest of the race. | Twists are technically a track power, so these happen before racer powers. Racers like Stunner would still change these to a 1, for example. | 2 |
| 10 | You Tromped on a Time Imp! | The racer that triggered this is eliminated, but participates in the next race as an extra racer for their player. | If Mush triggered this, they start with all the powers they had when they were eliminated. | 2 |
| 11 | Roast Chicken on the Ground! | Move the last place racer 7. | If multiple racers are in last place, they all get the bonus. They move simultaneously, if it matters. | 2 |
| 12 | Season Finale! | The racers who finish 1st and 2nd race one-on-one to win both trophies. They start on the second corner and 1st place goes first. | This counts as a new race, just quicker, so powers like Nepo Baby still trigger. Any points gotten by other racers that weren't 1st or 2nd chips stay with those racers. | 2 |
| 13 | Swap Meet! | All players draw a new racer and can swap it with their current one. | The decision is simultaneous. If you swap, your new racer starts at the same space as the old racer. Start of race powers do not happen, though end of race powers could. | 2 |

## 3. Boards and tracks

_TODO._ Twisty Twirl (twist), Whirly World (whirls). Track order: Twisty, Whirly, Twisty, Whirly.

## 4. Implementation order

Low-hanging fruit first, then engine changes grouped by gap, from small to large. Rules for every milestone are in [AGENT.md](../AGENT.md).

| Milestone | Racers | Engine work | Notes |
| --- | --- | --- | --- |
| M1 ✅ | Overtaker, Tail, Kingtripper | none | Passive modifier, two start-of-turn decisions. |
| M2 ✅ | Diva, Hopfrog, Mole | none | Swap warp, extra turn, roll override. |
| M3 ✅ | Kraken, Soulmate, Critic | none | Once per race, setup selection, reroll for others. |
| M4 ✅ | Hotel, Nemesis, The Hose | none | Hotel uses racer `victory_points` for now (E7 revisit in M17). Nemesis and The Hose use `engine.rng` directly (E2 revisit in M12/M13). |
| M5 ✅ | Icarus, Bite Mark, Speed Demon | E13 shared elimination helper (extract from `mouth.py`) | Speed Demon uses racer `victory_points` for now. |
| M6 ✅ | Nepo Baby | E9 corner positions on `Board` | Gloth reuses this in M9. |
| M7 ✅ | Streaker, Magical Athlete | E12 `is_main` on `PassingEvent` | Magical Athlete 5 needs a negative non-main `push_move`. |
| M8 ✅ | Blunderdog | E1 backward main move, non-additive modifiers | Reused by Le Saboteur and Penguin. |
| M9 ✅ | Spoilsport, Gloth | E5 race-end event and race cancel | Needs E9 from M6. |
| M10 ✅ | Mush, Understudy | E14 runtime ability grant that survives `replace_core_abilities` | Understudy is easy but fits here. Its Hog Knight copy case waits for M15. |
| M11 ✅ | Doppelgängster | E6 pre-finish interception | Needs E13 and E14. |
| M12 ✅ | Party Pooper, Stunner | E2 central die roll, E3 base-die override by aura | Re-route Nemesis and The Hose through the central roll. |
| M13 ✅ | Mr. Dice Guy, Show-Off | E2 multi-dice roll state | All dice values exposed to triggers. |
| M14 ✅ | Le Saboteur, Penguin | E1 (done), E10 roll while tripped | Le Saboteur needs E1 and E2, Penguin needs E1. |
| M15 ✅ | Hog Knight | E11 pieces (hogs) | Then add the Hog Knight case to Understudy. |
| M16 ✅ | `<NULL>` | E4 resync hook before `publish_to_subscribers` | Strip-and-restore. |
| M17 ✅ | Stepdad, Cheatah | E7 `turn_order` seat list (read-only use) | Switch `advance_turn` and `publish_to_subscribers` to the seat list. |
| M18 | Switcharoo | E7 swap of seats, `victory_points`, agents; per-seat result attribution | Result attribution is in `simulation/`, which AGENT.md forbids. Ask first. Revisit Hotel, Speed Demon. |
| M19 ✅ | Re-Runner | `RACER_ABILITIES` entry only | Generic racer. |
| M20 ✅ | Whirly World board (warp) | New board type, warp tiles | Easy. |
| M21 | Twisty Twirl board (twist) | Twist draw on 13 -> 14, once per game | Draw and `Blank` card are in. The real cards are M22-M30. |
| M22 ✅ | Twist: Roast Chicken on the Ground!, You Tromped on a Time Imp! | E15 card dispatch with the triggering racer, real deck | Immediate effects only, no state kept. `Blank` stays selectable for tests. |
| M23 ✅ | Twist: Bonkbug Infestation at the Finish Line!, The Piñata is Leaking! | E17 consumable chips | Board modifiers placed at draw time. |
| M24 ✅ | Twist: The Conveyor Belt is On!, No Running by the Scrying Pool! | E16 global rules in the main roll/move; E15 keeps several cards active | Persistent rules for the rest of the race. |
| M25 ✅ | Twist: Randomness has Randomly Ceased!, Curse Wands for Everyone! | E18 fixed die values, E19 turn skipping | Both go through `roll_die`. Curse Wands also changes the turn flow. |
| M26 ⚪ | Twist: Swap Meet! | none | Not implemented. The simulation measures racers, not players, so swapping a racer mid-race has no meaningful result. |
| M27 ✅ | Twist: Alchemy Lab Containment Breach! | E20 `TurnEndHookMixin` modifiers | Minor. Not a racer, so counts, rank and finish stay unchanged. Bite Mark case is a warp plus extra moves. |
| M28 | Twist: Mirror World Theory Confirmed! | E22 mirror positions once at the draw | Minor. Race logic stays forward. Apply after the drawing move completes, as a silent renumbering. Racers on the Start finish at once. |
| M29 | Twist: Season Finale! | E23 second race, E5 race-end event | Hard. Same racer states across both races, so `simulation/` should stay unchanged (verify). |
| M30 | Twist: The Fans Demand Chaos! | E15 (two cards at once) | Trivial alone. Last because card combinations need the other cards. |

### Racer notes by milestone

Trigger and code hook per racer (moved from the former runner table). Ability and clarification text: [racers.md](racers.md).

**M1**

- **Overtaker** (Passive roll modifier): `RollModificationMixin`, count active racers with higher position (finished racers are inactive).
- **Tail** (Start of own turn): `TurnStartEvent` + `BooleanDecisionMixin` + `push_warp`. Analogue: `hypnotist.py`, `third_wheel.py`.
- **Kingtripper** (Start of own turn): `TurnStartEvent` + `BooleanDecisionMixin` + `push_trip`. Tie choice via `SelectionDecisionMixin`. Analogue: `baba_yaga.py`, `hypnotist.py`.

**M2**

- **Diva** (Start of own turn): `TurnStartEvent` + `SimultaneousWarpCmdEvent` (`push_simultaneous_warp`). Tie choice via `SelectionDecisionMixin`. Analogue: `flip_flop.py`, `hypnotist.py`.
- **Hopfrog** (End of own turn): `TurnEndEvent` + `state.next_turn_override`. Analogue: `genius.py`, `skipper.py`.
- **Mole** (Start of own turn): `TurnStartEvent` + `racer.roll_override = (source, 6)` (as in `legs.py`). Counts as main move.

**M3**

- **Kraken** (Start of own turn, once per race): `TurnStartEvent` + `BooleanDecisionMixin` + `SimultaneousWarpCmdEvent` + `push_trip`. Analogue: `party_animal.py` (pull).
- **Soulmate** (Setup; start of own turn): `SetupPhaseMixin.on_setup` + `SelectionDecisionMixin` (analogue: `egg.py`, `twin.py`) + `TurnStartEvent` + `push_warp`.
- **Critic** (Other racer's roll window): `RollModificationWindowEvent` (target != owner, target ahead) + `BooleanDecisionMixin` + `trigger_reroll`. Once-per-turn reset on `PreTurnStartEvent`. Analogue: `dicemonger.py` (reroll for someone else).

**M4**

- **Hotel** (When another racer stops on my space): `PostMoveEvent`/`PostWarpEvent` (end tile == owner position) + `racer.victory_points` transfer + `push_trip`. Points live on the racer, so "can't pay" is `victory_points < 1`.
- **Nemesis** (Other racers' roll result): `RollResultEvent` (other racer) + `engine.rng.randint` + `push_move` queued after their move. Analogue: `duelist.py` (extra die).
- **The Hose** (End of own turn): `TurnEndEvent` + `engine.rng` + `push_trip`.

**M5**

- **Icarus** (Passive roll modifier; own roll result): `RollModificationMixin` (+3) + `RollResultEvent` (`dice_value == 6`) + elimination as in `mouth.py`.
- **Bite Mark** (On own main roll result): `RollResultEvent` (MAIN_ACT precedes `ExecuteMainMoveEvent`, so transform happens before the move). Swap abilities via `replace_core_abilities`. New W.E.R.E.M.O.U.T.H. ability on `PassingEvent` (passer == owner), elimination like `racers/mouth.py`.
- **Speed Demon** (Passive roll modifier; start of own turn): `RollModificationMixin` using `victory_points`; `TurnStartEvent` + elimination as in `mouth.py`.

**M6**

- **Nepo Baby** (Setup): `SetupPhaseMixin.on_setup` sets position (cf. `RacerConfig.start_pos`). Needs corner tile index per board.

**M7**

- **Streaker** (Own main move passes): `PassingEvent` (passer == owner). `PassingEvent` has no `is_main` flag (`MoveCmdEvent.is_main` exists), and needs once-per-move dedupe.
- **Magical Athlete** (Own main roll result (per die value)): `RollResultEvent` + `roll_override`/`skip_main_move` + `push_warp`/`push_simultaneous_warp`/`push_trip`/`next_turn_override`. 5 needs non-main negative `push_move` on another racer (movement code handles negative steps; verify clamp and passing). 6 needs `PassingEvent` filter.

**M8**

- **Blunderdog** (Passive roll modifier (self)): `RollModificationMixin`. Tripling needs non-additive modifiers. Backward main move is not possible: `MoveDistanceQuery.final_value = max(0, ...)` and `handle_execute_main_move` only moves if `dist > 0`.

**M9**

- **Spoilsport** (Start of own turn): `TurnStartEvent` + new race-cancel path (no 1st/2nd points unless already finished). Today `race_active` ends only via 2 finishers or sole survivor; result recording assumes finishers.
- **Gloth** (Passive roll modifier; race end): `RacerModifier` + `RollModificationMixin` (analogue: `blimp.py`, `party_animal.py`). Race-end bonus has no hook today (`check_race_over_condition` emits no event). Needs corner positions.

**M10**

- **Mush** (Own main roll result): `RollResultEvent` + `engine.draw_racers` + `grant_ability`. `replace_core_abilities` only preserves `ExternalAbilityMixin` abilities, so granted abilities must be wrapped. Stacks; copies don't inherit added powers.
- **Understudy** (Setup): `SetupPhaseMixin.on_setup` + `engine.instantiate_racer_abilities(name)` (analogue: `copycat.py`, `twin.py`). Setup order matters: other racers' abilities may not be assigned yet, use racer names. Hog Knight copy needs a hog piece.

**M11**

- **Doppelgängster** (On first finish): No pre-finish interception: `check_finish` calls `mark_finished` directly. Needs veto in `check_finish`/`mark_finished`, elimination (no VP, no finish powers), ability copy.

**M12**

- **Party Pooper** (Any racer's roll (all rolls, not just main)): `RollModificationWindowEvent` + `trigger_reroll` for main rolls. "All rolls" needs a central die roll function; dice are rolled via `engine.rng` directly in `roll.py`, `duelist.py`, `twin.py`.
- **Stunner** (Other racers' rolls): Aura on others. Modifier hooks only add deltas; base die cannot be forced. Needs a base-value override hook in `handle_perform_main_roll` and a central roll function for "all rolls".

**M13**

- **Mr. Dice Guy** (Replaces own main roll): Roll six dice via `engine.rng` and feed result as `roll_override`. `RollState` holds one `dice_value`; all six dice must count as rolled for triggers.
- **Show-Off** (Own main roll): Chained rolls inside one main-roll handler (loop with `engine.rng`, boolean decision per step), result via `roll_override`. All dice values must be exposed (Le Saboteur).

**M14**

- **Le Saboteur** (Other racers' main roll): Aura `RacerModifier` on others (analogue: `coach.py`, `gunk.py`) that flips direction when the die is 3. Needs backward main move and a reverse flag (double reverse = forward). Show-Off/Mr. Dice Guy need all dice values exposed.
- **Penguin** (Another racer passes; own turn while tripped): `PassingEvent` (passed == owner) + `push_trip`. Tripped turn: `run_turn` sets `main_move_consumed = True` and never pushes `PerformMainRollEvent`; `handle_perform_main_roll` skips tripped racers. Needs a roll-while-tripped path, trip cleared after the move. Doubling needs non-additive modifier.

**M15**

- **Hog Knight** (Setup; landing; passive roll modifier): Hog as `SpaceModifier` + `LandingHookMixin.on_land` that grants a `RacerModifier` (+2 via `RollModificationMixin`). `SetupPhaseMixin.on_setup` for the starting hog. Rules for hog ownership when a rider leaves/is eliminated are unclear (open question). Racers can hold two hogs.

**M16**

- **<NULL>** (Passive aura (position dependent)): Strip-and-restore, as proposed. `NullVoid(Ability, LifecycleManagedMixin)` keeps `stash: dict[int, list[Ability]]` and a `resync()` that (1) stashes `active_abilities` and calls `engine.clear_all_abilities(idx)` for each active racer strictly ahead of NULL, and (2) restores stashed racers no longer ahead via `engine._update_abilities(idx, stashed)` with the same instances (keeps state such as Kraken's once-per-race; `on_gain` re-runs, `on_setup` does not). Stripping also removes the stripped racer's own modifiers/auras through `on_loss`. -1: aura `RacerModifier` (cf. `coach.py` `CoachBoost`) added with `add_racer_modifier` to racers ahead; it is owned by NULL, so it survives the strip. `on_loss` restores everyone; drop stash entries of finished/eliminated racers. Call `resync()` from `PostMoveEvent`/`PostWarpEvent` (like `CoachAura`) and `RacerFinishedEvent`/`RacerEliminatedEvent`. Caveat: `PostMoveEvent` subscribers are ordered by distance from the current racer, so abilities of the mover (e.g. Mouth) can fire before NULL resyncs. Needs a resync call in `_finalize_committed_move`/`_finalize_committed_warp` before `publish_to_subscribers`. Warp swaps/simultaneous moves also need resync after all positions are set. Open rules question: strip applies on "ahead" only, so racers on the same space keep powers.

**M17**

- **Stepdad** (Passive aura; other racer's finish): Aura `RacerModifier` (+2). Needs a "left" convention (seating), re-targeting if stepkid is eliminated, `RacerFinishedEvent` for the bonus.
- **Cheatah** (Replaces own main roll): `racer.roll_override` (as in `legs.py`) for the chosen value, plus a guess decision by the right-hand neighbour and `skip_main_move`. Not a "roll" for triggers (`dice_value=None` already the case for overrides). Needs seating. AI: see [Cheatah guessing game](#cheatah-guessing-game).

**M18**

- **Switcharoo** (End of own turn): `TurnEndEvent` + `BooleanDecisionMixin` + `SelectionDecisionMixin` (target within 1 space). The swap changes who acts when: turn order follows players, so the two racers trade turn slots. Needs a seat order: `state.turn_order: list[int]` (seat -> racer idx), used by `advance_turn` (currently `(curr + 1) % n`), by `publish_to_subscribers` (currently `(owner_idx - curr) % count`), and for Cheatah/Stepdad neighbours. Swap = exchange the two entries. Chips belong to the player, so `victory_points` and the agent must follow the player. Tokens, positions and abilities stay on the racer. Result attribution must be per starting seat (player), otherwise Switcharoo's player is credited with the wrong racer. Mush-granted powers stay with the card (racer), no extra work. Open: swap heuristic for the agent (swap when the other racer is ahead or has the better power).

**M19**

- **Re-Runner** (Between races): Only affects later races of a multi-race game, so nothing to simulate per race. Register with an empty `RACER_ABILITIES` entry (generic racer). Expected extra VP in a multi-race game = her per-race VP in the single-race results, times the number of races she races in as an additional racer.

Every racer in section 1 appears exactly once.

### Twist notes by milestone

Card text and clarifications: section 2. Cards sorted by technical relation, then by effort.

**M22**

- **Roast Chicken on the Ground!** (Immediate): find the minimum position among active racers, `push_simultaneous_move` +7 for every racer on it (non-main move, so passing, landing and finish apply).
- **You Tromped on a Time Imp!** (Immediate): `eliminate_racer` on the racer whose move crossed 13 -> 14. Needs that racer passed into the card handler. The extra racer in the next race is not simulated (multi-race, E8), as with Re-Runner. Mush keeps nothing to simulate.

**M23**

- **Bonkbug Infestation at the Finish Line!** (Board modifier): `register_modifier` a `MoveDeltaTile(delta=-5)` on the last two tiles (`length - 2`, `length - 1`). "Stops on" matches `LandingHookMixin`. Check that the landing hook also fires for warps.
- **The Piñata is Leaking!** (Board modifier): a one-shot VP tile that unregisters itself in `on_land`, placed on every tile after the first corner without a feature, a modifier or a racer. Open: the racer that triggered the draw is already standing on tile 14, so it takes no chip.

**M24**

- **The Conveyor Belt is On!** (Persistent): `push_simultaneous_warp` all active racers to tile 1 (a warp, so no passing). The +3 is a `ConveyorBeltBonus` `RacerModifier` (`RollModificationMixin`, `owner_idx=None`) attached to every active racer at the draw, with its own source name. Racers added after the draw do not get it.
- **No Running by the Scrying Pool!** (Persistent): a `ScryingPoolRule` `RacerModifier` (`MainMoveInterceptorMixin`) attached to every active racer at the draw. `handle_execute_main_move` asks each interceptor first, and a final distance of 6+ (after modifiers) calls `eliminate_racer` instead of moving. Open: replaced rolls (Mole 6, Legs 5, Cheatah) count as a main move of that distance.

**M25**

- **Randomness has Randomly Ceased!** (Persistent): at the draw, each active racer rolls once through `roll_die` and gets a `FixedDie` `RacerModifier` (`FixedDieMixin`) holding the value. `roll_die` returns it for every later roll. Stunner's forced value still wins (twist is a track power). The stored value is final: Party Pooper does not reject or loop it. Multi-dice powers (Mr. Dice Guy, Show-Off) see identical dice.
- **Curse Wands for Everyone!** (Persistent): a `CurseWand` `RacerModifier` (`TurnSkipMixin`) on every active racer. `advance_turn` asks the current racer's modifiers for `seats_to_skip` (a `roll_die`) after each turn. Counting includes finished and eliminated seats. Landing on an inactive seat moves on to the next active one. `next_turn_override` (Hopfrog, Genius) wins, but the skip die is still rolled. One racer per player here, so one roll per turn.

**M26**

- **Swap Meet!** (Not simulated): the simulation measures how well racers perform, not players. A mid-race swap makes one result row belong to two racers, so the card is skipped. If drawn, it behaves like `Blank`.

**M27**

- **Alchemy Lab Containment Breach!** (Persistent): the piece is a `WeremouthPiece` modifier (position, start 0) hosted by the triggering racer, not an entry in the racer list, so sole-survivor and race-over counts, rank and finish are untouched. A generic `TurnEndHookMixin` hook, called after `TurnEndEvent`, rolls with the engine rng (not `roll_die`, so no die modifiers apply), moves it, and calls `eliminate_racer` on every active racer strictly between the old and new position. It stops past `length` and skips its roll when the race is over. Bite Mark racing as W.E.R.E.M.O.U.T.H.: no piece is added; the racer warps to the Start at the draw and gets one extra non-main `push_move` from a roll after every turn, with its existing passing elimination, and keeps its VP. Open: a racer on the Start when the piece begins to move is not passed, so it survives.

**M28**

- **Mirror World Theory Confirmed!** (Persistent): mirror once, then the race continues forward. Map `p -> length - p` for every active racer (finished and eliminated stay), static and dynamic tile keys, `first_corner`/`second_turn`, and positions stored inside tiles or abilities (`WarpTile` targets, hogs, Suckerfish target, Heckler turn start positions). Deltas keep their sign (forward stays forward). Apply after the drawing move completes: the draw happens mid-move 13 -> 14, so the mover is mapped after its passing, landing and finish checks. The mirror is plain assignment of numbers: no warp, move, passing, landing or any other event. Racers on the Start map to `length` and finish immediately via `check_finish`, in turn order starting after the current racer (clarification); the race ends at the second finisher. Open: a mirrored tile can sit under a racer that is already standing there, so it triggers only on the next landing.

**M29**

- **Season Finale!** (Deferred): a full first race, then a full second race, one game. Race 1 ends normally (race-end powers fire there: Gloth, Doppelgängster, Mastermind, Spoilsport). A Spoilsport cancel or a sole survivor ends the game with no second race. After race 1 ends with two finishers, start race 2: the 1st and 2nd finishers keep their `RacerState` (VP chips and tokens), everyone else is `sidelined` (inactive, abilities stripped, VP kept, not in race 2 at all, so Gloth gets no second bonus). Race 2 resets the finalists like a fresh race: position 15 (`second_turn`), `finish_position = None`, race 1 rank VP removed, abilities re-instantiated (Mush loses granted powers), once-per-race state fresh (Kraken), setup re-run (Spoilsport, Gloth if finalist, Mastermind, Nepo Baby on 12 = `first_corner`), `race_active = True`, 1st place takes the first turn. Race 2 payout: the winner gets `winner_vp[0] + winner_vp[1]`, the loser nothing from rank. Race 2 ends through the normal finish path. Open: `RaceEndedEvent` fires twice; `winning_turn_count` in the runner then reflects race 1.

**M30**

- **The Fans Demand Chaos!** (Immediate): draw two cards from the remaining deck and run both handlers in order. Needs every other card first. Open: drawing Fans again, drawing the same card twice, and Mirror World plus Season Finale.

Every card in section 2 appears exactly once.

## AI notes

### Cheatah guessing game

Solved strategy for Cheatah (picks a face) and the right-hand neighbour (guesses it). Treat it as a zero-sum hide-and-seek game: Cheatah gets the face's value unless the guess is correct, in which case he gets 0.

**Face value $u_k$** (k = 1..6): the main-move distance after modifiers (`get_current_modifiers`), plus a bonus for benefits (`get_benefit_at`: VP tile, forward boost, goal), minus a penalty for hazards (`get_hazard_at`: trip tile, back tile, hazardous racers on the tile). A sandbox turn per face (`simulate_turn_for`) is the more accurate, roughly 6× more expensive alternative.

**Solver:**

1. Drop faces with $u_k \le 0$. Getting caught is no worse than picking them.
2. Sort the remaining faces from highest to lowest value. Add them one by one to the support $S$ while the next value is greater than $V = \dfrac{|S|-1}{\sum_{k \in S} 1/u_k}$, the value with the current support.
3. Cheatah picks face $k$ with probability $p_k \propto 1/u_k$ (lower values are picked *more* often). The guesser guesses face $k$ with probability $q_k = 1 - V/u_k$.
4. Edge cases: no face with a positive value means Cheatah picks the best face. Exactly one positive face means Cheatah always picks it (no need to mix).

**Worked examples** ($V$ for Cheatah vs. the expected value of a normal roll):

| Scenario | Support | Cheatah mix | $V$ | Normal roll |
|---|---|---|---|---|
| Distance only | {6, 5, 4} | .27 / .32 / .41 | 3.24 | 3.50 |
| 6 worth 20 (e.g. goal or VP) | {6, 5} | .20 / .80 | 4.00 | 5.83 |
| 1 is a VP tile (worth 9) | {6, 5, 1} | .35 / .42 / .23 | 4.19 | 4.83 |
| 6 hits a back tile (worth −2) | {5, 4, 3} | .26 / .32 / .43 | 2.55 | 2.17 |
| 1, 2, 5 hit hazards (worth −3) | {6, 4, 3} | .22 / .33 / .44 | 2.67 | 0.67 |

**Findings:**

- The number of faces Cheatah should use is not fixed. It comes out of the solver and can be anything from 1 to 6. Do not force a minimum of 3.
- Leaving a face out is exploitable. A guesser who never guesses 4 hands Cheatah a free 4, which beats $V = 3.24$. In the distance-only case the guesser must guess 4 about 19% of the time.
- Strength: against a perfect guesser Cheatah is slightly worse than a normal roll when nothing near him matters. He beats a normal roll when hazards surround his landing spots. Those hazards can come from the track (trip and back tiles) or from opponents that punish certain landing spots (e.g. Baba Yaga, Hotel). At real tables, guessers are biased (they tend to guess 6), which adds value for Cheatah.
- The power-level benchmark (normal roll 3.5, plus the 1.5–2 extra that other racers' abilities give) is only for judging how strong Cheatah is. It does not change his choice.

**Implementation sketch:**

- Add a pure `solve_guessing_game(values: dict[int, float]) -> GuessingSolution` in `src/magsim/ai/guessing.py`. `GuessingSolution` is a frozen dataclass with `cheatah_mix`, `guesser_mix` and `value`.
- Smart agents sample their mix with `engine.rng`. Both sides compute the same $u_k$ from Cheatah's perspective.
- Baseline agents: Cheatah picks 6, the guesser guesses 6.
- Assumption: the guesser plays to minimise Cheatah's value. Guessing costs nothing, so this is close to the guesser's real incentive in a multiplayer race.

## Open questions

- **Spoilsport cancel + Gloth**: Gloth's race-end bonus also fires when Spoilsport cancels the race. Pinned in `tests/racers/test_open_questions.py`.
- **Multiple roll-replacing powers on one racer** (Mush, copies): Legs, Mole and Flip Flop each "skip rolling for the main move … instead". Implemented as one trade per turn: the first power to claim it wins (`engine.can_replace_main_roll`), so Legs + Flip Flop never swap and then move 5. Combining compatible trades is a plausible alternative reading. Pinned in `tests/racers/test_open_questions.py`.
- **Negative total movement**: a main move with a negative total is clamped to 0. Designers disagree: https://boardgamegeek.com/thread/3598754/negative-movement
- **Penguin recovery timing and re-trip**: a tripped Penguin rolls doubled and recovers right after his main move executes. A trip that arrives before the move executes is wiped. A trip picked up during the move (passing Banana, landing on a trip tile) persists, so he ends the move tripped and rolls doubled again next turn. Trips do not stack. Pinned in `tests/racers/test_open_questions.py`.
- **Mr. Dice Guy bust**: a no-duplicate roll is a bust that can be rerolled (Dicemonger, Magician). Without a reroll source the main move is skipped. Pinned in `tests/racers/test_open_questions.py`.
- **Multi-dice rolls and `dice_value`**: Show-Off's `dice_value` is his first die. Mr. Dice Guy's is the picked duplicate, `None` on a bust. Effects that read `dice_values` (Le Saboteur, Lackey, Inchworm) see every die, while effects that read `dice_value` (Magical Athlete, telemetry) see only that one. Pinned in `tests/racers/test_open_questions.py`.
- **Le Saboteur**: any 3 among the dice reverses the roller, even when the 3 is not the die he moves by. He does not trigger when the main move is replaced. Pinned in `tests/racers/test_open_questions.py`.
- **Party Pooper and Stunner with multi-dice rolls**: every die is a roll. Each 6 is rerolled (Pooper moves 1 per reroll, before the roller moves) and every die is forced to 1 in Stunner's aura. Pinned in `tests/racers/test_open_questions.py`.
- **NULL and passing order**: Centaur on 1, Legs on 2, NULL on 3, Centaur rolls 3 and passes both. Does anyone get pushed back? Currently nobody: passes resolve after the move, when Centaur is already stripped for landing ahead of NULL. Pinned in `tests/racers/test_open_questions.py`.
- **NULL passes a stripped racer**: NULL passes Banana. Currently Banana regains its power the moment NULL passes it and trips NULL. Pinned in `tests/racers/test_open_questions.py`.
- **NULL and first-turn powers**: Mastermind is stripped on his first turn and regains his power later. Currently he predicts at the first turn start after he regains it. Pinned in `tests/racers/test_open_questions.py`.
