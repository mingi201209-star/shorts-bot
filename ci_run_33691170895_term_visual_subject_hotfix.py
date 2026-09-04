from pathlib import Path
import re

RUNNER_PATH = Path("content/script_engine_v2_runner.py")
DOWNLOADER_PATH = Path("video/video_downloader.py")
ENGINE_PATH = Path("video/video_engine.py")

TERM_MARKER = "# RUN_33691170895_VIEWER_TERM_CONSISTENCY_V1"
VISUAL_MARKER = "# RUN_33691170895_DISCRIMINATIVE_SUBJECT_GUARD_V1"


def _append_if_missing_or_shadowed(text, marker, block, function_names):
    marker_pos = text.rfind(marker)
    if marker_pos >= 0:
        tail = text[marker_pos:]
        # Each installed layer defines its target wrapper exactly once. A second
        # later definition means a subsequent production layer shadowed it.
        if all(tail.count(f"\ndef {name}(") <= 1 for name in function_names):
            return text, False
    return text.rstrip() + "\n\n" + block.strip() + "\n", True


def _uniquify_reapply_predecessors(text, marker, block, aliases):
    """Keep each installed wrapper's predecessor capture immutable.

    Re-applying a wrapper after later production layers must not overwrite the
    module-global predecessor alias used by an earlier wrapper. Otherwise the
    earlier wrapper can start pointing forward into the later chain and create
    a cycle. First install keeps the historical symbol names; later installs get
    deterministic install-specific aliases.
    """
    if marker not in text:
        return block
    install_index = text.count(marker) + 1
    for alias in aliases:
        block = block.replace(alias, f"{alias}_install_{install_index}")
    return block


def _patch_term_boundary():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    block = r'''
# RUN_33691170895_VIEWER_TERM_CONSISTENCY_V1
# Final deterministic normalization is intentionally limited to viewer-facing
# scene.text and to a canonical chevron physical concept that is already present
# in the Script V2 plan. visual_goal/keyword/metadata/canonical grounding remain
# byte-for-byte untouched.
_RUN_33691170895_CHEVRON_VIEWER_TERMS = ("체브론", "셰브론")


def _run_33691170895_chevron_concept_context(plan):
    if not isinstance(plan, dict):
        return False
    values = [plan.get("topic", ""), plan.get("angle", "")]
    for contract in plan.get("contracts") or []:
        if not isinstance(contract, dict):
            continue
        values.extend([
            contract.get("locked_text", ""),
            contract.get("semantic_purpose", ""),
            " ".join(str(item) for item in contract.get("required_concepts") or []),
        ])
    corpus = " ".join(str(value or "") for value in values).lower()
    return any(token in corpus for token in (
        "chevron", "chevrons", "serrated", "nacelle/nozzle",
        "체브론", "셰브론", "톱니",
    )) and any(token in corpus for token in (
        "engine", "nozzle", "nacelle", "제트 엔진", "노즐",
    ))


def _run_33691170895_normalize_viewer_terms(script, plan):
    if not isinstance(script, dict) or not _run_33691170895_chevron_concept_context(plan):
        return script
    scenes = script.get("scenes")
    if not isinstance(scenes, list):
        return script

    occurrences = []
    distinct = set()
    for scene_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        narration = str(scene.get("text") or "")
        for term in _RUN_33691170895_CHEVRON_VIEWER_TERMS:
            pos = narration.find(term)
            if pos >= 0:
                occurrences.append((scene_index, pos, term))
                distinct.add(term)
    if len(distinct) < 2 or not occurrences:
        return script

    occurrences.sort(key=lambda item: (item[0], item[1]))
    primary = occurrences[0][2]
    changed = 0
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        before = str(scene.get("text") or "")
        after = before
        for term in _RUN_33691170895_CHEVRON_VIEWER_TERMS:
            if term != primary:
                after = after.replace(term, primary)
        if after != before:
            scene["text"] = after
            changed += 1
    if changed:
        print(
            "[VIEWER_TERM_NORMALIZED] concept=jet_engine_nozzle_chevron "
            f"primary={primary} scenes={changed}"
        )
    return script


_run_33691170895_previous_contract_normalization = _normalize_script_contracts_without_api


def _normalize_script_contracts_without_api(script, plan):
    result = _run_33691170895_previous_contract_normalization(script, plan)
    return _run_33691170895_normalize_viewer_terms(result, plan)
'''
    block = _uniquify_reapply_predecessors(
        text,
        TERM_MARKER,
        block,
        ("_run_33691170895_previous_contract_normalization",),
    )
    text, changed = _append_if_missing_or_shadowed(
        text,
        TERM_MARKER,
        block,
        ("_normalize_script_contracts_without_api",),
    )
    if changed:
        RUNNER_PATH.write_text(text, encoding="utf-8")
    return changed


