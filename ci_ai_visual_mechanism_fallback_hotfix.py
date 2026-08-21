from pathlib import Path

# Record the final general-scene stock decision without changing its ranking behavior.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
if "AI_VISUAL_GENERAL_SELECTION_TRACE" not in text:
    text += r'''

# AI_VISUAL_GENERAL_SELECTION_TRACE
_LAST_GENERAL_SELECTION = None
_ai_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    global _LAST_GENERAL_SELECTION
    selected = _ai_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    if selected is not None and subject_filter_query and not historical:
        _LAST_GENERAL_SELECTION = {
            "candidate": dict(selected),
            "query": str(subject_filter_query),
            "decision": visual_specificity_decision(selected, subject_filter_query),
            "visual": candidate_visible_component_evidence(selected, subject_filter_query),
        }
    else:
        _LAST_GENERAL_SELECTION = None
    return selected


def get_last_general_selection():
    if not isinstance(_LAST_GENERAL_SELECTION, dict):
        return None
    value = dict(_LAST_GENERAL_SELECTION)
    value["candidate"] = dict(value.get("candidate") or {})
    value["decision"] = dict(value.get("decision") or {})
    value["visual"] = dict(value.get("visual") or {})
    return value
'''
path.write_text(text, encoding="utf-8")

# For non-Hook concrete mechanism scenes only, allow AI after a low-quality contextual
# stock choice. The one-video generation budget is shared with the Hook path.
path = Path("video/video_engine.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    get_last_safe_reuse_offset,\n)",
    "    get_last_safe_reuse_offset,\n    get_last_general_selection,\n)",
    1,
)
old = '''        else:

            video_url = (
                fetch_video(
                    keyword
                )
            )
'''
new = '''        else:

            video_url = (
                fetch_video(
                    keyword
                )
            )

            try:
                from video.ai_visual_provider import ai_visual_eligible, generate_ai_visual
                from video.hook_visual_dominance import evaluate_hook_subject_dominance
                from video.video_downloader import register_visual_evidence, candidate_visible_component_evidence

                stock_trace = get_last_general_selection()
                stock_decision = (stock_trace or {}).get("decision") or {}
                stock_visual = (stock_trace or {}).get("visual") or {}
                stock_level = int(stock_decision.get("level", 99))
                # Component-relevant stock (levels 1-3) remains ahead of AI. Only
                # contextual/last-resort mechanism scenes may spend the shared budget.
                if ai_visual_eligible(item, hook=False) and stock_level >= 4:
                    required = list(stock_visual.get("required") or [])
                    ai_candidate = generate_ai_visual(
                        item,
                        required_components=required,
                        hook=False,
                        trigger_reason=f"mechanism_stock_level_{stock_level}",
                    )
                    if ai_candidate is not None:
                        dominance = evaluate_hook_subject_dominance(ai_candidate, item)
                        register_visual_evidence(
                            ai_candidate,
                            visible_components=dominance.get("visible_components", []),
                            source="mechanism_frame_vision_ai_generated",
                            definitive=True,
                        )
                        ai_visual = candidate_visible_component_evidence(ai_candidate, keyword)
                        verified = bool(
                            dominance.get("pass")
                            and ai_visual.get("state") == "TRUE"
                            and not dominance.get("obvious_generation_artifact", False)
                            and not dominance.get("factual_visual_contradiction", False)
                        )
                        if verified:
                            video_url = ai_candidate["url"]
                            print(
                                "[AI_VISUAL] generation_status=verified scene_id="
                                f"{idx + 1} selection_mode=AI_GENERATED_VERIFIED"
                            )
                        else:
                            print(
                                "[AI_VISUAL] generation_status=rejected scene_id="
                                f"{idx + 1} fallback=stock_contextual"
                            )
            except Exception as ai_error:
                print(
                    "[AI_VISUAL] generation_status=isolated_failure scene_id="
                    f"{idx + 1} reason={type(ai_error).__name__} fallback=stock_contextual"
                )
'''
if old not in text:
    raise RuntimeError("general scene provider block not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("✅ Concrete mechanism AI visual fallback wired with shared bounded budget")
