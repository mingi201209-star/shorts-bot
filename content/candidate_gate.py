# content/candidate_gate.py

import json
import os

import openai

from config import OPENAI_KEY

from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


MODEL = os.environ.get(
    "V3_CANDIDATE_GATE_MODEL",
    "gpt-4o-mini",
)


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


# ============================================================
# V3.2.1.2 Candidate Gate
# ============================================================
#
# Candidate Explorer가 고른 Winner를
# Script 생성 전에 독립적으로 한 번 더 검사한다.
#
#
# 목적:
#
# - 너무 넓은 주제 차단
# - 뻔한 Core Question 차단
# - Generic Reveal 차단
# - 약한 Payoff 차단
#
#
# 하지 않는 것:
#
# - 새로운 Candidate 생성
# - Script 작성
# - 숫자 점수
# - Fact 검증 완료 선언
#
#
# 익숙한 대상 자체는 허용한다.
#
# Familiar Subject
# + Unexpected Answer
#
# 는 좋은 Candidate가 될 수 있다.
#
# ============================================================


GATE_SYSTEM_PROMPT = """
너는 YouTube Shorts Candidate Explorer의
독립적인 최종 Candidate Reviewer다.

Candidate Explorer가 이미 선택한
Candidate 하나만 검사한다.

새 Candidate를 만들지 마라.

대본도 쓰지 마라.

숫자 점수도 사용하지 마라.


============================================================
CORE PRINCIPLE
============================================================

Recognizable enough to care.
Surprising enough to stay.
Grounded enough to verify.


익숙한 대상이라는 이유로
탈락시키지 마라.

중요한 것은

"대상이 얼마나 희귀한가"

가 아니라

"질문과 실제 답이 얼마나 예상 밖인가"

이다.


============================================================
REGENERATE CONDITIONS
============================================================

아래 문제 중 하나가
명확하게 존재하면

REGENERATE를 반환한다.


------------------------------------------------------------
1. BROAD / GENERIC QUESTION
------------------------------------------------------------

Core Question이

- X가 Y에 어떤 영향을 주는가?
- X와 Y는 어떤 관계인가?
- X가 왜 중요한가?
- X가 미래를 어떻게 바꿀까?
- X의 장점과 단점은 무엇인가?
- 왜 우리는 특정한 일반 행동을 하는가?
- 왜 우리는 특정한 일상 습관을 형성하는가?

처럼 지나치게 넓은가?


질문만 읽었을 때

하나의 구체적인 Reveal을
예상할 수 없다면 약한 Candidate다.


------------------------------------------------------------
2. GENERIC REVEAL
------------------------------------------------------------

Reveal이

- 영향을 준다
- 중요하다
- 도움이 된다
- 여러 요인이 작용한다
- 뇌가 영향을 준다
- 환경이 영향을 준다
- 사회가 영향을 준다
- 미래에 중요해질 수 있다

같은 일반론으로 끝나는가?


강한 Reveal에는 보통

- 구체적인 Mechanism
- 구조
- 제약
- 사건
- 원인
- 예상 밖의 연결

중 적어도 하나가 존재해야 한다.


------------------------------------------------------------
3. PREDICTABLE PAYOFF
------------------------------------------------------------

질문을 읽는 순간
대부분의 시청자가 결론을 쉽게 예상할 수 있는가?


영상을 끝까지 본 뒤에도

"아, 그래서 그런 거였구나"

라는 새로운 이해나 재해석이
거의 생기지 않는다면 약하다.


------------------------------------------------------------
4. MANUFACTURED INTEREST
------------------------------------------------------------

주제 자체보다

- 충격
- 비밀
- 숨겨진 이유
- 아무도 모르는
- 놀라운 진실

같은 표현을 붙여야만
흥미롭게 느껴지는가?


그렇다면 Candidate 자체가 약하다.


------------------------------------------------------------
5. SCOPE COLLAPSE
------------------------------------------------------------

하나의 Shorts에서 정확하게 설명하려면

수많은 원인,
예외,
역사적 배경,
복잡한 선행 개념

이 필요한가?


하나의 중심 인과관계로
목표 시간 안에 설명하기 어렵다면 약하다.


============================================================
PASS CONDITIONS
============================================================

다음 조건이면 PASS할 수 있다.


- 대상이 익숙해도 질문은 구체적이다.

- 하나의 실제 Mechanism,
  구조,
  제약,
  사건,
  원인,
  예상 밖 연결이 존재한다.

- Reveal이 Core Question에
  직접적인 답을 준다.

- Payoff가 Hook보다 약하지 않다.

- 시청자가 영상을 보기 전에는
  쉽게 예상하지 못했을
  구체적인 이해를 제공한다.

- 목표 시간 안에
  한 줄기의 설명으로 전달 가능하다.


============================================================
IMPORTANT
============================================================

이 Gate는
완벽한 Candidate만 통과시키는 시스템이 아니다.

명백히 제작 가치가 약한 Candidate만
차단한다.

판단이 애매하다면
PASS 쪽으로 판단한다.


============================================================
OUTPUT
============================================================

반드시 JSON 객체 하나만 출력한다.

Markdown 금지.
설명문 금지.
숫자 점수 금지.


PASS:

{
  "status": "PASS",
  "reason": "짧고 구체적인 이유"
}


실패:

{
  "status": "REGENERATE",
  "reason": "Candidate 자체가 왜 약한지 짧고 구체적인 이유"
}
"""


