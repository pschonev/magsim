import heapq
import logging
import random
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Sequence, Type, Callable, Any

# ------------------------------
# 1. Logging
# ------------------------------


class GlobalLogState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalLogState, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.total_turn = 0
        self.turn_log_count = 0
        self.current_racer_repr = "_"

    def new_round(self):
        self.total_turn += 1

    def start_turn_log(self, racer_repr: str):
        self.turn_log_count = 0
        self.current_racer_repr = racer_repr

    def inc_log_count(self):
        self.turn_log_count += 1


log_context = GlobalLogState()


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.total_turn = log_context.total_turn
        record.turn_log_count = log_context.turn_log_count
        record.racer_repr = log_context.current_racer_repr
        log_context.inc_log_count()
        return True


class CustomFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = f"{record.total_turn}.{record.racer_repr}.{record.turn_log_count}"
        msg = record.getMessage()
        return f"{prefix} - {record.levelname} - {msg}"


logger = logging.getLogger("magical_athlete")
logger.setLevel(logging.INFO)  # Changed to INFO to reduce noise
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CustomFormatter())
handler.addFilter(ContextFilter())
logger.addHandler(handler)
logger.propagate = False

# ------------------------------
# 2. Config
# ------------------------------

RacerName = Literal[
    "Centaur", "HugeBaby", "Scoocher", "Banana", "Copycat", "Gunk", "PartyAnimal"
]
AbilityName = Literal[
    "Trample",
    "HugeBabyPush",
    "BananaTrip",
    "ScoochStep",
    "CopyLead",
    "Slime",
    "PartyPull",
    "PartyBoost",
]

TRIP_SPACES: set[int] = {4, 10, 18}
FINISH_SPACE: int = 20
WIN_VP: int = 4
SECOND_VP: int = 2

# ------------------------------
# 3. Game State
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

    @property
    def repr(self) -> str:
        return f"{self.idx}:{self.name}"


@dataclass(slots=True)
class GameState:
    racers: list[RacerState]
    current_racer_idx: int = 0
    finished_order: list[int] = field(default_factory=list)

    def get_state_hash(self) -> int:
        """Creates a hash of the physical board state (positions + status)."""
        # We exclude 'abilities' from hash to avoid recursion issues if abilities change
        data = tuple((r.position, r.tripped, r.finished) for r in self.racers)
        return hash(data)


# ------------------------------
# 4. Events & Scheduling
# ------------------------------


class GameEvent:
    pass


class Phase:
    SYSTEM = 0
    PRE_MAIN = 10
    REACTION = 15
    MAIN_ACT = 20
    MOVE_EXEC = 30
    BOARD = 40
    CLEANUP = 100


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollAndMainMoveEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class MoveCmdEvent(GameEvent):
    racer_idx: int
    distance: int
    is_main_move: bool
    source: str


@dataclass(frozen=True)
class WarpCmdEvent(GameEvent):
    racer_idx: int
    target_tile: int
    source: str


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    victim_idx: int
    tile_idx: int


@dataclass(frozen=True)
class LandingEvent(GameEvent):
    mover_idx: int
    tile_idx: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int
    ability_name: AbilityName


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_amount + sum(self.modifiers))


@dataclass(order=True)
class ScheduledEvent:
    phase: int
    priority: int
    serial: int
    event: GameEvent = field(compare=False)


# ------------------------------
# 5. Interfaces
# ------------------------------

