from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectStateSpec:
    canonical_states: frozenset[str]
    claim_aliases: dict[str, str]
    vision_aliases: dict[str, str]


class SubjectStateRegistry:
    def __init__(self, specs: dict[str, SubjectStateSpec] | None = None) -> None:
        self._specs = specs if specs is not None else dict(_DEFAULT_SPECS)

    def is_valid(self, subject: str, state: str) -> bool:
        spec = self._specs.get(subject)
        return bool(spec and state in spec.canonical_states)

    def canonicalize_for_repair(self, subject: str, state: str) -> str | None:
        spec = self._specs.get(subject)
        if spec is None:
            return None
        if state in spec.canonical_states:
            return state
        return spec.claim_aliases.get(state)

    def canonicalize_for_evidence(self, subject: str, raw_state: str) -> str | None:
        spec = self._specs.get(subject)
        if spec is None:
            return None
        if raw_state in spec.canonical_states:
            return raw_state
        return spec.vision_aliases.get(raw_state)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._specs)


_DEFAULT_SPECS: dict[str, SubjectStateSpec] = {
    "flap": SubjectStateSpec(
        canonical_states=frozenset({"DEPLOYED", "RETRACTED", "PARTIALLY_DEPLOYED"}),
        claim_aliases={
            "OPEN": "DEPLOYED",
            "EXTENDED": "DEPLOYED",
            "DOWN": "DEPLOYED",
            "CLOSED": "RETRACTED",
            "UP": "RETRACTED",
            "PARTIAL": "PARTIALLY_DEPLOYED",
        },
        vision_aliases={
            "EXTENDED": "DEPLOYED",
            "DOWN": "DEPLOYED",
            "UP": "RETRACTED",
        },
    ),
    "landing_gear": SubjectStateSpec(
        canonical_states=frozenset({"EXTENDED", "RETRACTED"}),
        claim_aliases={"DOWN": "EXTENDED", "DEPLOYED": "EXTENDED", "UP": "RETRACTED"},
        vision_aliases={"DOWN": "EXTENDED", "UP": "RETRACTED"},
    ),
    "door": SubjectStateSpec(
        canonical_states=frozenset({"OPEN", "CLOSED"}),
        claim_aliases={},
        vision_aliases={},
    ),
    "window_corner": SubjectStateSpec(
        canonical_states=frozenset({"SQUARISH", "ROUNDED"}),
        claim_aliases={},
        vision_aliases={},
    ),
}
