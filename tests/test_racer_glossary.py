"""The glossary's decision flag matches the racers' own ability classes."""

import json
from pathlib import Path

from magsim.analysis.filters import racers_with_decisions
from magsim.core.agent import BooleanDecisionMixin, SelectionDecisionMixin
from magsim.core.registry import RACER_ABILITIES
from magsim.racers import get_ability_classes

GLOSSARY = Path(__file__).resolve().parent.parent / "web" / "src" / "utils" / "racerGlossary.ts"
DECISION_MIXINS = (BooleanDecisionMixin, SelectionDecisionMixin)


def own_decision_racers() -> set[str]:
    classes = get_ability_classes()
    return {
        racer
        for racer, ability_names in RACER_ABILITIES.items()
        if any(name in classes and issubclass(classes[name], DECISION_MIXINS) for name in ability_names)
    }


def glossary_entries() -> list[dict[str, str | bool | None]]:
    lines = [line.strip().rstrip(",") for line in GLOSSARY.read_text().splitlines()]
    return [json.loads(line) for line in lines if line.startswith('{"key"')]


def test_decision_racers_are_those_whose_own_abilities_use_a_decision_mixin() -> None:
    decision = set(racers_with_decisions())
    assert decision == own_decision_racers()
    assert decision <= set(RACER_ABILITIES)
    assert "Dicemonger" not in decision
    assert "Copycat" in decision


def test_glossary_file_flags_match_the_registry() -> None:
    entries = glossary_entries()
    flagged = {e["key"] for e in entries if e["decision"]}
    assert flagged == set(racers_with_decisions())
    assert all("flavor" not in e for e in entries)
    unsimulated = {e["key"] for e in entries if not e["implemented"]}
    assert unsimulated.isdisjoint(flagged)