def _patch_visual_boundary():
    text = DOWNLOADER_PATH.read_text(encoding="utf-8")
    block = r'''
# RUN_33691170895_DISCRIMINATIVE_SUBJECT_GUARD_V1
# Reuse MISS is not a quality failure by itself. This guard applies only when a
# scene requires the discriminative jet-engine nozzle chevron subject and only
# at the general stock candidate acceptance boundary. Provider metadata never
# becomes proof. Existing definitive structured visual evidence is reused.
_RUN_33691170895_ACTIVE_SCENE = None


def _run_33691170895_scene_subject_requirement(scene):
    if not isinstance(scene, dict):
        return None
    supply = scene.get("_canonical_visual_supply")
    if not isinstance(supply, dict):
        supply = {}
    values = [
        scene.get("text", ""),
        scene.get("visual_goal", ""),
        scene.get("keyword", ""),
        supply.get("canonical_subject", ""),
        " ".join(str(item) for item in supply.get("canonical_terms") or []),
        " ".join(str(item) for item in supply.get("visual_discriminators") or []),
    ]
    corpus = " ".join(str(value or "") for value in values).lower()
    chevron = any(token in corpus for token in (
        "chevron", "chevrons", "serrated", "sawtooth", "sawtoothed",
        "체브론", "셰브론", "톱니",
    ))
    engine = any(token in corpus for token in (
        "jet engine", "engine", "제트 엔진", "엔진",
    ))
    nozzle = any(token in corpus for token in (
        "nozzle", "nacelle", "rear", "trailing edge", "노즐", "엔진 뒤",
    ))
    if not (chevron and engine and nozzle):
        return None
    return {
        "canonical_subject": "jet engine nozzle chevron",
        "required": ("engine", "nozzle", "chevron"),
    }


def _run_33691170895_definitive_visible_components(candidate):
    components = set()
    key = _visual_evidence_key(candidate)
    record = _VISUAL_EVIDENCE_REGISTRY.get(key)
    if isinstance(record, dict) and record.get("definitive"):
        components.update(
            str(item).strip().lower()
            for item in record.get("visible_components") or []
            if str(item).strip()
        )

    for field in ("vision_evidence", "visual_evidence", "verified_evidence", "subject_evidence"):
        evidence = candidate.get(field)
        if not isinstance(evidence, dict):
            continue
        source = str(evidence.get("source") or evidence.get("provenance") or "").lower()
        trusted = bool(
            evidence.get("verified") is True
            or evidence.get("definitive") is True
            or (evidence.get("pass") is True and any(token in source for token in ("vision", "verifier", "verified")))
        )
        if not trusted:
            continue
        components.update(
            str(item).strip().lower()
            for item in evidence.get("visible_components") or []
            if str(item).strip()
        )
    return components


def _run_33691170895_component_flags(components):
    normalized = " | ".join(sorted(components))
    return {
        "engine": "engine" in normalized or "jet" in normalized,
        "nozzle": any(token in normalized for token in ("nozzle", "nacelle", "rear", "trailing edge")),
        "chevron": any(token in normalized for token in ("chevron", "serrated", "sawtooth", "sawtoothed")),
    }


def run_33691170895_discriminative_subject_acceptance(candidate, scene):
    requirement = _run_33691170895_scene_subject_requirement(scene)
    if requirement is None:
        return True, "NOT_APPLICABLE"
    components = _run_33691170895_definitive_visible_components(candidate)
    flags = _run_33691170895_component_flags(components)
    missing = [name for name in requirement["required"] if not flags.get(name)]
    if missing:
        return False, "MISSING_REQUIRED_DISCRIMINATIVE_SUBJECT_EVIDENCE"
    return True, "VERIFIED_DISCRIMINATIVE_SUBJECT_EVIDENCE"


_run_33691170895_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    scene = _RUN_33691170895_ACTIVE_SCENE
    requirement = _run_33691170895_scene_subject_requirement(scene)
    if requirement is None:
        return _run_33691170895_previous_choose_best_candidate(
            candidates,
            relevant_top_n=relevant_top_n,
            historical=historical,
            subject_filter_query=subject_filter_query,
        )

    eligible = []
    for candidate in candidates or []:
        allowed, reason = run_33691170895_discriminative_subject_acceptance(candidate, scene)
        if allowed:
            eligible.append(candidate)
        else:
            print(
                "[GENERAL_VISUAL_REJECT] "
                f"candidate={candidate.get('source_id', candidate.get('id'))} "
                f"reason={reason}"
            )

    selected = _run_33691170895_previous_choose_best_candidate(
        eligible,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    if selected is None:
        return None
    allowed, reason = run_33691170895_discriminative_subject_acceptance(selected, scene)
    if not allowed:
        print(
            "[GENERAL_VISUAL_REJECT] "
            f"candidate={selected.get('source_id', selected.get('id'))} reason={reason}"
        )
        return None
    return selected


_run_33691170895_previous_fetch_video = fetch_video


def fetch_video(query_or_scene):
    global _RUN_33691170895_ACTIVE_SCENE
    if not isinstance(query_or_scene, dict):
        return _run_33691170895_previous_fetch_video(query_or_scene)
    scene = query_or_scene
    keyword = str(scene.get("keyword") or "").strip()
    previous = _RUN_33691170895_ACTIVE_SCENE
    _RUN_33691170895_ACTIVE_SCENE = scene
    try:
        return _run_33691170895_previous_fetch_video(keyword)
    finally:
        _RUN_33691170895_ACTIVE_SCENE = previous
'''
    block = _uniquify_reapply_predecessors(
        text,
        VISUAL_MARKER,
        block,
        (
            "_run_33691170895_previous_choose_best_candidate",
            "_run_33691170895_previous_fetch_video",
        ),
    )
    text, changed = _append_if_missing_or_shadowed(
        text,
        VISUAL_MARKER,
        block,
        ("choose_best_candidate", "fetch_video"),
    )
    if changed:
        DOWNLOADER_PATH.write_text(text, encoding="utf-8")

    engine = ENGINE_PATH.read_text(encoding="utf-8")
    patched, count = re.subn(r"fetch_video\(\s*keyword\s*\)", "fetch_video(item)", engine)
    if count:
        ENGINE_PATH.write_text(patched, encoding="utf-8")
        changed = True
    return changed


def main():
    term_changed = _patch_term_boundary()
    visual_changed = _patch_visual_boundary()
    if not term_changed and not visual_changed:
        print("✅ Run 33691170895 term/visual subject guard already installed")
        return
    print("✅ Run 33691170895 viewer-term consistency + discriminative visual subject guard installed")


if __name__ == "__main__":
    main()