# ============================================================
# Candidate Validation
# ============================================================

def require_candidate(candidate):

    if not isinstance(
        candidate,
        dict,
    ):

        raise TypeError(
            "candidate는 dict여야 합니다."
        )

    required = (
        "topic",
        "angle",
        "core_question",
        "micro_narrative",
    )

    for field in required:

        if field not in candidate:

            raise ValueError(
                "Candidate Gate 필드 누락: "
                f"{field}"
            )

    micro = candidate.get(
        "micro_narrative"
    )

    if not isinstance(
        micro,
        dict,
    ):

        raise ValueError(
            "candidate.micro_narrative는 "
            "dict여야 합니다."
        )

    payload = {
        "topic":
            str(
                candidate.get(
                    "topic",
                    "",
                )
            ).strip(),

        "angle":
            str(
                candidate.get(
                    "angle",
                    "",
                )
            ).strip(),

        "core_question":
            str(
                candidate.get(
                    "core_question",
                    "",
                )
            ).strip(),

        "micro_narrative": {
            "hook":
                str(
                    micro.get(
                        "hook",
                        "",
                    )
                ).strip(),

            "core_question":
                str(
                    micro.get(
                        "core_question",
                        "",
                    )
                ).strip(),

            "reveal":
                str(
                    micro.get(
                        "reveal",
                        "",
                    )
                ).strip(),

            "payoff":
                str(
                    micro.get(
                        "payoff",
                        "",
                    )
                ).strip(),
        },
    }

    if not payload["topic"]:

        raise ValueError(
            "Candidate Gate topic이 비어 있습니다."
        )

    if not payload["angle"]:

        raise ValueError(
            "Candidate Gate angle이 비어 있습니다."
        )

    if not payload[
        "core_question"
    ]:

        raise ValueError(
            "Candidate Gate core_question이 "
            "비어 있습니다."
        )

    for field, value in (
        payload[
            "micro_narrative"
        ].items()
    ):

        if not value:

            raise ValueError(
                "Candidate Gate "
                "micro_narrative."
                f"{field}가 비어 있습니다."
            )

    return payload


# ============================================================
# Gate Output Validation
# ============================================================

