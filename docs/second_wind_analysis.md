# Second Wind Expansion: Required Changes

Source: `docs/Magical_Athlete_Second_Wind_Rules.pdf`. Target: `src/magsim`.

Status: runner table done. Other sections are placeholders.

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

| # | Runner | Ability text | Trigger | Code hook | Difficulty | Gaps |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Bite Mark (HUUAARRGGHHH!!!!) | When I roll a 1 or 2 for my main move, I transform into a W.E.R.E.M.O.U.T.H. who eliminates any racers I pass. | On own main roll result | `RollResultEvent` (MAIN_ACT precedes `ExecuteMainMoveEvent`, so transform happens before the move). Swap abilities via `replace_core_abilities`. New W.E.R.E.M.O.U.T.H. ability on `PassingEvent` (passer == owner), elimination like `racers/mouth.py`. | 🟢 | E13 |
| 2 | Critic (BON MOTS) | I can make racers ahead of me reroll their main move once per turn. | Other racer's roll window | `RollModificationWindowEvent` (target != owner, target ahead) + `BooleanDecisionMixin` + `trigger_reroll`. Once-per-turn reset on `PreTurnStartEvent`. Analogue: `dicemonger.py` (reroll for someone else). | 🟢 | |
| 3 | Gloth (GLORPOR) | I get -1 to my main move. When the race ends, I get 3 points if I'm not past the second corner. | Passive roll modifier; race end | `RacerModifier` + `RollModificationMixin` (analogue: `blimp.py`, `party_animal.py`). Race-end bonus has no hook today (`check_race_over_condition` emits no event). Needs corner positions. | 🟡 | E5, E9 |
| 4 | Blunderdog (BLUNDERTRAIL) | When I'm in last place, triple my main move roll. When I'm not, I move backwards for my main move instead. | Passive roll modifier (self) | `RollModificationMixin`. Tripling needs non-additive modifiers. Backward main move is not possible: `MoveDistanceQuery.final_value = max(0, ...)` and `handle_execute_main_move` only moves if `dist > 0`. | 🟡 | E1 |
| 5 | Diva (QUELLE DRAMATIQUE!) | If I'm in last place at the start of my turn, I swap spaces with the lead racer. Otherwise I swap with the last place racer. | Start of own turn | `TurnStartEvent` + `SimultaneousWarpCmdEvent` (`push_simultaneous_warp`). Tie choice via `SelectionDecisionMixin`. Analogue: `flip_flop.py`, `hypnotist.py`. | 🟢 | |
| 6 | Hog Knight (PIGGYBACK) | I start my race on a hog that gives +2 to its rider's main move. When a racer stops on the hog's space, they take it. | Setup; landing; passive roll modifier | Hog as `SpaceModifier` + `LandingHookMixin.on_land` that grants a `RacerModifier` (+2 via `RollModificationMixin`). `SetupPhaseMixin.on_setup` for the starting hog. Rules for hog ownership when a rider leaves/is eliminated are unclear (open question). Racers can hold two hogs. | 🟡 | E11 |
| 7 | Cheatah (SLEIGHT OF PAW) | Instead of rolling for my main move, I secretly set my die to any number. If the player to my right guesses the number, I don't move. | Replaces own main roll | `racer.roll_override` (as in `legs.py`) for the chosen value, plus a guess decision by the right-hand neighbour and `skip_main_move`. Not a "roll" for triggers (`dice_value=None` already the case for overrides). Needs seating. | 🟡 | E7 |
| 8 | Doppelgängster (TAKE A DIVE) | The racer who finishes 1st is eliminated instead. I get their power. | On first finish | No pre-finish interception: `check_finish` calls `mark_finished` directly. Needs veto in `check_finish`/`mark_finished`, elimination (no VP, no finish powers), ability copy. | 🟡 | E6, E13, E14 |
| 9 | Hopfrog (BOIOIOING) | When I end my turn 1 space behind a racer, I take an extra turn. | End of own turn | `TurnEndEvent` + `state.next_turn_override`. Analogue: `genius.py`, `skipper.py`. | 🟢 | |
| 10 | Hotel (MONOPOLIZE) | When a racer stops on my space, they pay me 1 point. If they can't, they trip. | When another racer stops on my space | `PostMoveEvent`/`PostWarpEvent` (end tile == owner position) + `racer.victory_points` transfer + `push_trip`. Points live on the racer, so "can't pay" is `victory_points < 1`. | 🟢 | E7 |
| 11 | Kraken (GET OVER HERE) | Once per race, at the start of my turn, I can warp all other racers to my space and trip them. | Start of own turn, once per race | `TurnStartEvent` + `BooleanDecisionMixin` + `SimultaneousWarpCmdEvent` + `push_trip`. Analogue: `party_animal.py` (pull). | 🟢 | |
| 12 | Mole (TUNNELIN') | If there aren't any racers within 1 space of me, I can skip rolling for my main move and move 6 instead. | Start of own turn | `TurnStartEvent` + `racer.roll_override = (source, 6)` (as in `legs.py`). Counts as main move. | 🟢 | |
| 13 | Icarus (FLIGHT RISK) | I get +3 to my main move. If I roll a 6 for my main move, I'm eliminated. | Passive roll modifier; own roll result | `RollModificationMixin` (+3) + `RollResultEvent` (`dice_value == 6`) + elimination as in `mouth.py`. | 🟢 | E13 |
| 14 | Le Saboteur (TROIS REVOIR) | When other racers roll a 3 for their main move, they move backwards instead. | Other racers' main roll | Aura `RacerModifier` on others (analogue: `coach.py`, `gunk.py`) that flips direction when the die is 3. Needs backward main move and a reverse flag (double reverse = forward). Show-Off/Mr. Dice Guy need all dice values exposed. | 🟡 | E1, E2 |
| 15 | Mr. Dice Guy (YES! MORE!) | I roll all six dice for my main move and pick any number that was rolled more than once. If I roll one of each number, I don't move. | Replaces own main roll | Roll six dice via `engine.rng` and feed result as `roll_override`. `RollState` holds one `dice_value`; all six dice must count as rolled for triggers. | 🟡 | E2 |
| 16 | Kingtripper (REGISLIDE) | At the start of my turn, I can trip the lead racer. | Start of own turn | `TurnStartEvent` + `BooleanDecisionMixin` + `push_trip`. Tie choice via `SelectionDecisionMixin`. Analogue: `baba_yaga.py`, `hypnotist.py`. | 🟢 | |
| 17 | Magical Athlete (FLEXOMANCY) | When I roll this for my main move: 1 move 7; 2 last place racer warps to me; 3 I warp to another racer and trip them; 4 move 4 and take an extra turn; 5 lead racer moves backwards 5; 6 move 6 and trip any racers I pass. | Own main roll result (per die value) | `RollResultEvent` + `roll_override`/`skip_main_move` + `push_warp`/`push_simultaneous_warp`/`push_trip`/`next_turn_override`. 5 needs non-main negative `push_move` on another racer (movement code handles negative steps; verify clamp and passing). 6 needs `PassingEvent` filter. | 🟡 | E12 |
| 18 | Mush (GLOBSTER MASH) | When I roll a 1 or 2 for my main move, I draw a racer card and get its power for the rest of the race. | Own main roll result | `RollResultEvent` + `engine.draw_racers` + `grant_ability`. `replace_core_abilities` only preserves `ExternalAbilityMixin` abilities, so granted abilities must be wrapped. Stacks; copies don't inherit added powers. | 🟡 | E14 |
| 19 | Nemesis (GRUDGE MATCH) | When other racers roll for their main move, I can roll too. If I roll the same, I move that amount. | Other racers' roll result | `RollResultEvent` (other racer) + `engine.rng.randint` + `push_move` queued after their move. Analogue: `duelist.py` (extra die). | 🟢 | E2 |
| 20 | Overtaker (SKULLDIGGERY) | I get +1 to my main move for each racer ahead of me. | Passive roll modifier | `RollModificationMixin`, count active racers with higher position (finished racers are inactive). | 🟢 | |
| 21 | Re-Runner (RUN IT BACK) | After my first race, I race as an extra racer for my player in all remaining races. | Between races | Only affects later races of a multi-race game, so nothing to simulate per race. Register with an empty `RACER_ABILITIES` entry (generic racer). Expected extra VP in a multi-race game = her per-race VP in the single-race results, times the number of races she races in as an additional racer. | ⚪ | |
| 22 | Nepo Baby (HUGELY RICH) | I start the race on the first corner of the track. | Setup | `SetupPhaseMixin.on_setup` sets position (cf. `RacerConfig.start_pos`). Needs corner tile index per board. | 🟡 | E9 |
| 23 | Party Pooper (NOISE COMPLAINT) | All sixes must be rerolled. When they are, I move 1. | Any racer's roll (all rolls, not just main) | `RollModificationWindowEvent` + `trigger_reroll` for main rolls. "All rolls" needs a central die roll function; dice are rolled via `engine.rng` directly in `roll.py`, `duelist.py`, `twin.py`. | 🟡 | E2 |
| 24 | Show-Off (GUYS, WATCH!) | After I roll for my main move, I can keep rolling and adding each amount to my move. If I ever roll the same or lower, I don't move. | Own main roll | Chained rolls inside one main-roll handler (loop with `engine.rng`, boolean decision per step), result via `roll_override`. All dice values must be exposed (Le Saboteur). | 🟡 | E2 |
| 25 | <NULL> ([VOID]) | Racers ahead of me get -1 to their main move and have no powers. | Passive aura (position dependent) | Strip-and-restore, as proposed. `NullVoid(Ability, LifecycleManagedMixin)` keeps `stash: dict[int, list[Ability]]` and a `resync()` that (1) stashes `active_abilities` and calls `engine.clear_all_abilities(idx)` for each active racer strictly ahead of NULL, and (2) restores stashed racers no longer ahead via `engine._update_abilities(idx, stashed)` with the same instances (keeps state such as Kraken's once-per-race; `on_gain` re-runs, `on_setup` does not). Stripping also removes the stripped racer's own modifiers/auras through `on_loss`. -1: aura `RacerModifier` (cf. `coach.py` `CoachBoost`) added with `add_racer_modifier` to racers ahead; it is owned by NULL, so it survives the strip. `on_loss` restores everyone; drop stash entries of finished/eliminated racers. Call `resync()` from `PostMoveEvent`/`PostWarpEvent` (like `CoachAura`) and `RacerFinishedEvent`/`RacerEliminatedEvent`. Caveat: `PostMoveEvent` subscribers are ordered by distance from the current racer, so abilities of the mover (e.g. Mouth) can fire before NULL resyncs. Needs a resync call in `_finalize_committed_move`/`_finalize_committed_warp` before `publish_to_subscribers`. Warp swaps/simultaneous moves also need resync after all positions are set. Open rules question: strip applies on "ahead" only, so racers on the same space keep powers. | 🟡 | E4 |
| 26 | Penguin (TUMMY TIME) | Whenever a racer passes me, I trip. While I'm tripped, double my roll for my main move instead of skipping it. | Another racer passes; own turn while tripped | `PassingEvent` (passed == owner) + `push_trip`. Tripped turn: `run_turn` sets `main_move_consumed = True` and never pushes `PerformMainRollEvent`; `handle_perform_main_roll` skips tripped racers. Needs a roll-while-tripped path, trip cleared after the move. Doubling needs non-additive modifier. | 🟡 | E1, E10 |
| 27 | Soulmate (TWIN FLAME) | Before my race, I pick any opposing racer. When I start my turn within 5 spaces of them, I warp to their space. | Setup; start of own turn | `SetupPhaseMixin.on_setup` + `SelectionDecisionMixin` (analogue: `egg.py`, `twin.py`) + `TurnStartEvent` + `push_warp`. | 🟢 | |
| 28 | Speed Demon (TERMINAL VELOCITY) | I get +1 to my main move for each point my player has. I am eliminated if I'm 4+ spaces in the lead at the start of my turn. | Passive roll modifier; start of own turn | `RollModificationMixin` using `victory_points`; `TurnStartEvent` + elimination as in `mouth.py`. | 🟢 | E7, E13 |
| 29 | Streaker (EXHIBIT B) | When I pass any number of racers during my main move, I get 1 point. | Own main move passes | `PassingEvent` (passer == owner). `PassingEvent` has no `is_main` flag (`MoveCmdEvent.is_main` exists), and needs once-per-move dedupe. | 🟡 | E12 |
| 30 | Tail (REAR END) | At the start of my turn, I can warp to the space behind the next racer ahead of me. | Start of own turn | `TurnStartEvent` + `BooleanDecisionMixin` + `push_warp`. Analogue: `hypnotist.py`, `third_wheel.py`. | 🟢 | |
| 31 | Spoilsport (CRY FOUL) | If all other racers are 5+ spaces ahead of me at the start of my turn, the race is cancelled and I get 3 points. | Start of own turn | `TurnStartEvent` + new race-cancel path (no 1st/2nd points unless already finished). Today `race_active` ends only via 2 finishers or sole survivor; result recording assumes finishers. | 🟡 | E5 |
| 32 | Stunner (STOP TRAFFIC) | Other racers within 1 space of me roll a 1 for all rolls. | Other racers' rolls | Aura on others. Modifier hooks only add deltas; base die cannot be forced. Needs a base-value override hook in `handle_perform_main_roll` and a central roll function for "all rolls". | 🟡 | E2, E3 |
| 33 | The Hose (POWER WASH) | At the end of my turn, roll a die and trip every racer within that many spaces ahead of me. | End of own turn | `TurnEndEvent` + `engine.rng` + `push_trip`. | 🟢 | E2 |
| 34 | Stepdad (STEP UP) | The racer to my left gets +2 to their main move. If they finish 1st, I get 3 points. | Passive aura; other racer's finish | Aura `RacerModifier` (+2). Needs a "left" convention (seating), re-targeting if stepkid is eliminated, `RacerFinishedEvent` for the bonus. | 🟡 | E7 |
| 35 | Switcharoo (MARSWAPIAL) | When I end my turn within 1 space of another racer, I can swap who controls which racer: their player takes my card and I take theirs. | End of own turn | `TurnEndEvent` + `BooleanDecisionMixin` + `SelectionDecisionMixin` (target within 1 space). The swap changes who acts when: turn order follows players, so the two racers trade turn slots. Needs a seat order: `state.turn_order: list[int]` (seat -> racer idx), used by `advance_turn` (currently `(curr + 1) % n`), by `publish_to_subscribers` (currently `(owner_idx - curr) % count`), and for Cheatah/Stepdad neighbours. Swap = exchange the two entries. Chips belong to the player, so `victory_points` and the agent must follow the player. Tokens, positions and abilities stay on the racer. Result attribution must be per starting seat (player), otherwise Switcharoo's player is credited with the wrong racer. Mush-granted powers stay with the card (racer), no extra work. Open: swap heuristic for the agent (swap when the other racer is ahead or has the better power). | 🟡 | E7 |
| 36 | Understudy (THE METHOD) | Before my race, I copy an opposing racer's power. | Setup | `SetupPhaseMixin.on_setup` + `engine.instantiate_racer_abilities(name)` (analogue: `copycat.py`, `twin.py`). Setup order matters: other racers' abilities may not be assigned yet, use racer names. Hog Knight copy needs a hog piece. | 🟢 | E11 |

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

## 2. Twist cards

_TODO._ Rulebook lists: Bonkbug Infestation, Mirror World Theory, Curse Wands for Everyone, The Piñata is Leaking, Alchemy Lab Containment Breach, The Fans Demand Chaos, The Conveyor Belt is On, No Running by the Scrying Pool, Roast Chicken on the Ground, Swap Meet, Randomness has Randomly Ceased, Season Finale, You Tromped on a Time Imp.

## 3. Boards and tracks

_TODO._ Twisty Twirl (twist), Whirly World (whirls). Track order: Twisty, Whirly, Twisty, Whirly.

## 4. Implementation order

Low-hanging fruit first, then engine changes grouped by gap, from small to large. Rules for every milestone are in [AGENT.md](../AGENT.md).

| Milestone | Racers | Engine work | Notes |
| --- | --- | --- | --- |
| M1 ✅ | Overtaker, Tail, Kingtripper | none | Passive modifier, two start-of-turn decisions. |
| M2 ✅ | Diva, Hopfrog, Mole | none | Swap warp, extra turn, roll override. |
| M3 ✅ | Kraken, Soulmate, Critic | none | Once per race, setup selection, reroll for others. |
| M4 | Hotel, Nemesis, The Hose | none | Hotel uses racer `victory_points` for now (E7 revisit in M17). Nemesis and The Hose use `engine.rng` directly (E2 revisit in M12/M13). |
| M5 | Icarus, Bite Mark, Speed Demon | E13 shared elimination helper (extract from `mouth.py`) | Speed Demon uses racer `victory_points` for now. |
| M6 | Nepo Baby | E9 corner positions on `Board` | Gloth reuses this in M9. |
| M7 | Streaker, Magical Athlete | E12 `is_main` on `PassingEvent` | Magical Athlete 5 needs a negative non-main `push_move`. |
| M8 | Blunderdog | E1 backward main move, non-additive modifiers | Reused by Le Saboteur and Penguin. |
| M9 | Spoilsport, Gloth | E5 race-end event and race cancel | Needs E9 from M6. |
| M10 | Mush, Understudy | E14 runtime ability grant that survives `replace_core_abilities` | Understudy is easy but fits here. Its Hog Knight copy case waits for M15. |
| M11 | Doppelgängster | E6 pre-finish interception | Needs E13 and E14. |
| M12 | Party Pooper, Stunner | E2 central die roll, E3 base-die override by aura | Re-route Nemesis and The Hose through the central roll. |
| M13 | Mr. Dice Guy, Show-Off | E2 multi-dice roll state | All dice values exposed to triggers. |
| M14 | Le Saboteur, Penguin | E1 (done), E10 roll while tripped | Le Saboteur needs E1 and E2, Penguin needs E1. |
| M15 | Hog Knight | E11 pieces (hogs) | Then add the Hog Knight case to Understudy. |
| M16 | <NULL> | E4 resync hook before `publish_to_subscribers` | Strip-and-restore. |
| M17 | Stepdad, Cheatah | E7 `turn_order` seat list (read-only use) | Switch `advance_turn` and `publish_to_subscribers` to the seat list. |
| M18 | Switcharoo | E7 swap of seats, `victory_points`, agents; per-seat result attribution | Result attribution is in `simulation/`, which AGENT.md forbids. Ask first. Revisit Hotel, Speed Demon. |
| M19 | Re-Runner | `RACER_ABILITIES` entry only | Generic racer. |
| M20 | Whirly World board (warp) | New board type, warp tiles | Easy. |
| M21 | Twisty Twirl board (twist) | Twist mechanics | Very hard. Twist cards (section 2) are scheduled together with it. |

Every racer in section 1 appears exactly once.