"""Non-authoritative Jev shadow evaluator.

Jev never controls production in V1. It only records a typed opinion so we can
compare it with the existing Candidate/Narrowness gates before granting any
authority.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

JEV_SHADOW_ENABLED = os.getenv("JEV_SHADOW_ENABLED", "0") == "1"
JEV_API_KEY = os.getenv("JEV_API_KEY", "")
JEV_API_URL = os.getenv("JEV_API_URL", "https://api.typesafe.ai/v1/systemone")
JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")
JEV_TIMEOUT_SECONDS = float(os.getenv("JEV_TIMEOUT_SECONDS", "8"))
JEV_SHADOW_LOG = Path(os.getenv("JEV_SHADOW_LOG", "artifacts/diagnostics/jev_shadow.jsonl"))


def _append(event: dict[str, Any]) -> None:
    try:
        JEV_SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
        with JEV_SHADOW_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[JEV_SHADOW] log failure (ignored): {exc}")


def evaluate_candidate_shadow(candidate: dict[str, Any], existing_verdict: str, existing_reason: str = "") -> dict[str, Any]:
    """Return/log Jev's opinion without changing the caller's verdict."""
    if not JEV_SHADOW_ENABLED:
        return {"status": "DISABLED"}
    if not JEV_API_KEY:
        event = {"status": "SKIPPED", "reason": "JEV_API_KEY unavailable", "existing_verdict": existing_verdict}
        _append(event)
        return event

    state = {
        "candidate": {
            "topic": candidate.get("topic"),
            "core_question": candidate.get("core_question"),
            "reveal": candidate.get("reveal"),
            "mechanism": candidate.get("mechanism"),
            "fact_check_focus": candidate.get("fact_check_focus"),
            "visual_proof": candidate.get("visual_proof"),
        },
        "existing_gate": {"verdict": existing_verdict, "reason": existing_reason},
        "constraints": [
            "Do not invent facts, numbers, causes, or mechanisms.",
            "A strong Shorts candidate needs one concrete question, one specific reveal, and a visually provable payoff.",
            "This is shadow evaluation only; the answer must not authorize production behavior.",
        ],
    }
    questions = {
        "route": {
            "type": "choice",
            "instructions": "Choose the best routing signal for this candidate.",
            "criteria": {
                "PASS": "Specific, grounded, and usable as-is.",
                "REWRITE": "Same subject is promising but the question/reveal should be narrowed or clarified.",
                "ESCALATE": "Evidence is insufficient or ambiguous enough that a stronger reasoning/fact-check step is warranted.",
                "FAIL": "The candidate is fundamentally unsuitable rather than repairable by a bounded rewrite.",
            },
        },
        "specificity": {
            "type": "score",
            "instructions": "Rate how concrete and narrowly answerable the candidate is.",
            "criteria": ["Very broad", "Broad", "Usable", "Specific", "Highly specific"],
        },
        "grounded": {
            "type": "noul",
            "instructions": "Is the candidate grounded in the supplied evidence without needing invented facts?",
        },
    }

    try:
        # Keep the optional shadow observer import-safe in focused regression
        # jobs that intentionally do not install runtime HTTP dependencies.
        import requests
        response = requests.post(
            JEV_API_URL,
            headers={"Authorization": f"Bearer {JEV_API_KEY}", "Content-Type": "application/json"},
            json={"model": JEV_MODEL, "state": state, "questions": questions},
            timeout=JEV_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        event = {
            "status": "OK",
            "existing_verdict": existing_verdict,
            "existing_reason": existing_reason,
            "jev": response.json(),
        }
    except Exception as exc:
        event = {
            "status": "ERROR",
            "existing_verdict": existing_verdict,
            "error": f"{type(exc).__name__}: {exc}",
        }

    _append(event)
    print(f"[JEV_SHADOW] {event['status']} existing={existing_verdict}")
    return event
