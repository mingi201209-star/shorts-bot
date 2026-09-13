from pathlib import Path


RUNNER = Path("content/script_engine_v2_runner.py")
DOWNLOADER = Path("video/video_downloader.py")
FINAL_QA = Path("quality/final_visual_semantic_qa.py")
MARKER = "# RUN_34753759233_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1"
RESULT_MARKER = "# RUN_34781319743_RESULT_VISUAL_PROMISE_V1"
FINAL_QA_MARKER = "# RUN_34781319743_RESULT_VISUAL_FINAL_QA_V1"


runner = RUNNER.read_text(encoding="utf-8")
if MARKER not in runner:
    anchor = "def _owned_claim_keyword_terms(contract):"
    if anchor not in runner:
        raise RuntimeError(
            "Run 34753759233 scene-role grounded keyword: "
            "_owned_claim_keyword_terms anchor not found "
            "(ci_grounded_keyword_contract_hotfix.py must run first)"
        )

    runner = runner.rstrip() + "\n\n\n" + MARKER + r'''
# Run 34753759233 (fixed-topic "착륙 직후 날개 위로 솟는 스포일러", exact main
# 65f6f5e0815e5c24c858fb5ec659b69e662d83d3, immediately after #360/#361
# landed): PR #360/#361 fixed literal spoiler grounding at the Candidate
# Pool/pre-Writer boundary; this run then proved a *separate* bug exposed
# only once that fix worked. `owned_claim_id` values like
# "spoiler_weight_to_wheels" and "spoiler_braking_effectiveness" are
# causal-LINEAGE labels ("this result claim descends from the spoiler
# claim"), not a promise that this specific Scene's own narration/
# visual_goal shows the spoiler. `_owned_claim_keyword_terms` previously
# tokenized `owned_claim_id` unconditionally, so "spoiler" leaked into
# Scene 4/5's retrieval keyword even though neither Scene names it. The
# retrieval/proof layer then promoted that bookkeeping token into a hard
# visual component requirement.
#
# Fix: a concrete physical-component word sourced only from `owned_claim_id`
# is no longer trusted as claim-specific keyword content unless the claim's
# own descriptive grounding independently repeats it. Non-component id
# tokens remain useful retrieval hints. No API/retry/budget/threshold change.
_RUN_34753759233_PHYSICAL_COMPONENT_TERMS = {
    "aircraft", "wing", "window", "cabin", "engine", "spinner",
    "bridge", "tunnel", "road", "building", "chevron", "flap",
    "spoiler", "speedbrake", "winglet", "wingtip",
}

_run_34753759233_previous_owned_claim_keyword_terms = _owned_claim_keyword_terms


def _owned_claim_keyword_terms(contract):
    contract = contract if isinstance(contract, dict) else {}
    id_terms = _grounded_keyword_terms(
        str(contract.get("owned_claim_id") or "").replace("_", " ")
    )
    content_values = [str(contract.get("supporting_evidence_summary") or "")]
    content_values.extend(
        str(item) for item in contract.get("allowed_paraphrase_scope") or [] if item
    )
    content_values.extend(
        str(item) for item in contract.get("required_concepts") or [] if item
    )
    content_terms = []
    for value in content_values:
        for term in _grounded_keyword_terms(value):
            if term not in content_terms:
                content_terms.append(term)

    result = []
    for term in id_terms:
        if term in _RUN_34753759233_PHYSICAL_COMPONENT_TERMS and term not in content_terms:
            continue
        if term not in result:
            result.append(term)
    for term in content_terms:
        if term not in result:
            result.append(term)
    return result
''' + "\n"
    RUNNER.write_text(runner, encoding="utf-8")
    print("✅ Run 34753759233 scene-role grounded keyword applied: claim-id component leakage closed")
else:
    print("✅ Run 34753759233 scene-role grounded keyword already installed")


