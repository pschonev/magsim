import heapq
import logging
import random
from dataclasses import dataclass, field
from typing import Literal, Sequence

# ------------------------------
# IDs and static configuration
# ------------------------------

RacerName = Literal[
    "Centaur",
    "BigBaby",
    "Scoocher",
    "Banana",
    "Copycat",
    "Gunk",
    "PartyAnimal",
]

AbilityName = Literal[
    # triggered abilities
    "Trample",  # Centaur: move passed racers back 2
    "BigBabyPush",  # Big Baby: push landing racer back 1
    "BananaTrip",  # Banana: trip racers who pass
    "ScoochStep",  # Scoocher: move 1 whenever any ability is used
    "CopyLead",  # Copycat: copy abilities of leader
    "Slime",  # Gunk: -1 to others' main move
    "PartyPull",  # Party Animal: pull all 1 closer at turn start
    "PartyBoost",  # Party Animal: +1 main move per co-occupant
]

TRIP_SPACES: set[int] = {4, 10, 18}
FINISH_SPACE: int = 20
WIN_VP: int = 5

# Which abilities each racer starts with (no MainMove here, it is a rule)
RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "Centaur": {"Trample"},
    "BigBaby": {"BigBabyPush"},
    "Scoocher": {"ScoochStep"},
    "Banana": {"BananaTrip"},
    "Copycat": {"CopyLead"},
    "Gunk": {"Slime"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
}


# ------------------------------
# Core state
# ------------------------------


@dataclass(slots=True)
class RacerState:
    idx: int
    name: RacerName
    position: int = 0
    tripped: bool = False
    finished: bool = False
    victory_points: int = 0
    abilities: set[AbilityName] = field(default_factory=set)


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    finished_order: list[int] = field(default_factory=list)


# ------------------------------
# Events and scheduling
# ------------------------------


class GameEvent:
    """Marker base class."""

    pass


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollAndMainMoveEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class CmdMoveEvent(GameEvent):
    racer_idx: int
    distance: int
    is_main_move: bool
    source_racer_idx: int | None
    source_ability: AbilityName | None


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class LandingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int
    ability_id: AbilityName


@dataclass(order=True)
class ScheduledEvent:
    # priority key for heapq: smaller sorts earlier
    phase: int
    turn_distance: int
    serial: int
    event: GameEvent = field(compare=False)


class Phase:
    SYSTEM = 0
    BOARD = 10
    ABILITY = 20
    MOVE = 30
    CLEANUP = 100


# ------------------------------
# Engine
# ------------------------------

