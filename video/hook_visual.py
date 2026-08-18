import json
import re

from config import (
    PEXELS_RELEVANT_TOP_N,
    PEXELS_SEARCH_PER_PAGE,
)

from video.video_downloader import (
    USED_VIDEO_IDS,
    _candidate_matches_subject_anchor,
    _fallback_query_for_lock,
    _general_fallback_queries,
    _has_explicit_human_intent,
    _historical_candidate_safe,
    _human_centric_candidate,
    _is_nature_object_query,
    _page_slug,
    _subject_anchor_terms,
    build_context_locked_query,
    fetch_pexels_video,
    normalize_search_query,
    search_pexels_candidates,
)


HOOK_VISUAL_CRITERIA = (
    "semantic_match",
    "subject_visibility",
    "mobile_clarity",
    "visual_motion",
    "novelty",
    "obstruction_risk",
)

HOOK_VISUAL_MIN_SCORE = 6.6


def _tokens(text):
    return {
        item
        for item in re.findall(
            r"[a-z0-9]+",
            normalize_search_query(text),
        )
        if len(item) >= 3
    }


def _safe_candidate_pool(
    candidates,
    query,
    historical,
):
    ordered = sorted(
        candidates,
        key=lambda item: int(
            item.get(
                "search_position",
                9999,
            )
        ),
    )

    ordered = [
        item
        for item in ordered
        if item.get("id")
        not in USED_VIDEO_IDS
    ]

    if historical:
        ordered = [
            item
            for item in ordered
            if _historical_candidate_safe(
                item
            )
        ]

        return ordered[
            :max(
                1,
                min(
                    3,
                    PEXELS_RELEVANT_TOP_N,
                ),
            )
        ]

    if (
        _is_nature_object_query(query)
        and not _has_explicit_human_intent(
            query
        )
    ):
        subject_safe = [
            item
            for item in ordered
            if not _human_centric_candidate(
                item
            )
        ]

        if subject_safe:
            ordered = subject_safe

    subject_anchors = (
        _subject_anchor_terms(query)
    )

    if subject_anchors:
        anchor_matches = [
            item
            for item in ordered
            if _candidate_matches_subject_anchor(
                item,
                query,
            )
        ]

        if anchor_matches:
            ordered = anchor_matches

    return ordered[
        :max(
            1,
            PEXELS_RELEVANT_TOP_N,
        )
    ]


def _score_candidate(
    candidate,
    scene,
):
    keyword = normalize_search_query(
        scene.get(
            "keyword",
            "",
        )
    )

    slug = _page_slug(
        candidate.get(
            "page_url"
        )
    )

    query_tokens = _tokens(
        keyword
    )
    slug_tokens = _tokens(
        slug
    )

    overlap = len(
        query_tokens
        & slug_tokens
    )

    semantic_match = min(
        10.0,
        3.5 + overlap * 2.0,
    )

    subject_anchors = (
        _subject_anchor_terms(
            keyword
        )
    )

    subject_visibility = (
        8.8
        if (
            subject_anchors
            and _candidate_matches_subject_anchor(
                candidate,
                keyword,
            )
        )
        else min(
            9.0,
            semantic_match + 0.8,
        )
    )

    width = float(
        candidate.get(
            "width",
            0,
        )
        or 0
    )
    height = float(
        candidate.get(
            "height",
            0,
        )
        or 0
    )

    portrait = (
        height >= width
        and height > 0
    )

    mobile_clarity = (
        8.8
        if portrait
        else 5.5
    )

    if (
        width >= 720
        and height >= 1280
    ):
        mobile_clarity = min(
            10.0,
            mobile_clarity + 0.7,
        )

    motion_terms = {
        "moving",
        "running",
        "flowing",
        "pouring",
        "rotating",
        "flying",
        "walking",
        "driving",
        "working",
        "opening",
        "closing",
        "burning",
        "waves",
        "waterfall",
        "traffic",
        "timelapse",
        "machinery",
    }

    motion_hits = len(
        slug_tokens
        & motion_terms
    )

    duration = float(
        candidate.get(
            "duration",
            0,
        )
        or 0
    )

    visual_motion = min(
        10.0,
        5.0
        + motion_hits * 1.5
        + (
            0.7
            if duration >= 4.0
            else 0.0
        ),
    )

    generic_terms = {
        "video",
        "background",
        "people",
        "person",
        "nature",
        "technology",
    }

    distinctive = len(
        slug_tokens
        - generic_terms
    )

    novelty = min(
        9.5,
        5.5 + distinctive * 0.35,
    )

    obstruction_terms = {
        "portrait",
        "face",
        "person",
        "people",
        "text",
        "sign",
        "screen",
        "phone",
        "poster",
        "document",
        "menu",
        "label",
    }

    obstruction_hits = len(
        slug_tokens
        & obstruction_terms
    )

    obstruction_risk = min(
        10.0,
        obstruction_hits * 2.2,
    )

    visual_goal = str(
        scene.get(
            "visual_goal",
            "",
        )
    ).lower()

    if (
        "클로즈" in visual_goal
        or "close" in visual_goal
    ):
        subject_visibility = min(
            10.0,
            subject_visibility + 0.5,
        )
        mobile_clarity = min(
            10.0,
            mobile_clarity + 0.5,
        )

    scores = {
        "semantic_match": round(
            semantic_match,
            3,
        ),
        "subject_visibility": round(
            subject_visibility,
            3,
        ),
        "mobile_clarity": round(
            mobile_clarity,
            3,
        ),
        "visual_motion": round(
            visual_motion,
            3,
        ),
        "novelty": round(
            novelty,
            3,
        ),
        "obstruction_risk": round(
            obstruction_risk,
            3,
        ),
    }

    total = (
        scores["semantic_match"]
        * 1.35
        + scores[
            "subject_visibility"
        ] * 1.30
        + scores[
            "mobile_clarity"
        ] * 1.20
        + scores[
            "visual_motion"
        ] * 0.80
        + scores["novelty"]
        * 0.65
        + (
            10.0
            - scores[
                "obstruction_risk"
            ]
        ) * 1.15
    ) / 6.45

    return scores, round(
        total,
        3,
    )


