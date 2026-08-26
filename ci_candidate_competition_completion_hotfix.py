"""Wire Visual Quality V1 competition to already-fetched valid candidates only."""
from pathlib import Path

# Scene role is carried inside each create_scene worker; no signature/provider call changes.
path = Path("video/video_engine.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_QUALITY_CANDIDATE_ROLE_V1"
if marker not in text:
    anchor = '''        # ====================================================
        # 3. Pexels 후보 검색 + 선택
        # ====================================================
'''
    block = '''        # VISUAL_QUALITY_CANDIDATE_ROLE_V1
        # Worker-local role hint only; candidate generation/search is unchanged.
        from quality.final_visual_director import infer_scene_role as _vq_infer_scene_role
        os.environ["VQ_SCENE_ROLE"] = _vq_infer_scene_role(item, idx, 999)

''' + anchor
    if anchor not in text:
        raise RuntimeError("candidate role anchor missing")
    text = text.replace(anchor, block, 1)
    path.write_text(text, encoding="utf-8")

path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
if "VISUAL_QUALITY_CANDIDATE_COMPETITION_V1" not in text:
    text += r'''

# VISUAL_QUALITY_CANDIDATE_COMPETITION_V1
# Wrap the final existing selector: no search/generation is performed here.
_vq_previous_choose_best_candidate = choose_best_candidate


def _vq_competition_scores(candidate, query, role):
    tier, _ = general_scene_unknown_safe_tier(candidate, query)
    compatibility = candidate_anchor_compatibility(candidate, query)
    decision = visual_specificity_decision(candidate, query)
    matched = int(compatibility.get("matched", 0) or 0)
    total = int(compatibility.get("total", 0) or 0)
    semantic = 9.0 if total > 0 and matched >= total else (7.5 if matched > 0 else 0.0)
    explanatory = max(0.0, 10.0 - 1.5 * float(tier))
    if int(decision.get("specific_hits", 0) or 0) > 0:
        explanatory = min(10.0, explanatory + 1.0)
    return {
        "semantic_match": semantic,
        "explanatory_power": explanatory,
        "subject_prominence": 8.0 if matched else 6.0,
        "mobile_clarity": 8.0,
        "hook_visual_strength": 8.0,
        "payoff_visual_strength": 7.0,
        "artifact_risk": 1.0,
        "obstruction_risk": 1.0,
    }


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    role = str(os.environ.get("VQ_SCENE_ROLE") or "setup").lower()
    competition_roles = {"hook", "reveal", "cause", "mechanism", "solution", "result", "conclusion"}
    if role not in competition_roles or historical or not subject_filter_query or len(candidates or []) < 2:
        return _vq_previous_choose_best_candidate(candidates, relevant_top_n=relevant_top_n, historical=historical, subject_filter_query=subject_filter_query)

    # Preserve every existing eligibility/hard gate. Only candidates in tiers 1-4
    # can enter V1; cross-domain/abstract tier 5+ never competes.
    valid = []
    for candidate in list(candidates or []):
        if _candidate_is_used(candidate):
            continue
        tier, _ = general_scene_unknown_safe_tier(candidate, subject_filter_query)
        if tier <= 4:
            valid.append((tier, int(candidate.get("search_position", 9999)), candidate))
    valid.sort(key=lambda item: (item[0], item[1]))
    supplied = [item[2] for item in valid[:2]]
    if len(supplied) < 2:
        return _vq_previous_choose_best_candidate(candidates, relevant_top_n=relevant_top_n, historical=historical, subject_filter_query=subject_filter_query)

    from quality.final_visual_director import select_best_valid_candidate
    enriched = []
    for candidate in supplied:
        copy = dict(candidate)
        copy["scores"] = _vq_competition_scores(candidate, subject_filter_query, role)
        enriched.append(copy)
    selected = select_best_valid_candidate(enriched, role, max_candidates=2)
    if selected is None:
        return _vq_previous_choose_best_candidate(candidates, relevant_top_n=relevant_top_n, historical=historical, subject_filter_query=subject_filter_query)
    selected_key = _candidate_unique_key(selected)
    for original in supplied:
        if _candidate_unique_key(original) == selected_key:
            print(f"[VisualQuality] competition role={role} selected={selected.get('source_id', selected.get('id'))} supplied=2")
            # Re-enter the complete pre-competition selector stack for the
            # single winner.  Besides preserving every existing hard gate,
            # this lets the final semantic-QA wrapper record the winner's
            # exact lineage instead of retaining a previously rejected search
            # candidate (production Run 33000942031, Scene 1).
            return _vq_previous_choose_best_candidate(
                [original],
                relevant_top_n=relevant_top_n,
                historical=historical,
                subject_filter_query=subject_filter_query,
            )
    return _vq_previous_choose_best_candidate(candidates, relevant_top_n=relevant_top_n, historical=historical, subject_filter_query=subject_filter_query)
'''
    path.write_text(text, encoding="utf-8")

print("VISUAL_QUALITY_CANDIDATE_COMPETITION_V1 installed")
