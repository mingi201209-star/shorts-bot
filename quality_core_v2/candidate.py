"""CandidateV2 gate: deterministic, provider-free checks only.

This is NOT the Explorer (no LLM call here). It is the same role
content/candidate_gate.py plays for V1: an independent, cheap, deterministic
check applied to a Candidate before it is allowed further downstream.

Real generation/bounded-rewrite (max 1 retry, per the execution order) is a
separate concern that calls an LLM adapter; that adapter is intentionally
NOT part of this module so this file stays replay-safe (zero network calls).
"""

from __future__ import annotations

import re
from typing import List, Tuple

from quality_core_v2.schemas import CandidateV2, Verdict

MAX_CANDIDATE_REWRITES = 1

# Reveal endings that are conclusions, not mechanisms. A Reveal ending in one
# of these (after stripping trailing particles) is rejected regardless of
# what precedes it -- this is the exact list of vague-benefit language named
# in the execution order.
_VAGUE_REVEAL_PATTERNS = [
    r"효율\s*(?:을|를)?\s*(?:높이|향상|개선)",
    r"안전성?\s*(?:을|를)?\s*(?:높이|향상|강화)",
    r"최적화(?:합니다|된다|시킵니다|하기 위해서?입니다)?",
    r"도움이?\s*됩니다",
    r"영향을?\s*줍니다",
    r"efficiency",
    r"safety",
    r"optimi[sz]",
]
_VAGUE_REVEAL_RE = re.compile("|".join(_VAGUE_REVEAL_PATTERNS), re.IGNORECASE)


def _has_content(*values: str) -> bool:
    return all(bool((v or "").strip()) for v in values)


def evaluate_candidate_v2(candidate: CandidateV2) -> Verdict:
    """PASS/REGENERATE a Candidate on the four required properties:

    1. concrete physical subject   (concrete_subject non-empty and specific)
    2. observable phenomenon       (observable_phenomenon non-empty)
    3. concrete question           (core_question non-empty, not vague)
    4. non-trivial mechanism/reveal (reveal not a vague-benefit ending)

    No bypass: this function returns REGENERATE-equivalent (passed=False)
    for any violation, and there is no path back to PASS inside this
    function itself (bounded rewrite, if any, is the caller's job and must
    re-submit a new candidate to this same function).
    """
    if not _has_content(
        candidate.concrete_subject,
        candidate.observable_phenomenon,
        candidate.core_question,
        candidate.mechanism,
        candidate.reveal,
    ):
        return Verdict(False, "missing one or more required Candidate fields", "candidate")

    if _VAGUE_REVEAL_RE.search(candidate.reveal):
        return Verdict(
            False,
            f"Reveal ends in vague-benefit language, not a mechanism: {candidate.reveal!r}",
            "candidate",
        )

    if not candidate.canonical_subject.strip():
        return Verdict(False, "canonical_subject is unresolved", "candidate")

    return Verdict(True, "concrete subject + observable phenomenon + narrow mechanism/reveal", "candidate")
