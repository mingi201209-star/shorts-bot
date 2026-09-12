from pathlib import Path


path = Path("main.py")
text = path.read_text(encoding="utf-8")

needle = '''        pool[\n            judge_type\n        ] = [\n            result\n        ]\n\n    return pool\n'''

replacement = '''        pool[\n            judge_type\n        ] = [\n            result\n        ]\n\n        # Hard novelty failure means the candidate itself is weak.\n        # Stop before FACT/VISUAL judges and before any rewrite/review.\n        if judge_type == "novelty":\n\n            try:\n                novelty_score = float(\n                    result.get(\n                        "score",\n                        0.0,\n                    )\n                )\n            except Exception:\n                novelty_score = 10.0\n\n            if (\n                novelty_score\n                < NOVELTY_HARD_REGENERATE_SCORE\n            ):\n\n                print("")\n                print(\n                    "⏭️ Novelty 조기 차단: "\n                    f"{novelty_score:.2f} < "\n                    f"{NOVELTY_HARD_REGENERATE_SCORE:.2f}"\n                )\n                print(\n                    "   FACT/VISUAL Judge를 생략하고 "\n                    "Candidate Explorer로 반환합니다."\n                )\n\n                break\n\n    return pool\n'''

if replacement in text:
    print("early novelty hotfix already applied")
elif needle not in text:
    raise RuntimeError("run_initial_judges patch target not found")
else:
    path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    print("early novelty hotfix applied")


# Production counterexample: run 32538176597 selected a candidate that was
# specific enough for Candidate Gate but predictably scored Novelty 5/10 before
# and after rewrite. Align the pre-script gate with the downstream novelty
# contract without changing any judge threshold.
gate_path = Path("content/candidate_gate.py")
gate_text = gate_path.read_text(encoding="utf-8")

core_marker = '''"질문과 실제 답이 얼마나 예상 밖인가"\n\n이다.\n'''
core_insert = '''"질문과 실제 답이 얼마나 예상 밖인가"\n\n이다.\n\n이 Gate는 후단 Novelty Judge와 같은 방향으로 판단해야 한다.\n구체적인 사실이나 메커니즘이 있다는 이유만으로 PASS하지 마라.\n질문을 읽은 일반 시청자가 Reveal의 방향을 쉽게 예상할 수 있고,\nScript 표현을 바꾸는 것만으로 새로움이 생기지 않는다면 REGENERATE한다.\n'''

payoff_marker = '''라는 새로운 이해나 재해석이\n거의 생기지 않는다면 약하다.\n'''
payoff_insert = '''라는 새로운 이해나 재해석이\n거의 생기지 않는다면 약하다.\n\n특히 질문 자체가 답의 방향을 거의 말해주거나,\nReveal이 상식적인 물리 현상·일상적 인과를 단순 확인하는 수준이면\n구체적인 용어가 있어도 REGENERATE한다.\n\n예: "비행 중 기내에서 중력이 느껴지는 방식이 어떻게 다른가"처럼\n익숙한 현상의 단순 변화만 묻고 Reveal도 예상 가능한 변화 설명에 머문다면\n후단 Rewrite로 해결할 문제가 아니라 Candidate 자체가 약한 것이다.\n\n반대로 익숙한 비행기 소재라도 예상과 반대되는 원인, 숨은 설계 제약,\n구체적인 메커니즘으로 기존 직관을 바꾸는 Reveal이 있으면 PASS할 수 있다.\n'''

ambiguity_marker = '''판단이 애매하다면\nPASS 쪽으로 판단한다.\n'''
ambiguity_insert = '''단, "구체적이지만 예상 가능한 Candidate"는 애매한 PASS로 처리하지 마라.\n이 경우 후단 Novelty Rewrite가 Candidate 선택 문제를 고칠 수 없으므로\nREGENERATE 쪽으로 판단한다.\n\n그 외의 판단이 애매하다면\nPASS 쪽으로 판단한다.\n'''

if "CANDIDATE_NOVELTY_PARITY_V1" in gate_text:
    print("candidate novelty parity already applied")
else:
    for marker, patched in (
        (core_marker, core_insert + "\nCANDIDATE_NOVELTY_PARITY_V1\n"),
        (payoff_marker, payoff_insert),
        (ambiguity_marker, ambiguity_insert),
    ):
        if marker not in gate_text:
            raise RuntimeError("candidate novelty parity patch target not found")
        gate_text = gate_text.replace(marker, patched, 1)

    gate_path.write_text(gate_text, encoding="utf-8")
    print("candidate novelty parity hotfix applied")