def fetch_hook_pexels_video(scene):
    original_query = str(
        scene.get(
            "keyword",
            "",
        )
    ).strip()

    effective_query, context_lock = (
        build_context_locked_query(
            original_query
        )
    )

    historical = bool(
        context_lock
    )

    queries = [
        effective_query
    ]

    if historical:
        fallback = (
            _fallback_query_for_lock(
                context_lock
            )
        )

        if fallback not in queries:
            queries.append(
                fallback
            )

    else:
        for fallback in (
            _general_fallback_queries(
                effective_query
            )
        ):
            if fallback not in queries:
                queries.append(
                    fallback
                )

    audit = {
        "query": original_query,
        "effective_query": (
            effective_query
        ),
        "context_lock": context_lock,
        "criteria": list(
            HOOK_VISUAL_CRITERIA
        ),
        "minimum": (
            HOOK_VISUAL_MIN_SCORE
        ),
        "searches": [],
        "selected": None,
        "fallback": False,
    }

    best = None

    for search_query in queries:
        candidates = (
            search_pexels_candidates(
                search_query,
                per_page=(
                    PEXELS_SEARCH_PER_PAGE
                ),
            )
        )

        safe_pool = (
            _safe_candidate_pool(
                candidates,
                search_query,
                historical,
            )
        )

        scored = []

        for candidate in safe_pool:
            scores, total_score = (
                _score_candidate(
                    candidate,
                    {
                        **scene,
                        "keyword": (
                            search_query
                        ),
                    },
                )
            )

            scored.append({
                "candidate": candidate,
                "scores": scores,
                "total_score": (
                    total_score
                ),
            })

        scored.sort(
            key=lambda item: (
                item[
                    "total_score"
                ]
            ),
            reverse=True,
        )

        audit[
            "searches"
        ].append({
            "query": search_query,
            "candidate_count": len(
                candidates
            ),
            "safe_pool_count": len(
                safe_pool
            ),
            "top": [
                {
                    "id": item[
                        "candidate"
                    ].get("id"),
                    "search_position": item[
                        "candidate"
                    ].get(
                        "search_position"
                    ),
                    "page_url": item[
                        "candidate"
                    ].get(
                        "page_url"
                    ),
                    "scores": item[
                        "scores"
                    ],
                    "total_score": item[
                        "total_score"
                    ],
                }
                for item in scored[:5]
            ],
        })

        if (
            scored
            and (
                best is None
                or scored[0][
                    "total_score"
                ] > best[
                    "total_score"
                ]
            )
        ):
            best = scored[0]

        if (
            scored
            and scored[0][
                "total_score"
            ] >= HOOK_VISUAL_MIN_SCORE
        ):
            best = scored[0]
            break

    if (
        best
        and best[
            "total_score"
        ] >= HOOK_VISUAL_MIN_SCORE
    ):
        candidate = best[
            "candidate"
        ]

        video_id = candidate.get(
            "id"
        )

        if video_id is not None:
            USED_VIDEO_IDS.add(
                video_id
            )

        audit["selected"] = {
            "id": video_id,
            "page_url": candidate.get(
                "page_url"
            ),
            "scores": best[
                "scores"
            ],
            "total_score": best[
                "total_score"
            ],
            "mode": (
                "hook_strict"
            ),
        }

        print_hook_visual_audit(
            audit
        )

        return candidate[
            "url"
        ]

    audit["fallback"] = True
    audit["fallback_reason"] = (
        "엄격 Hook visual 기준을 충족하는 안전 후보가 없어 기존 Pexels 선택 경로로 fallback"
    )

    print_hook_visual_audit(
        audit
    )

    return fetch_pexels_video(
        original_query
    )


def print_hook_visual_audit(audit):
    print("")
    print("=" * 64)
    print("🎯 HOOK VISUAL AUDIT JSON")
    print(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        )
    )
    print("=" * 64)
