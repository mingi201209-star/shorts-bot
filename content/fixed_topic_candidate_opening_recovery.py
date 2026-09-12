from __future__ import annotations

from copy import deepcopy
from typing import Callable, Mapping, MutableMapping, Tuple


QUESTION_ENDINGS = ("?", "？", "까요", "나요", "일까", "걸까")


def _text(value) -> str:
    return str(value or "").strip()


def _is_question_like(value: str) -> bool:
    text = _text(value)
    if not text:
        return False
    return text.endswith(QUESTION_ENDINGS) or text.startswith(("왜 ", "어째서 ", "어떻게 "))


def recover_fixed_topic_candidate_hook(
    candidate_result: Mapping,
    *,
    fixed_topic: str,
    prefix: str,
    restates_question: Callable[[str, str], bool],
    opening_violation_reason: Callable[[str, str], str],
) -> Tuple[dict, bool, str]:
    """Repair only a fixed-topic Winner whose Hook repeats its Core Question.

    The replacement is selected exclusively from the already-generated
    Candidate's own payoff/reveal.  No text is invented and no model/network
    call is made.  Every projected Hook must pass both the existing Candidate
    Hook->Question restatement guard and the final Script opening-human
    contract.  If no candidate-owned sentence satisfies both authorities the
    original Candidate is returned unchanged so the existing validator fails
    closed.
    """

    original = deepcopy(dict(candidate_result or {}))
    fixed = _text(fixed_topic)
    if not fixed or prefix != "winner":
        return original, False, "not_fixed_topic_winner"

    micro = original.get("micro_narrative")
    if not isinstance(micro, MutableMapping):
        return original, False, "missing_micro_narrative"

    hook = _text(micro.get("hook"))
    top_question = _text(original.get("core_question"))
    micro_question = _text(micro.get("core_question"))
    questions = [question for question in (top_question, micro_question) if question]
    if not hook or not questions:
        return original, False, "missing_hook_or_question"

    if not any(restates_question(hook, question) for question in questions):
        return original, False, "hook_already_progresses"

    # Prefer the Candidate-owned payoff: a concrete consequence/result is the
    # desired 0-2s opening shape and lets Scene 2 ask why.  Reveal is a bounded
    # fallback when payoff itself is unusable.  Later FACT/Script/Visual gates
    # remain authoritative over either sentence.
    proposals = (
        ("payoff", _text(micro.get("payoff"))),
        ("reveal", _text(micro.get("reveal"))),
    )

    authoritative_question = top_question or micro_question
    for source, proposal in proposals:
        if not proposal or proposal == hook or _is_question_like(proposal):
            continue
        if any(restates_question(proposal, question) for question in questions):
            continue
        if _text(opening_violation_reason(proposal, authoritative_question)):
            continue

        recovered = deepcopy(original)
        recovered_micro = dict(recovered.get("micro_narrative") or {})
        recovered_micro["hook"] = proposal
        recovered["micro_narrative"] = recovered_micro
        return recovered, True, source

    return original, False, "no_safe_candidate_owned_progression"