# Run 34781319743 / #550 HUMAN QA:
# #362 correctly stopped RESULT scenes from inheriting a spoiler hard-anchor,
# but it accidentally treated generic aircraft/wing stock as sufficient.
# Actual Scene 4 rendered the old green night-vision aircraft, and Scene 5
# rendered a cloud-level passenger-wing shot while narration promised
# weight-on-wheels and braking/landing-rollout results. The visual_goal is the
# authority for what a RESULT scene must visibly establish. Keep the canonical
# subject as context, but require one goal-specific result-evidence family and
# use that same family to steer retrieval. This is a semantic filter only:
# no score threshold, provider, Vision/API call, retry, or generation budget
# is changed.
downloader = DOWNLOADER.read_text(encoding="utf-8")
if RESULT_MARKER not in downloader:
    required_symbols = (
        "def enforce_visual_subject_anchor_query(",
        "def general_scene_unknown_safe_tier(",
        "def choose_best_candidate(",
        "def get_last_final_visual_selection(",
    )
    missing = [symbol for symbol in required_symbols if symbol not in downloader]
    if missing:
        raise RuntimeError(
            "Run 34781319743 result visual contract requires final downloader contracts: "
            + ", ".join(missing)
        )

    downloader = downloader.rstrip() + "\n\n\n" + RESULT_MARKER + r'''
# Exact production authority: Run 34781319743 (#550), where Scene 4 selected
# Pixabay 15270 (night-vision aircraft/binoculars) and Scene 5 selected Pixabay
# 142647 (generic wing/clouds). Both were machine-PASS but human-FAIL.
#
# The contract is intentionally derived from narration/visual_goal, never from
# a causal keyword alone. `visual_goal` wins when present. It currently closes
# two general observable RESULT families exposed by #550:
#   - weight-on-wheels / landing-gear result
#   - runway / landing-rollout / braking result
# Additional families must be added only from future concrete counterexamples.
_RUN_34781319743_RESULT_GROUPS = {
    "landing_gear_wheel": {
        "goal_aliases": (
            "착륙 장치", "랜딩기어", "바퀴",
            "landing gear", "undercarriage", "wheel", "wheels",
        ),
        "candidate_aliases": (
            "landing gear", "undercarriage", "wheel", "wheels",
            "tire", "tires", "tyre", "tyres",
        ),
        "query_terms": ("aircraft", "landing", "gear", "wheel", "touchdown"),
    },
    "runway_rollout": {
        "goal_aliases": (
            "활주로", "지상 활주", "감속", "제동",
            "runway", "rollout", "ground roll", "braking",
            "deceleration", "decelerating",
        ),
        "candidate_aliases": (
            "runway", "rollout", "ground roll", "braking",
            "deceleration", "decelerating", "touchdown",
            "taxiing", "taxiway",
        ),
        "query_terms": ("aircraft", "runway", "landing", "braking", "rollout"),
    },
}
_RUN_34781319743_CURRENT_RESULT_CONTRACT = {
    "required": False,
    "group": "",
    "source": "",
    "query_terms": [],
}

# Canonical components can remain causal lineage in Script grounding, but when
# the Scene's own visual promise is an observable downstream result they must
# not crowd the retrieval query unless narration/visual_goal explicitly names
# them.
_RUN_34781319743_CAUSAL_COMPONENT_ALIASES = {
    "wing": ("wing", "날개"),
    "spoiler": ("spoiler", "spoilers", "스포일러"),
    "flap": ("flap", "flaps", "플랩"),
    "winglet": ("winglet", "wingtip", "윙렛", "날개 끝"),
    "chevron": ("chevron", "chevrons", "셰브론", "체브론", "톱니"),
    "window": ("window", "windows", "창문"),
    "engine": ("engine", "engines", "엔진"),
    "spinner": ("spinner", "spinners", "스피너"),
}


def _run_34781319743_contains(value, aliases):
    raw = str(value or "").lower()
    return any(str(alias).lower() in raw for alias in aliases)


def _run_34781319743_result_contract(narration, visual_goal):
    # visual_goal is the strongest scene-local visual promise. Only fall back
    # to narration when a goal is blank; do not infer a result family from the
    # retrieval keyword or canonical subject.
    goal = str(visual_goal or "").strip().lower()
    authority = goal if goal else str(narration or "").strip().lower()
    if not authority:
        return {
            "required": False, "group": "", "source": "", "query_terms": []
        }
    # Prefer runway/rollout when the goal explicitly promises the whole
    # deceleration/ground-roll result, even if narration also mentions wheels.
    order = ("runway_rollout", "landing_gear_wheel")
    for group in order:
        spec = _RUN_34781319743_RESULT_GROUPS[group]
        if _run_34781319743_contains(authority, spec["goal_aliases"]):
            return {
                "required": True,
                "group": group,
                "source": "visual_goal" if goal else "narration",
                "query_terms": list(spec["query_terms"]),
            }
    return {"required": False, "group": "", "source": "", "query_terms": []}


def _run_34781319743_candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""
    helper = globals().get("_candidate_text_for_visual_contract")
    if callable(helper):
        return str(helper(candidate) or "").lower()
    helper = globals().get("_candidate_metadata")
    if callable(helper):
        return str(helper(candidate) or "").lower()
    return " ".join(
        str(candidate.get(key) or "").lower()
        for key in ("title", "tags", "description", "metadata", "source_url", "url")
    )


def _run_34781319743_result_text_matches(text, contract):
    if not bool((contract or {}).get("required")):
        return True
    group = str((contract or {}).get("group") or "")
    spec = _RUN_34781319743_RESULT_GROUPS.get(group)
    if not spec:
        return False
    return _run_34781319743_contains(text, spec["candidate_aliases"])


def _run_34781319743_result_candidate_matches(candidate, contract=None):
    contract = contract or _RUN_34781319743_CURRENT_RESULT_CONTRACT
    return _run_34781319743_result_text_matches(
        _run_34781319743_candidate_text(candidate), contract
    )


def get_current_result_visual_contract():
    return dict(_RUN_34781319743_CURRENT_RESULT_CONTRACT)


_run_34781319743_previous_enforce_visual_subject_anchor_query = (
    enforce_visual_subject_anchor_query
)


def enforce_visual_subject_anchor_query(
    *, narration, visual_goal, query, visual_type="real_world_broll"
):
    global _RUN_34781319743_CURRENT_RESULT_CONTRACT
    effective = _run_34781319743_previous_enforce_visual_subject_anchor_query(
        narration=narration,
        visual_goal=visual_goal,
        query=query,
        visual_type=visual_type,
    )
    contract = _run_34781319743_result_contract(narration, visual_goal)
    _RUN_34781319743_CURRENT_RESULT_CONTRACT = dict(contract)
    if not contract["required"]:
        return effective

    source = f"{narration or ''} {visual_goal or ''}".lower()
    base_words = normalize_search_query(effective).split()
    preferred = list(contract["query_terms"])
    words = []
    for word in preferred:
        if word and word not in words:
            words.append(word)

    for word in base_words:
        # Remove a causal/canonical component from a RESULT retrieval query only
        # when the Scene's own narration/visual_goal does not name it.
        aliases = _RUN_34781319743_CAUSAL_COMPONENT_ALIASES.get(word)
        if aliases and not _run_34781319743_contains(source, aliases):
            continue
        if word not in words:
            words.append(word)
        if len(words) >= 7:
            break

    result_query = " ".join(words[:7]).strip()
    current_subject = globals().get("_CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT")
    if isinstance(current_subject, dict):
        current_subject["effective_query"] = result_query

    if result_query != normalize_search_query(effective):
        print(
            "[RESULT_VISUAL_CONTRACT] "
            f"group={contract['group']} source={contract['source']} "
            f"original={normalize_search_query(effective) or 'none'} "
            f"effective={result_query}"
        )
    return result_query


_run_34781319743_previous_general_scene_unknown_safe_tier = (
    general_scene_unknown_safe_tier
)


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _run_34781319743_previous_general_scene_unknown_safe_tier(
        candidate, scene_query
    )
    contract = _RUN_34781319743_CURRENT_RESULT_CONTRACT
    if not bool(contract.get("required")):
        return tier, label
    if not _run_34781319743_result_candidate_matches(candidate, contract):
        return max(5, int(tier or 0)), (
            "MISSING_RESULT_VISUAL_EVIDENCE_"
            + str(contract.get("group") or "UNKNOWN").upper()
        )
    return tier, label


_run_34781319743_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(
    candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None
):
    global _LAST_FINAL_VISUAL_SELECTION
    contract = _RUN_34781319743_CURRENT_RESULT_CONTRACT
    candidate_list = list(candidates or [])
    if bool(contract.get("required")) and not historical:
        eligible = []
        for candidate in candidate_list:
            if _run_34781319743_result_candidate_matches(candidate, contract):
                eligible.append(candidate)
            else:
                print(
                    "[RESULT_VISUAL_REJECT] "
                    f"candidate={candidate.get('source_id', candidate.get('id', ''))} "
                    f"group={contract.get('group')} reason=missing_goal_result_evidence"
                )
        candidate_list = eligible
        if not candidate_list:
            _LAST_FINAL_VISUAL_SELECTION = {
                "accepted": False,
                "mode": "MISSING_RESULT_VISUAL_EVIDENCE",
                "tier": 99,
                "visual_state": "UNKNOWN",
                "anchor_matched": 0,
                "anchor_total": 0,
                "provider": "",
                "source_id": "",
                "metadata": "",
                "result_visual_contract_required": True,
                "required_result_visual_group": str(contract.get("group") or ""),
                "result_visual_evidence_matched": False,
            }
            return None

    return _run_34781319743_previous_choose_best_candidate(
        candidate_list,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )


_run_34781319743_previous_get_last_final_visual_selection = (
    get_last_final_visual_selection
)


def get_last_final_visual_selection():
    selection = _run_34781319743_previous_get_last_final_visual_selection()
    contract = _RUN_34781319743_CURRENT_RESULT_CONTRACT
    selection["result_visual_contract_required"] = bool(contract.get("required"))
    selection["required_result_visual_group"] = str(contract.get("group") or "")
    if bool(contract.get("required")):
        selection["result_visual_evidence_matched"] = (
            _run_34781319743_result_text_matches(
                str(selection.get("metadata") or ""), contract
            )
        )
    else:
        selection["result_visual_evidence_matched"] = True
    return selection
''' + "\n"
    DOWNLOADER.write_text(downloader, encoding="utf-8")
    print(
        "✅ Run 34781319743 result visual promise installed: "
        "wheel/runway RESULT scenes reject generic aircraft/wing stock"
    )