AbilityCallback = Callable[[Any, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


class Ability(ABC):
    name: AbilityName
    triggers: tuple[Type[GameEvent], ...] = ()

    def register(self, engine: "GameEngine", owner_idx: int):
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        if engine.state.racers[owner_idx].finished:
            return
        self.execute(event, owner_idx, engine)

    @abstractmethod
    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        pass


class Modifier(ABC):
    name: AbilityName

    @abstractmethod
    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        pass


# ------------------------------
# 6. Abilities
# ------------------------------


class AbilityTrample(Ability):
    """Centaur: When I pass a racer, they move -2."""

    name = "Trample"
    triggers = (PassingEvent,)

    def execute(self, event: PassingEvent, owner_idx: int, engine: "GameEngine"):
        if event.mover_idx != owner_idx:
            return
        victim = engine.get_racer(event.victim_idx)
        if victim.finished:
            return

        logger.info(f"Trample: Centaur passed {victim.repr}. Victim moves -2.")
        engine.push_event(
            MoveCmdEvent(victim.idx, -2, False, "Trample"), phase=Phase.REACTION
        )
        engine.emit_ability_trigger(owner_idx, self.name)


class AbilityBananaTrip(Ability):
    """Banana: I trip any racer that passes me."""

    name = "BananaTrip"
    triggers = (PassingEvent,)

    def execute(self, event: PassingEvent, owner_idx: int, engine: "GameEngine"):
        if event.victim_idx != owner_idx:
            return
        mover = engine.get_racer(event.mover_idx)
        if mover.finished:
            return

        logger.info(f"BananaTrip: {mover.repr} passed Banana! Mover trips.")
        mover.tripped = True
        engine.emit_ability_trigger(owner_idx, self.name)


class AbilityHugeBabyPush(Ability):
    """Huge Baby: No one can ever be on my space... put them behind me."""

    name = "HugeBabyPush"
    triggers = (LandingEvent,)

    def execute(self, event: LandingEvent, owner_idx: int, engine: "GameEngine"):
        if event.mover_idx == owner_idx:
            return

        owner = engine.get_racer(owner_idx)
        victim = engine.get_racer(event.mover_idx)

        if victim.finished:
            return
        if owner.position != event.tile_idx:
            return

        target = max(0, owner.position - 1)
        logger.info(
            f"HugeBabyPush: {victim.repr} landed on HugeBaby. Warping to {target}."
        )

        engine.push_event(
            WarpCmdEvent(victim.idx, target, "HugeBabyPush"), phase=Phase.REACTION
        )
        engine.emit_ability_trigger(owner_idx, self.name)


class AbilityScoochStep(Ability):
    """Scoocher: When another racer's power happens, I move 1."""

    name = "ScoochStep"
    triggers = (AbilityTriggeredEvent,)

    def execute(
        self, event: AbilityTriggeredEvent, owner_idx: int, engine: "GameEngine"
    ):
        if event.source_racer_idx == owner_idx:
            return

        # Loop protection is handled by the Engine's history check,
        # but conceptually this ability is very prone to loops.
        engine.push_event(
            MoveCmdEvent(owner_idx, 1, False, "ScoochStep"), phase=Phase.REACTION
        )


class AbilityPartyPull(Ability):
    """Party Animal: Before main move, all racers move 1 space towards me."""

    name = "PartyPull"
    triggers = (TurnStartEvent,)

    def execute(self, event: TurnStartEvent, owner_idx: int, engine: "GameEngine"):
        if event.racer_idx != owner_idx:
            return

        party_animal = engine.get_racer(owner_idx)
        logger.info("PartyPull: Pulling everyone closer!")
        engine.emit_ability_trigger(owner_idx, self.name)

        for r in engine.state.racers:
            if r.idx == owner_idx or r.finished:
                continue
            direction = 0
            if r.position < party_animal.position:
                direction = 1
            elif r.position > party_animal.position:
                direction = -1

            if direction != 0:
                engine.push_event(
                    MoveCmdEvent(r.idx, direction, False, "PartyPull"),
                    phase=Phase.PRE_MAIN,
                )


class ModifierPartyBoost(Modifier):
    """Party Animal: +1 to main move per guest."""

    name = "PartyBoost"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx != owner_idx:
            return
        owner = engine.get_racer(owner_idx)
        guests = [
            r
            for r in engine.state.racers
            if r.idx != owner_idx and not r.finished and r.position == owner.position
        ]
        if guests:
            query.modifiers.append(len(guests))
            engine.emit_ability_trigger(owner_idx, self.name)


class ModifierSlime(Modifier):
    """Gunk: -1 to others' main move."""

    name = "Slime"

    def modify(self, query: MoveDistanceQuery, owner_idx: int, engine: "GameEngine"):
        if query.racer_idx == owner_idx:
            return
        query.modifiers.append(-1)
        engine.emit_ability_trigger(owner_idx, self.name)


class AbilityCopyLead(Ability):
    """Copycat: Copy the leader."""

    name = "CopyLead"
    triggers = (LandingEvent, TurnStartEvent)

    def execute(self, event: GameEvent, owner_idx: int, engine: "GameEngine"):
        me = engine.get_racer(owner_idx)
        if me.finished:
            return

        # Exclude finished racers from 'Lead' definition
        active = [
            r for r in engine.state.racers if not r.finished and r.idx != owner_idx
        ]
        if not active:
            return

        max_pos = max(r.position for r in active)
        leaders = [r for r in active if r.position == max_pos]
        leader = engine.rng.choice(leaders)

        current_abilities = me.abilities
        target_abilities = RACER_ABILITIES.get(leader.name, set()) | {self.name}

        if current_abilities != target_abilities:
            # Only log if it's a change to avoid log spam
            logger.info(f"Copycat: Now copying {leader.name}")
            engine.update_racer_abilities(owner_idx, target_abilities)


# ------------------------------
# 7. Registry
# ------------------------------

ABILITY_CLASSES = {
    "Trample": AbilityTrample,
    "HugeBabyPush": AbilityHugeBabyPush,
    "BananaTrip": AbilityBananaTrip,
    "ScoochStep": AbilityScoochStep,
    "PartyPull": AbilityPartyPull,
    "CopyLead": AbilityCopyLead,
}
MODIFIER_CLASSES = {
    "PartyBoost": ModifierPartyBoost,
    "Slime": ModifierSlime,
}
RACER_ABILITIES = {
    "Centaur": {"Trample"},
    "HugeBaby": {"HugeBabyPush"},
    "Scoocher": {"ScoochStep"},
    "Banana": {"BananaTrip"},
    "Copycat": {"CopyLead"},
    "Gunk": {"Slime"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
}

# ------------------------------
# 8. Engine
# ------------------------------


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    queue: list[ScheduledEvent] = field(default_factory=list)
    subscribers: dict[Type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    modifiers: list[tuple[Modifier, int]] = field(default_factory=list)

    _serial: int = 0
    race_over: bool = False

    # Loop detection history: Set of (StateHash, EventHash)
    history: set[tuple[int, int]] = field(default_factory=set)

    def subscribe(
        self, event_type: Type[GameEvent], callback: AbilityCallback, owner_idx: int
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def register_modifier(self, modifier: Modifier, owner_idx: int):
        self.modifiers.append((modifier, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        racer = self.get_racer(racer_idx)
        racer.abilities = new_abilities
        # Clean up and re-register
        for et in self.subscribers:
            self.subscribers[et] = [
                s for s in self.subscribers[et] if s.owner_idx != racer_idx
            ]
        self.modifiers = [m for m in self.modifiers if m[1] != racer_idx]
        for an in new_abilities:
            if an in ABILITY_CLASSES:
                ABILITY_CLASSES[an]().register(self, racer_idx)
            if an in MODIFIER_CLASSES:
                self.register_modifier(MODIFIER_CLASSES[an](), racer_idx)

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def push_event(self, event: GameEvent, *, phase: int):
        self._serial += 1
        sched = ScheduledEvent(phase, 0, self._serial, event)
        heapq.heappush(self.queue, sched)

    def emit_ability_trigger(self, source_idx: int, ability: AbilityName):
        self.push_event(
            AbilityTriggeredEvent(source_idx, ability), phase=Phase.REACTION
        )

    def publish_to_subscribers(self, event: GameEvent):
        if type(event) not in self.subscribers:
            return
        subs = self.subscribers[type(event)]
        current = self.state.current_racer_idx
        total = len(self.state.racers)
        # Active player -> Clockwise
        for sub in sorted(subs, key=lambda s: (s.owner_idx - current) % total):
            sub.callback(event, sub.owner_idx, self)

    # --- Core Loop ---

    def run_race(self):
        log_context.reset()
        while not self.race_over:
            self.run_turn()
            self.advance_turn()

    def run_turn(self):
        # Clear history at start of turn (loops are only relevant per-turn execution chain)
        self.history.clear()

        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        log_context.start_turn_log(racer.repr)

        logger.info(f"=== START TURN: {racer.repr} ===")

        if racer.tripped:
            logger.info(f"{racer.repr} is recovering from Trip.")
            racer.tripped = False
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
        else:
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
            self.push_event(RollAndMainMoveEvent(cr), phase=Phase.MAIN_ACT)

        while self.queue and not self.race_over:
            sched = heapq.heappop(self.queue)

            # --- LOOP DETECTION ---
            state_hash = self.state.get_state_hash()
            # Use repr(event) to distinguish between identical event types with different values
            event_sig = hash(repr(sched.event))
            history_key = (state_hash, event_sig)

            if history_key in self.history:
                logger.warning(
                    f"Loop detected for {sched.event}. Discarding to break cycle."
                )
                continue
            self.history.add(history_key)
            # ----------------------

            self.handle_event(sched.event)

    def handle_event(self, event: GameEvent):
        match event:
            case (
                TurnStartEvent()
                | PassingEvent()
                | LandingEvent()
                | AbilityTriggeredEvent()
            ):
                self.publish_to_subscribers(event)
            case RollAndMainMoveEvent():
                self._handle_main_roll(event)
            case MoveCmdEvent():
                self._handle_move(event)
            case WarpCmdEvent():
                self._handle_warp(event)

    def _handle_main_roll(self, event: RollAndMainMoveEvent):
        racer = self.get_racer(event.racer_idx)
        if racer.finished:
            return

        roll = self.rng.randint(1, 6)
        query = MoveDistanceQuery(event.racer_idx, roll)

        for mod, owner_idx in self.modifiers:
            if not self.get_racer(owner_idx).finished:
                mod.modify(query, owner_idx, self)

        final_dist = query.final_value
        logger.info(f"Roll: {roll} -> Final: {final_dist}")

        if final_dist != 0:
            self.push_event(
                MoveCmdEvent(event.racer_idx, final_dist, True, "MainMove"),
                phase=Phase.MOVE_EXEC,
            )

    def _check_finish(self, racer: RacerState) -> bool:
        if not racer.finished and racer.position > FINISH_SPACE:
            racer.finished = True
            self.state.finished_order.append(racer.idx)
            rank = len(self.state.finished_order)
            logger.info(f"!!! {racer.repr} FINISHED rank {rank} !!!")
            if rank == 1:
                racer.victory_points += WIN_VP
            if rank >= 2:
                racer.victory_points += SECOND_VP
                self.race_over = True
                self.queue.clear()  # Stop processing immediately
            return True
        return False

    def _handle_move(self, evt: MoveCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        start_pos = racer.position
        end_pos = start_pos + evt.distance

        logger.info(f"Move: {racer.repr} {start_pos}->{end_pos} ({evt.source})")

        # Trigger Passing (Simplified: if moving forward, trigger for all tiles strictly between)
        if evt.distance > 0:
            for tile in range(start_pos + 1, min(end_pos, FINISH_SPACE) + 1):
                victims = [
                    r
                    for r in self.state.racers
                    if r.position == tile and r.idx != racer.idx and not r.finished
                ]
                # Technically you only 'pass' if you end up ahead of them?
                # Rules: "Start behind and end ahead".
                # So if we land ON them (end_pos == tile), it's not a pass yet.
                # But Centaur tramples when passing.
                # We'll trigger for all tiles strictly < end_pos.
                if tile < end_pos:
                    for v in victims:
                        self.push_event(
                            PassingEvent(racer.idx, v.idx, tile), phase=Phase.MOVE_EXEC
                        )

        racer.position = end_pos

        # Check finish immediately
        if self._check_finish(racer):
            return

        self.push_event(LandingEvent(racer.idx, end_pos), phase=Phase.BOARD)

    def _handle_warp(self, evt: WarpCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        logger.info(f"Warp: {racer.repr} -> {evt.target_tile} ({evt.source})")
        racer.position = evt.target_tile

        if self._check_finish(racer):
            return

        self.push_event(LandingEvent(racer.idx, evt.target_tile), phase=Phase.BOARD)

    def advance_turn(self):
        if self.race_over:
            return
        n = len(self.state.racers)
        curr = self.state.current_racer_idx
        next_idx = (curr + 1) % n

        # Skip finished racers
        while self.state.racers[next_idx].finished:
            next_idx = (next_idx + 1) % n
            if next_idx == curr:
                break  # Should be caught by race_over check usually

        if next_idx < curr:
            log_context.new_round()
        self.state.current_racer_idx = next_idx


if __name__ == "__main__":
    # Full Roster Test
    roster = ["PartyAnimal", "Scoocher", "HugeBaby", "Centaur", "Copycat", "Gunk"]

    racers = [RacerState(i, name) for i, name in enumerate(roster)]
    eng = GameEngine(GameState(racers), random.Random(42))

    for r in racers:
        eng.update_racer_abilities(r.idx, set(RACER_ABILITIES[r.name]))

    eng.run_race()

    logger.info("Race Results:")
    for r in eng.state.racers:
        logger.info(
            f"{r.name}: Pos {r.position}, VP {r.victory_points}, Finished: {r.finished}"
        )
