from quality.judge import (
    run_judge,
    print_judge_result,
)
from quality.explanation_judge import (
    run_explanation_judge,
    print_explanation_result,
)


DEFAULT_JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
    "explanation",
]

MIN_CONFIDENCE = 0.72
MAX_REVIEWS_PER_TYPE = 3
MIN_CRITICAL_REVIEWS = 2


def needs_extra_review(result):
    if not isinstance(result, dict):
        return True

    confidence = float(result.get("confidence", 0.0))
    critical_risk = bool(result.get("critical_risk", False))
    score = float(result.get("score", 0.0))

    if confidence < MIN_CONFIDENCE:
        return True
    if critical_risk:
        return True
    if 5.0 <= score <= 7.0:
        return True
    return False


def has_internal_disagreement(results, threshold=2.5):
    if len(results) < 2:
        return False
    scores = [float(item.get("score", 0.0)) for item in results]
    return (max(scores) - min(scores)) >= threshold


def _run_specialist_once(judge_type, script_data, *, model):
    if judge_type == "explanation":
        result = run_explanation_judge(
            script_data,
            model=model,
        )
        print_explanation_result(result)
        return result

    result = run_judge(
        judge_type,
        script_data,
        model=model,
    )
    print_judge_result(result)
    return result


def run_specialist_pool(
    judge_type,
    script_data,
    *,
    model="gpt-4o-mini",
):
    results = []

    first = _run_specialist_once(
        judge_type,
        script_data,
        model=model,
    )
    results.append(first)

    if not needs_extra_review(first):
        return results

    second = _run_specialist_once(
        judge_type,
        script_data,
        model=model,
    )
    results.append(second)

    critical_exists = any(
        item.get("critical_risk", False)
        for item in results
    )
    disagreement = has_internal_disagreement(results)

    if not disagreement and not critical_exists:
        return results

    if len(results) < MAX_REVIEWS_PER_TYPE:
        third = _run_specialist_once(
            judge_type,
            script_data,
            model=model,
        )
        results.append(third)

    return results


def run_judge_pool(
    script_data,
    *,
    judge_types=None,
    model="gpt-4o-mini",
):
    if judge_types is None:
        judge_types = DEFAULT_JUDGE_TYPES

    pool_results = {}

    print("")
    print("=" * 56)
    print("⚖️ V3 JUDGE POOL START")
    print("=" * 56)

    for judge_type in judge_types:
        print("")
        print(f"🔍 전문 심사 시작: {judge_type.upper()}")
        pool_results[judge_type] = run_specialist_pool(
            judge_type,
            script_data,
            model=model,
        )

    print("")
    print("=" * 56)
    print("✅ V3 JUDGE POOL COMPLETE")
    print("=" * 56)
    return pool_results


def get_pool_statistics(pool_results):
    by_type = {
        judge_type: len(results)
        for judge_type, results in pool_results.items()
    }
    return {
        "total_reviews": sum(by_type.values()),
        "by_type": by_type,
    }


def print_pool_statistics(pool_results):
    stats = get_pool_statistics(pool_results)

    print("")
    print("=" * 50)
    print("📊 JUDGE POOL STATISTICS")
    print("=" * 50)
    print("총 Judge 호출:", stats["total_reviews"])

    for judge_type, count in stats["by_type"].items():
        print(f" - {judge_type}: {count}회")

    print("=" * 50)