def validate_gate_output(data):

    if not isinstance(
        data,
        dict,
    ):

        raise ValueError(
            "Candidate Gate 응답은 "
            "JSON 객체여야 합니다."
        )

    status = str(
        data.get(
            "status",
            "",
        )
    ).strip().upper()

    reason = str(
        data.get(
            "reason",
            "",
        )
    ).strip()

    if status not in (
        "PASS",
        "REGENERATE",
    ):

        raise ValueError(
            "Candidate Gate status는 "
            "PASS 또는 REGENERATE여야 합니다. "
            f"현재 값: {status}"
        )

    if not reason:

        raise ValueError(
            "Candidate Gate reason이 "
            "비어 있습니다."
        )

    return {
        "status":
            status,

        "reason":
            reason,
    }


# ============================================================
# Candidate Gate
# ============================================================

def _evaluate_candidate_once(
    candidate,
    *,
    model=MODEL,
    role="Winner",
):

    payload = (
        require_candidate(
            candidate
        )
    )

    print("")
    print("=" * 64)

    print(
        "🚪 V3.2.1.2 CANDIDATE GATE"
    )

    print("=" * 64)

    print(
        "대상:",
        role,
    )

    print(
        "Topic:",
        payload["topic"],
    )

    print(
        "Question:",
        payload[
            "core_question"
        ],
    )

    call_number = (
        authorize_call(
            model
        )
    )

    print(
        "💳 Candidate Gate API call "
        f"authorized: #{call_number}"
    )

    response = (
        openai
        .chat
        .completions
        .create(
            model=model,

            messages=[
                {
                    "role":
                        "system",

                    "content":
                        GATE_SYSTEM_PROMPT,
                },

                {
                    "role":
                        "user",

                    "content": (
                        "아래 Candidate를 "
                        "독립적으로 최종 검사하라.\n\n"
                        + json.dumps(
                            payload,
                            ensure_ascii=False,
                            indent=2,
                        )
                    ),
                },
            ],

            temperature=0.0,

            response_format={
                "type":
                    "json_object",
            },
        )
    )

    usage = (
        record_usage(
            model,
            response,
        )
    )

    print(
        "💰 Candidate Gate call:"
        f" ${usage['cost_usd']:.6f}"
    )

    print_budget_status()

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:

        raise RuntimeError(
            "Candidate Gate 응답이 "
            "비어 있습니다."
        )

    try:

        parsed = (
            json.loads(
                content
            )
        )

    except Exception as exc:

        raise ValueError(
            "Candidate Gate JSON 파싱 실패"
        ) from exc

    result = (
        validate_gate_output(
            parsed
        )
    )

    print("")

    print(
        "🚪 Gate 결과:",
        result["status"],
    )

    print(
        "이유:",
        result["reason"],
    )

    print("=" * 64)

    return result


# ============================================================
# CANDIDATE_GATE_BOUNDED_RECOVERY_V1
# ============================================================
#
# Production runs 618/619 showed the same failure mode Narrowness
# self-critique had before its own bounded recovery: Candidate Gate
# correctly identified a genuinely broad/generic candidate (run 619's
# "광활한 사막에 위치한 마을의 수원지" -- "질문이 지나치게 넓고 일반적이며,
# Reveal이 구체적인 메커니즘이나 예상 밖의 연결을 제공하지 않음"), but the
# only reaction the caller (main.py's Candidate Loop) had was to discard
# the whole subject and spend a fresh Candidate Explorer attempt on an
# unrelated topic. This does NOT change the Gate's own PASS/REGENERATE
# logic or threshold in any way -- a recovered candidate goes back
# through the exact same, unmodified ``_evaluate_candidate_once`` a
# normal candidate would. It only gives a rejected candidate a small,
# bounded number of chances to become narrower/more specific on the
# SAME subject before the caller gives up on it and moves to a new
# direction, same as before.
#
# A rewrite could plausibly reintroduce the kind of broadness the
# Narrowness self-critique gate (content/candidate_explorer.py) already
# guards against, so a rewritten candidate is also re-checked there
# before being re-submitted to this same Gate -- a recovered candidate
# is validated exactly as rigorously as a freshly generated one.
MAX_CANDIDATE_GATE_REWRITES = 2