logger = logging.getLogger("magical_athlete")


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    queue: list[ScheduledEvent] = field(default_factory=list)
    _serial: int = 0
    race_over: bool = False
    # for simple loop detection within a turn
    seen_signatures: set[int] = field(default_factory=set)

    # ---------- scheduling ----------

    def push_event(
        self,
        event: GameEvent,
        *,
        phase: int,
        reactor_idx: int | None = None,
    ) -> None:
        """Schedule an event with phase and relative turn distance."""
        self._serial += 1
        current = self.state.current_racer_idx
        if reactor_idx is None or not self.state.racers:
            dist = 0
        else:
            n = len(self.state.racers)
            dist = (reactor_idx - current) % n

        sched = ScheduledEvent(
            phase=phase,
            turn_distance=dist,
            serial=self._serial,
            event=event,
        )
        heapq.heappush(self.queue, sched)
        logger.info(
            "Enqueued %s (phase=%s, dist=%s, serial=%s)",
            event,
            phase,
            dist,
            self._serial,
        )

    # ---------- main loop ----------

    def run_race(self) -> None:
        """Run turns until two racers have finished."""
        while not self.race_over:
            self.start_turn()
            self.process_events_for_turn()
            self.advance_turn()

    def start_turn(self) -> None:
        self.seen_signatures.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        logger.info("=== Turn start: Racer %s (#%d) ===", racer.name, cr)
        self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM, reactor_idx=cr)

    def process_events_for_turn(self) -> None:
        while self.queue and not self.race_over:
            sched = heapq.heappop(self.queue)
            event = sched.event
            if self.is_loop(event):
                logger.warning("Loop detected for event %s – skipping", event)
                continue
            logger.info("Processing %s", event)
            self.handle_event(event)

    def advance_turn(self) -> None:
        if self.race_over:
            return
        n = len(self.state.racers)
        # advance to next non-finished racer
        for _ in range(n):
            self.state.current_racer_idx = (self.state.current_racer_idx + 1) % n
            if not self.state.racers[self.state.current_racer_idx].finished:
                break

    # ---------- loop detection ----------

    def is_loop(self, event: GameEvent) -> bool:
        """Very simple per-turn loop detection."""
        positions = tuple(r.position for r in self.state.racers)
        tripped = tuple(r.tripped for r in self.state.racers)
        key = (type(event).__name__, positions, tripped)
        sig = hash(key)
        if sig in self.seen_signatures:
            return True
        self.seen_signatures.add(sig)
        return False

    # ---------- event dispatch ----------

    def handle_event(self, event: GameEvent) -> None:
        match event:
            case TurnStartEvent(racer_idx):
                self.on_turn_start(racer_idx)
            case RollAndMainMoveEvent(racer_idx):
                self.on_roll_and_main_move(racer_idx)
            case CmdMoveEvent():
                self.on_cmd_move(event)
            case PassingEvent():
                self.on_passing(event)
            case LandingEvent():
                self.on_landing(event)
            case AbilityTriggeredEvent():
                self.on_ability_triggered(event)
            case _:
                logger.warning("Unhandled event type: %s", event)

    # ---------- helpers ----------

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def active_and_not_finished(self, idx: int) -> bool:
        r = self.state.racers[idx]
        return not r.finished

    def emit_ability_trigger(self, source_idx: int, ability: AbilityName) -> None:
        """Every ability (not main move, not board) should call this."""
        r = self.get_racer(source_idx)
        if r.finished:
            return
        evt = AbilityTriggeredEvent(source_racer_idx=source_idx, ability_id=ability)
        self.push_event(evt, phase=Phase.ABILITY, reactor_idx=source_idx)

    # ---------- turn start ----------

    def on_turn_start(self, racer_idx: int) -> None:
        racer = self.get_racer(racer_idx)
        if racer.finished:
            logger.info(
                "Racer %s (#%d) already finished; skipping turn", racer.name, racer_idx
            )
            return

        # Tripped: stand up instead of moving
        if racer.tripped:
            logger.info(
                "Racer %s (#%d) is tripped and stands up", racer.name, racer_idx
            )
            racer.tripped = False
            return

        # Turn-start abilities: PartyPull and CopyLead
        self.run_turn_start_abilities(racer_idx)

        # Now schedule main move (system rule, not an ability)
        self.push_event(
            RollAndMainMoveEvent(racer_idx), phase=Phase.SYSTEM, reactor_idx=racer_idx
        )

    def run_turn_start_abilities(self, racer_idx: int) -> None:
        racer = self.get_racer(racer_idx)
        abilities = racer.abilities

        # Copycat: copy abilities of current leader (excluding self)
        if "CopyLead" in abilities:
            self.ability_copy_lead(racer_idx)

        # Party Animal: pull everyone 1 closer
        if "PartyPull" in abilities:
            self.ability_party_pull(racer_idx)

    # ---------- main move and modifiers ----------

    def on_roll_and_main_move(self, racer_idx: int) -> None:
        racer = self.get_racer(racer_idx)
        if racer.finished:
            logger.info(
                "Racer %s (#%d) already finished; no main move", racer.name, racer_idx
            )
            return

        roll = self.rng.randint(1, 6)
        logger.info("Racer %s (#%d) rolls %d", racer.name, racer_idx, roll)

        distance = self.apply_move_modifiers(racer_idx, roll)
        logger.info(
            "Racer %s (#%d) main move distance: %d", racer.name, racer_idx, distance
        )

        if distance != 0:
            move_evt = CmdMoveEvent(
                racer_idx=racer_idx,
                distance=distance,
                is_main_move=True,
                source_racer_idx=None,
                source_ability=None,
            )
            self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=racer_idx)

    def apply_move_modifiers(self, target_idx: int, base: int) -> int:
        """Gunk and PartyBoost."""
        steps = base

        target = self.get_racer(target_idx)

        # Gunk: everyone else's main move is -1
        for r in self.state.racers:
            if "Slime" in r.abilities and not r.finished and r.idx != target_idx:
                logger.info(
                    "Gunk (#%d) Slime modifies main move of %s (#%d) by -1",
                    r.idx,
                    target.name,
                    target_idx,
                )
                steps -= 1
                self.emit_ability_trigger(r.idx, "Slime")

        # PartyBoost: +1 per co-occupant on Party Animal's space, only for Party Animal's own main move
        if "PartyBoost" in target.abilities and not target.finished:
            same_tile = [
                r
                for r in self.state.racers
                if r.idx != target_idx
                and not r.finished
                and r.position == target.position
            ]
            bonus = len(same_tile)
            if bonus:
                logger.info(
                    "Party Animal (#%d) PartyBoost gives +%d move (co-occupants: %s)",
                    target_idx,
                    bonus,
                    [r.idx for r in same_tile],
                )
                steps += bonus
                self.emit_ability_trigger(target_idx, "PartyBoost")

        if steps < 0:
            steps = 0
        return steps

    # ---------- movement pipeline ----------

    def on_cmd_move(self, evt: CmdMoveEvent) -> None:
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            logger.info(
                "Racer %s (#%d) is finished; ignoring move", racer.name, racer.idx
            )
            return

        start = racer.position
        dist = evt.distance
        if dist == 0:
            # still produce LandingEvent at current tile
            self.push_event(
                LandingEvent(mover_idx=evt.racer_idx, tile_idx=start),
                phase=Phase.SYSTEM,
                reactor_idx=evt.racer_idx,
            )
            return

        direction = 1 if dist > 0 else -1
        steps = abs(dist)

        logger.info(
            "CmdMove: %s (#%d) moves from %d by %d (source_racer=%s, source_ability=%s)",
            racer.name,
            racer.idx,
            start,
            dist,
            evt.source_racer_idx,
            evt.source_ability,
        )

        # Emit passing events
        for i in range(1, steps):
            tile = start + direction * i
            if tile > FINISH_SPACE:
                break
            self.push_event(
                PassingEvent(mover_idx=evt.racer_idx, tile_idx=tile),
                phase=Phase.SYSTEM,
                reactor_idx=evt.racer_idx,
            )

        # Final landing
        final_tile = start + dist
        self.push_event(
            LandingEvent(mover_idx=evt.racer_idx, tile_idx=final_tile),
            phase=Phase.SYSTEM,
            reactor_idx=evt.racer_idx,
        )

    def on_passing(self, evt: PassingEvent) -> None:
        mover = self.get_racer(evt.mover_idx)
        if mover.finished:
            return

        logger.info(
            "PassingEvent: %s (#%d) passes tile %d",
            mover.name,
            mover.idx,
            evt.tile_idx,
        )

        # Active player's ability (Trample) first
        if "Trample" in mover.abilities:
            self.ability_centaur_trample(evt)

        # Other players' abilities: BananaTrip, in turn order after active
        for offset in range(1, len(self.state.racers)):
            idx = (self.state.current_racer_idx + offset) % len(self.state.racers)
            r = self.get_racer(idx)
            if r.finished:
                continue
            # BananaTrip: trips movers who pass Banana's space
            if "BananaTrip" in r.abilities and r.position == evt.tile_idx:
                self.ability_banana_trip(banana_idx=r.idx, mover_idx=mover.idx)

    def on_landing(self, evt: LandingEvent) -> None:
        mover = self.get_racer(evt.mover_idx)
        if mover.finished:
            return

        logger.info(
            "LandingEvent: %s (#%d) lands on %d",
            mover.name,
            mover.idx,
            evt.tile_idx,
        )

        # Update position
        mover.position = evt.tile_idx

        # Check finish
        if mover.position > FINISH_SPACE:
            self.handle_finish(mover.idx)
            return

        # Board tripping spaces
        if mover.position in TRIP_SPACES:
            logger.info(
                "Board: tile %d trips %s (#%d)",
                mover.position,
                mover.name,
                mover.idx,
            )
            mover.tripped = True

        # Other players' landing-triggered abilities (BigBabyPush) in order
        for offset in range(0, len(self.state.racers)):
            idx = (self.state.current_racer_idx + offset) % len(self.state.racers)
            r = self.get_racer(idx)
            if r.finished or r.idx == mover.idx:
                continue
            if "BigBabyPush" in r.abilities and r.position == mover.position:
                self.ability_big_baby_push(baby_idx=r.idx, victim_idx=mover.idx)

    def handle_finish(self, racer_idx: int) -> None:
        racer = self.get_racer(racer_idx)
        if racer.finished:
            return

        racer.finished = True
        racer.position = FINISH_SPACE + 1
        self.state.finished_order.append(racer_idx)
        order = len(self.state.finished_order)
        logger.info(
            "Racer %s (#%d) finishes in place %d",
            racer.name,
            racer.idx,
            order,
        )
        if order == 1:
            racer.victory_points += WIN_VP
            logger.info(
                "Racer %s (#%d) gains %d VP (total %d)",
                racer.name,
                racer.idx,
                WIN_VP,
                racer.victory_points,
            )
        if order >= 2:
            logger.info("Second finisher reached; race over.")
            self.race_over = True
            self.queue.clear()

    # ---------- abilities ----------

    def ability_centaur_trample(self, evt: PassingEvent) -> None:
        mover = self.get_racer(evt.mover_idx)
        if "Trample" not in mover.abilities:
            return
        victims = [
            r
            for r in self.state.racers
            if r.position == evt.tile_idx and not r.finished and r.idx != mover.idx
        ]
        if not victims:
            return
        logger.info(
            "Centaur Trample: %s (#%d) tramples racers %s on tile %d",
            mover.name,
            mover.idx,
            [v.idx for v in victims],
            evt.tile_idx,
        )
        for v in victims:
            move_evt = CmdMoveEvent(
                racer_idx=v.idx,
                distance=-2,
                is_main_move=False,
                source_racer_idx=mover.idx,
                source_ability="Trample",
            )
            self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=mover.idx)
        self.emit_ability_trigger(mover.idx, "Trample")

    def ability_banana_trip(self, banana_idx: int, mover_idx: int) -> None:
        banana = self.get_racer(banana_idx)
        mover = self.get_racer(mover_idx)
        if mover.finished:
            return
        logger.info(
            "BananaTrip: %s (#%d) trips %s (#%d)",
            banana.name,
            banana.idx,
            mover.name,
            mover.idx,
        )
        mover.tripped = True
        self.emit_ability_trigger(banana.idx, "BananaTrip")

    def ability_big_baby_push(self, baby_idx: int, victim_idx: int) -> None:
        baby = self.get_racer(baby_idx)
        victim = self.get_racer(victim_idx)
        if victim.finished:
            return
        logger.info(
            "BigBabyPush: %s (#%d) pushes %s (#%d) back 1",
            baby.name,
            baby.idx,
            victim.name,
            victim.idx,
        )
        move_evt = CmdMoveEvent(
            racer_idx=victim.idx,
            distance=-1,
            is_main_move=False,
            source_racer_idx=baby.idx,
            source_ability="BigBabyPush",
        )
        self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=baby.idx)
        self.emit_ability_trigger(baby.idx, "BigBabyPush")

    def ability_copy_lead(self, copy_idx: int) -> None:
        copycat = self.get_racer(copy_idx)
        # find leaders (highest position, not finished, not self)
        active = [r for r in self.state.racers if not r.finished and r.idx != copy_idx]
        if not active:
            return
        max_pos = max(r.position for r in active)
        leaders = [r for r in active if r.position == max_pos]
        leader = self.rng.choice(leaders)
        # copy abilities from definition: use RACER_ABILITIES of leader.name
        new_abilities = set(RACER_ABILITIES.get(leader.name, set()))
        # keep CopyLead itself
        new_abilities.add("CopyLead")
        copycat.abilities = new_abilities
        logger.info(
            "CopyLead: %s (#%d) copies abilities of %s (#%d): %s",
            copycat.name,
            copycat.idx,
            leader.name,
            leader.idx,
            sorted(copycat.abilities),
        )
        self.emit_ability_trigger(copycat.idx, "CopyLead")

    def ability_party_pull(self, party_idx: int) -> None:
        party = self.get_racer(party_idx)
        if party.finished:
            return
        logger.info(
            "PartyPull: %s (#%d) pulls everyone 1 step closer",
            party.name,
            party.idx,
        )
        for r in self.state.racers:
            if r.idx == party_idx or r.finished:
                continue
            if r.position < party.position:
                dist = 1
            elif r.position > party.position:
                dist = -1
            else:
                continue
            move_evt = CmdMoveEvent(
                racer_idx=r.idx,
                distance=dist,
                is_main_move=False,
                source_racer_idx=party.idx,
                source_ability="PartyPull",
            )
            self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=party.idx)
        self.emit_ability_trigger(party.idx, "PartyPull")

    def on_ability_triggered(self, evt: AbilityTriggeredEvent) -> None:
        logger.info(
            "AbilityTriggeredEvent: ability %s by racer #%d",
            evt.ability_id,
            evt.source_racer_idx,
        )
        # Scoocher: move 1 whenever any ability is used
        for r in self.state.racers:
            if r.finished:
                continue
            if "ScoochStep" in r.abilities:
                logger.info(
                    "ScoochStep: Scoocher %s (#%d) moves 1 due to ability %s",
                    r.name,
                    r.idx,
                    evt.ability_id,
                )
                move_evt = CmdMoveEvent(
                    racer_idx=r.idx,
                    distance=1,
                    is_main_move=False,
                    source_racer_idx=r.idx,
                    source_ability="ScoochStep",
                )
                self.push_event(move_evt, phase=Phase.MOVE, reactor_idx=r.idx)


# ------------------------------
# Factory / setup
# ------------------------------


def build_engine(racers: Sequence[RacerName], seed: int = 0) -> GameEngine:
    state_racers: list[RacerState] = []
    for idx, name in enumerate(racers):
        abilities = set(RACER_ABILITIES.get(name, set()))
        state_racers.append(
            RacerState(
                idx=idx,
                name=name,
                position=0,
                tripped=False,
                finished=False,
                victory_points=0,
                abilities=abilities,
            )
        )
    state = GameState(racers=state_racers, current_racer_idx=0)
    rng = random.Random(seed)
    return GameEngine(state=state, rng=rng)


# ------------------------------
# Demo
# ------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Starting a race: just a list of racer names
    starting_racers: list[RacerName] = [
        "Centaur",
        "BigBaby",
        "Scoocher",
        "Banana",
        "Copycat",
        "Gunk",
        "PartyAnimal",
    ]

    engine = build_engine(starting_racers, seed=42)
    engine.run_race()

    logger.info(
        "Final positions: %s",
        [(r.idx, r.name, r.position) for r in engine.state.racers],
    )
    logger.info(
        "VP totals: %s",
        [(r.idx, r.name, r.victory_points) for r in engine.state.racers],
    )