else:
    print("✅ Run 34781319743 result visual promise already installed")


final_qa = FINAL_QA.read_text(encoding="utf-8")
if FINAL_QA_MARKER not in final_qa:
    if "def record_final_visual_scene(" not in final_qa:
        raise RuntimeError(
            "Run 34781319743 result final QA: record_final_visual_scene not found"
        )
    if "def validate_final_visual_semantic_qa(" not in final_qa:
        raise RuntimeError(
            "Run 34781319743 result final QA: validate_final_visual_semantic_qa not found"
        )
    final_qa = final_qa.rstrip() + "\n\n\n" + FINAL_QA_MARKER + r'''
# Defense in depth for #550 HUMAN QA. The selection boundary should reject
# generic result footage first; Final Visual Semantic QA independently rejects
# stale/alternate lineage that claims a wheel/runway RESULT query without any
# corresponding retrieval evidence in the selected asset metadata.
_RUN_34781319743_FINAL_RESULT_GROUPS = {
    "landing_gear_wheel": (
        "landing gear", "undercarriage", "wheel", "wheels",
        "tire", "tires", "tyre", "tyres",
    ),
    "runway_rollout": (
        "runway", "rollout", "ground roll", "braking",
        "deceleration", "decelerating", "touchdown",
        "taxiing", "taxiway",
    ),
}


def _run_34781319743_final_result_group(query):
    normalized = str(query or "").lower().replace("-", " ")
    words = set(normalized.split())
    if (
        "landing gear" in normalized
        or bool(words & {"wheel", "wheels", "undercarriage", "tire", "tires", "tyre", "tyres"})
    ):
        return "landing_gear_wheel"
    if bool(
        words
        & {
            "runway", "rollout", "braking", "deceleration",
            "decelerating", "touchdown", "taxiing", "taxiway",
        }
    ):
        return "runway_rollout"
    return ""


def _run_34781319743_final_result_metadata_ok(item, group):
    if not group:
        return True
    metadata = str((item or {}).get("metadata") or "").lower()
    aliases = _RUN_34781319743_FINAL_RESULT_GROUPS.get(group, ())
    return any(alias in metadata for alias in aliases)


_run_34781319743_previous_record_final_visual_scene = record_final_visual_scene


def record_final_visual_scene(scene_index, query, selection, *, hook_verified=False):
    entry = _run_34781319743_previous_record_final_visual_scene(
        scene_index, query, selection, hook_verified=hook_verified
    )
    group = _run_34781319743_final_result_group(query)
    entry["result_visual_contract_required"] = bool(group)
    entry["required_result_visual_group"] = group
    entry["result_visual_evidence_matched"] = (
        _run_34781319743_final_result_metadata_ok(entry, group)
    )

    SCENE_REPORT_DIR.mkdir(exist_ok=True)
    scene_path = SCENE_REPORT_DIR / f"scene_{int(scene_index):04d}.json"
    scene_path.write_text(
        json.dumps(entry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entry


_run_34781319743_previous_validate_final_visual_semantic_qa = (
    validate_final_visual_semantic_qa
)


def validate_final_visual_semantic_qa(scenes):
    expected = len(list(scenes or []))
    by_index = {item["scene_index"]: item for item in _SCENE_REPORT}
    for path in SCENE_REPORT_DIR.glob("scene_*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        by_index[int(item["scene_index"])] = item
    ordered = sorted(by_index.values(), key=lambda item: item["scene_index"])

    result_failures = []
    for item in ordered:
        group = str(item.get("required_result_visual_group") or "")
        required = bool(item.get("result_visual_contract_required")) or bool(group)
        matched = bool(item.get("result_visual_evidence_matched"))
        if required and not matched:
            item["failure_reason"] = (
                "missing_required_result_visual_evidence:"
                + (group or "unknown")
            )
            result_failures.append(item)

    if result_failures:
        seen = {item["scene_index"] for item in ordered}
        missing = [idx for idx in range(expected) if idx not in seen]
        payload = {
            "status": "FAIL",
            "scene_count": expected,
            "checked_scene_count": len(ordered),
            "missing_scene_indexes": missing,
            "failed_scenes": result_failures,
            "scenes": ordered,
        }
        REPORT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise RuntimeError(
            "FINAL_VISUAL_SEMANTIC_QA_RESULT_EVIDENCE_FAILED "
            f"failed={[item['scene_index'] for item in result_failures]}"
        )

    return _run_34781319743_previous_validate_final_visual_semantic_qa(scenes)
''' + "\n"
    FINAL_QA.write_text(final_qa, encoding="utf-8")
    print(
        "✅ Run 34781319743 Final Visual QA result-evidence defense installed"
    )
else:
    print("✅ Run 34781319743 Final Visual QA result-evidence defense already installed")