_CANDIDATE_GATE_REWRITE_PROMPT = """
[SYSTEM PROMPT: CANDIDATE GATE TARGETED REWRITE]

너는 독립적인 Candidate Gate Reviewer가 이미 REGENERATE 판정을 내린
Candidate 하나를 같은 소재, 같은 대상 안에서
Gate가 지적한 문제를 해결한 버전으로 다시 쓰는 역할이다.

새로운 대상이나 다른 방향으로 바꾸지 마라.
같은 대상(subject)을 유지한 채,
아래 [GATE REJECTION REASON]에서 지적된
너무 넓거나 일반적인 질문, 또는
구체적인 메커니즘/예상 밖 연결이 없는 Reveal 대신

- 수치
- 임계값
- 예외
- 조건
- 순서
- 구체적인 메커니즘
- 예상 밖의 연결

중 하나 이상이 들어간
더 좁고 구체적인 Core Question과 Reveal로 다시 써라.

OUTPUT CONTRACT의 winner 객체와
동일한 형식의 JSON 객체 하나만 반환하라
(status 필드 없이 winner 필드 내용만):

{
  "topic": "",
  "angle": "",
  "core_question": "",
  "micro_narrative": {
    "hook": "",
    "core_question": "",
    "reveal": "",
    "payoff": ""
  },
  "fact_check_focus": [],
  "visual_proof": [""],
  "selection_reason": ""
}
"""


