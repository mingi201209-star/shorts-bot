import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content.candidate_explorer import build_execution_context


FIXED_TOPIC = "초고층 빌딩에는 왜 사람이 사용하지 않는 층이 있을까?"


def require(text, needle, label):
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main():
    main_source = Path("main.py").read_text(encoding="utf-8")
    explorer_source = Path(
        "content/candidate_explorer.py"
    ).read_text(encoding="utf-8")
    workflow_source = Path(
        ".github/workflows/main.yml"
    ).read_text(encoding="utf-8")

    # Blank topic must preserve the original automatic selector path.
    require(
        main_source,
        "choose_topic_direction()",
        "automatic topic selector",
    )
    require(
        main_source,
        "if forced_topic:",
        "fixed topic branch",
    )
    require(
        main_source,
        "else:\n\n                topic_info = (\n                    choose_topic_direction()",
        "automatic fallback branch",
    )

    automatic_context = build_execution_context(
        {
            "category": "자동 탐색",
            "topic": "자동 방향",
        },
        fixed_topic=None,
    )
    require(
        automatic_context,
        "탐색의 출발점이지",
        "legacy automatic explorer context",
    )

    fixed_context = build_execution_context(
        {
            "category": "지정 주제",
            "topic": FIXED_TOPIC,
        },
        fixed_topic=FIXED_TOPIC,
    )
    require(
        fixed_context,
        "FIXED PRODUCTION TOPIC",
        "fixed production explorer context",
    )
    require(
        fixed_context,
        FIXED_TOPIC,
        "exact fixed topic",
    )
    require(
        fixed_context,
        "runner_up은 null",
        "fixed topic runner-up protection",
    )

    require(
        explorer_source,
        "winner_topic != fixed_topic",
        "fixed topic exact-match guard",
    )
    require(
        explorer_source,
        'result["runner_up"] = None',
        "fixed topic runner-up disable",
    )

    require(
        workflow_source,
        "topic:\n        description:",
        "workflow dispatch topic input",
    )
    require(
        workflow_source,
        "SHORTS_TOPIC: ${{ inputs.topic }}",
        "workflow topic environment",
    )

    # Regression markers: topic input must not change production policies.
    protected_markers = {
        "video/hook_visual_dominance.py": [
            "HOOK_SUBJECT_DOMINANCE_MIN = 8.0",
            "HOOK_ACTION_MATCH_MIN = 7.0",
            "HOOK_MAX_COMPETING_SUBJECT_RISK = 4.0",
        ],
        "content/hook_experiment.py": [
            "HOOK_MIN_SCORE = 7.2",
            "HOOK_GENERATION_COUNT = 10",
        ],
        "config.py": [
            'TTS_RATE = "+13%"',
        ],
    }

    for path, markers in protected_markers.items():
        source = Path(path).read_text(encoding="utf-8")
        for marker in markers:
            require(source, marker, f"protected policy in {path}")

    print("✅ production topic input regression PASS")
    print("   blank topic -> automatic selection preserved")
    print("   provided topic -> exact fixed topic context")
    print("   protected Hook/dominance/TTS markers preserved")


if __name__ == "__main__":
    main()