# Run 34705737709 spent one GPT-5.6 Sol Writer on a rounded-window Candidate
# that the unchanged downstream Novelty Judge scored 4/10, then spent a second
# Sol Writer when the same trusted physical subject returned under a different
# topic label. With the production $0.05 ceiling, that second Writer alone pushed
# the run to $0.055195 before the next Judge could start.
#
# Move the existing novelty authority in front of the expensive Writer only for
# automatic aviation Winners. This adds one bounded gpt-4o-mini Judge call after
# Candidate Gate PASS, but synthesizes no fact, changes no threshold, and does
# not add a Writer/rewrite/retry. A low-novelty trusted physical identity is also
# remembered for this Python process so a renamed version cannot spend another
# Candidate Gate / novelty / Writer path in the same run.
PREWRITE_MARKER = "# RUN_34705737709_PREWRITER_NOVELTY_V1"
PREWRITE_PATCH = r'''

# RUN_34705737709_PREWRITER_NOVELTY_V1
# Authority: Production Run 34705737709. The downstream Novelty minimum remains
# 5.0; this layer merely evaluates that same editorial property before the costly
# Writer in automatic aviation mode. Fixed-topic behavior is untouched.
_PREWRITER_NOVELTY_MIN_SCORE = 5.0
_PREWRITER_NOVELTY_REJECTED_CANONICALS = set()
_PREWRITER_UNKNOWN_CANONICALS = {"", "unknown", "not_applicable", "not applicable"}
_original_evaluate_candidate_before_prewriter_novelty = evaluate_candidate


def _prewriter_normalize_identity(value):
    return " ".join(str(value or "").strip().lower().split())


def _prewriter_automatic_aviation_enabled(role):
    return (
        str(role or "").strip().lower() == "winner"
        and not str(os.environ.get("SHORTS_TOPIC", "")).strip()
        and str(os.environ.get("SHORTS_CANDIDATE_SCOPE", "")).strip().lower()
        == "aviation"
    )


def _prewriter_trusted_canonical_family(candidate):
    if not isinstance(candidate, dict):
        return ""
    if str(candidate.get("subject_kind") or "").strip().lower() != "physical_entity":
        return ""

    canonical = _prewriter_normalize_identity(candidate.get("canonical_subject"))
    if canonical in _PREWRITER_UNKNOWN_CANONICALS:
        return ""

    evidence = candidate.get("_trusted_grounding_evidence")
    if not isinstance(evidence, list):
        return ""
    for item in evidence:
        if not isinstance(item, dict):
            continue
        supported = _prewriter_normalize_identity(item.get("supports_subject"))
        source = str(item.get("source") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if supported == canonical and source and detail:
            return canonical
    return ""


def _prewriter_novelty_probe(candidate):
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    beats = (
        ("hook", micro.get("hook")),
        ("core_question", micro.get("core_question") or candidate.get("core_question")),
        ("reveal", micro.get("reveal")),
        ("payoff", micro.get("payoff")),
    )
    scenes = []
    for purpose, text in beats:
        value = str(text or "").strip()
        if value:
            scenes.append({
                "text": value,
                "semantic_purpose": purpose,
            })

    return {
        "title": str(candidate.get("topic") or "").strip(),
        "topic": str(candidate.get("topic") or "").strip(),
        "scenes": scenes,
    }


def _run_prewriter_novelty(candidate):
    # Import at call time so any later production Judge wrappers remain
    # authoritative. Novelty does not use the FACT-only identity precheck.
    from quality.judge import run_judge, print_judge_result

    result = run_judge(
        "novelty",
        _prewriter_novelty_probe(candidate),
        model=os.environ.get("V3_JUDGE_MODEL", "gpt-4o-mini"),
    )
    print("")
    print("🧪 PRE-WRITER NOVELTY PREFLIGHT")
    print_judge_result(result)
    return result


def evaluate_candidate(candidate, *, model=MODEL, role="Winner"):
    enabled = _prewriter_automatic_aviation_enabled(role)
    canonical_family = (
        _prewriter_trusted_canonical_family(candidate)
        if enabled
        else ""
    )

    if (
        canonical_family
        and canonical_family in _PREWRITER_NOVELTY_REJECTED_CANONICALS
    ):
        print("")
        print(
            "🚫 PRE-WRITER NOVELTY FAMILY MEMORY: "
            f"{canonical_family}"
        )
        return {
            "status": "REGENERATE",
            "failure_type": "PREWRITER_NOVELTY_FAMILY_REPEAT",
            "reason": (
                "이번 실행에서 Novelty 최소 기준 미달로 폐기한 동일한 "
                "trusted canonical subject가 다른 표현으로 다시 선택되었습니다."
            ),
        }

    editorial = _original_evaluate_candidate_before_prewriter_novelty(
        candidate,
        model=model,
        role=role,
    )
    if not enabled or editorial.get("status") != "PASS":
        return editorial

    novelty = _run_prewriter_novelty(candidate)
    try:
        novelty_score = float(novelty.get("score", 0.0))
    except (TypeError, ValueError):
        novelty_score = 0.0

    if novelty_score < _PREWRITER_NOVELTY_MIN_SCORE:
        if canonical_family:
            _PREWRITER_NOVELTY_REJECTED_CANONICALS.add(canonical_family)
        print(
            "🚫 PRE-WRITER NOVELTY BLOCK: "
            f"{novelty_score:.2f} < {_PREWRITER_NOVELTY_MIN_SCORE:.2f}"
        )
        return {
            "status": "REGENERATE",
            "failure_type": "PREWRITER_NOVELTY_LOW",
            "reason": (
                "Writer 실행 전 Novelty Judge가 기존 최소 기준 미달을 확인했습니다: "
                f"{novelty_score:.2f} < {_PREWRITER_NOVELTY_MIN_SCORE:.2f}. "
                "비싼 Writer를 사용하지 않고 새 Candidate를 탐색합니다."
            ),
        }

    print(
        "✅ PRE-WRITER NOVELTY PASS: "
        f"{novelty_score:.2f} >= {_PREWRITER_NOVELTY_MIN_SCORE:.2f}"
    )
    return editorial
'''


gate_text = gate_path.read_text(encoding="utf-8")
if PREWRITE_MARKER in gate_text:
    print("pre-Writer novelty preflight already applied")
else:
    gate_path.write_text(
        gate_text.rstrip() + PREWRITE_PATCH + "\n",
        encoding="utf-8",
    )
    print(
        "pre-Writer novelty preflight applied; "
        "Writer/rewrite/retry/quality/cost ceilings unchanged"
    )