def _rewrite_candidate_for_gate_feedback(candidate, reason, *, model=MODEL):
    """Targeted, same-subject rewrite of a candidate Candidate Gate rejected
    as REGENERATE.

    Feeds the Gate's own rejection reason back in and asks for a version of
    the SAME subject that resolves it (never a new topic direction). The
    rewritten candidate is validated with the same ``validate_candidate``
    schema check every normal Winner goes through, and it is NOT treated as
    accepted here -- the caller must still run it back through the
    unmodified Narrowness self-critique and the unmodified Candidate Gate.

    Returns the rewritten winner dict, or ``None`` if the rewrite call
    failed or produced an unusable/malformed candidate (in which case the
    caller should treat this rewrite attempt as spent and move on).
    """

    # Imported lazily to avoid a module-load-time dependency between
    # content/candidate_gate.py and content/candidate_explorer.py (neither
    # module currently imports the other at top level).
    #
    # ``import content.candidate_explorer`` resolves to the
    # content/candidate_explorer/ package (a package always wins import
    # resolution over a same-named module), which only re-exports a small,
    # explicit surface (e.g. MODEL). The legacy module itself -- with
    # ``extract_json``/``validate_candidate``/``_self_critique_narrowness``
    # -- is loaded there as ``_LEGACY``, so it must be reached through that
    # attribute, not imported directly off the package.
    import content.candidate_explorer as _ce_pkg

    extract_json = _ce_pkg._LEGACY.extract_json
    validate_candidate = _ce_pkg._LEGACY.validate_candidate

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    original_summary = (
        f"Topic: {candidate.get('topic', '')}\n"
        f"Angle: {candidate.get('angle', '')}\n"
        f"Core Question: {candidate.get('core_question', '')}\n"
        f"Hook: {micro.get('hook', '')}\n"
        f"Reveal: {micro.get('reveal', '')}\n"
        f"Payoff: {micro.get('payoff', '')}\n"
        f"\n[GATE REJECTION REASON]\n{reason}"
    )

    call_number = authorize_call(model)
    print(f"💳 Candidate Gate rewrite API call authorized: #{call_number}")

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _CANDIDATE_GATE_REWRITE_PROMPT},
                {"role": "user", "content": original_summary},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
    except Exception:
        return None

    usage = record_usage(model, response)
    print(f"💰 Candidate Gate rewrite call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        return None

    try:
        parsed = extract_json(content)
    except Exception:
        return None

    try:
        return validate_candidate(parsed, prefix="winner", runner_up=False)
    except Exception:
        return None


def _narrowness_recheck_ok(candidate, *, model):
    """Re-runs the unmodified Narrowness self-critique gate on a candidate
    that Candidate Gate's bounded recovery just rewrote.

    A rewrite aimed at satisfying Candidate Gate could plausibly reintroduce
    the broadness the separate Narrowness self-critique gate already guards
    against, so a recovered candidate must clear that gate too, exactly as a
    freshly generated Winner would. Returns ``(ok, reason)``. If the
    Narrowness gate itself cannot be reached/evaluated, this fails open
    (treats the candidate as acceptable to this specific recheck) so a
    missing/broken import never fabricates a false REGENERATE -- the
    unmodified Candidate Gate re-check that follows remains the real gate.
    """

    try:
        import content.candidate_explorer as _ce_pkg

        self_critique_narrowness = _ce_pkg._LEGACY._self_critique_narrowness
    except Exception:
        return True, ""

    try:
        critique = self_critique_narrowness(candidate, model=model)
    except Exception:
        return True, ""

    if critique.get("verdict") == "TOO_BROAD":
        return False, critique.get("reason", "")

    return True, ""


def evaluate_candidate(
    candidate,
    *,
    model=MODEL,
    role="Winner",
):
    """Candidate Gate with bounded, same-subject rewrite recovery.

    Behaves exactly like ``_evaluate_candidate_once`` for a candidate that
    PASSes outright. For a candidate the Gate REGENERATEs, this gives it up
    to ``MAX_CANDIDATE_GATE_REWRITES`` targeted, same-subject rewrite
    attempts (using the Gate's own rejection reason) before falling back to
    the original REGENERATE result -- at which point the caller's existing
    discard-and-move-to-a-new-topic behavior is unchanged.

    No Gate threshold or PASS/REGENERATE logic is altered by this: every
    rewritten candidate is judged by the exact same, unmodified
    ``_evaluate_candidate_once`` (and, before that, the exact same,
    unmodified Narrowness self-critique). There is no forced-pass path --
    if a rewrite still fails both gates, or the rewrite itself fails, the
    attempt is simply spent, and after ``MAX_CANDIDATE_GATE_REWRITES``
    attempts the candidate is discarded exactly as it was before this
    recovery existed.
    """

    result = _evaluate_candidate_once(candidate, model=model, role=role)

    rewrite_attempts = 0

    while (
        result.get("status") == "REGENERATE"
        and rewrite_attempts < MAX_CANDIDATE_GATE_REWRITES
    ):

        print("")
        print("=" * 64)
        print(
            "🔧 CANDIDATE GATE BOUNDED RECOVERY: "
            f"rewrite {rewrite_attempts + 1}/{MAX_CANDIDATE_GATE_REWRITES}"
        )
        print("=" * 64)
        print("이유:", result.get("reason", ""))
        print("=" * 64)

        rewritten = _rewrite_candidate_for_gate_feedback(
            candidate,
            result.get("reason", ""),
            model=model,
        )

        rewrite_attempts += 1

        if rewritten is None:
            # Rewrite itself failed or was unusable -- this attempt is
            # spent. Keep the original (still REGENERATE) result so the
            # loop condition above can still try again if attempts remain.
            continue

        narrowness_ok, narrowness_reason = _narrowness_recheck_ok(
            rewritten,
            model=model,
        )

        if not narrowness_ok:
            result = {
                "status": "REGENERATE",
                "reason": (
                    "Candidate Gate 재검토 중 Narrowness 재검사 실패: "
                    f"{narrowness_reason}"
                ),
            }
            continue

        result = _evaluate_candidate_once(rewritten, model=model, role=role)

        if result.get("status") == "PASS":
            # Mutate the caller's candidate dict IN PLACE (rather than
            # returning a new object the caller would have to remember to
            # use) so the Winner the rest of the pipeline scripts/renders
            # is the SAME rewritten candidate that actually passed both
            # gates, not the original, discarded, too-broad one.
            candidate.clear()
            candidate.update(rewritten)

    return result
