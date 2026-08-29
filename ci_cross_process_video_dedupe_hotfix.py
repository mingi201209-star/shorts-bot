from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} marker mismatch count={count}")
    return text.replace(old, new, 1)

path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
old_helpers = '''def _candidate_is_used(candidate):
    key = _candidate_unique_key(candidate)
    if key in USED_VIDEO_IDS:
        return True
    return (
        str(candidate.get("provider") or "pexels") == "pexels"
        and candidate.get("id") in USED_VIDEO_IDS
    )


def _mark_candidate_used(candidate):
    USED_VIDEO_IDS.add(_candidate_unique_key(candidate))
    if str(candidate.get("provider") or "pexels") == "pexels":
        video_id = candidate.get("id")
        if video_id is not None:
            USED_VIDEO_IDS.add(video_id)
'''
new_helpers = '''def _video_source_claim_root():
    override = str(os.environ.get("VIDEO_SOURCE_CLAIM_DIR") or "").strip()
    root = override or os.path.join(os.getcwd(), ".video_source_claims", str(os.environ.get("GITHUB_RUN_ID") or "local"))
    os.makedirs(root, exist_ok=True)
    return root


def _candidate_claim_path(candidate):
    key = str(_candidate_unique_key(candidate) or "unknown")
    safe_key = re.sub(r"[^a-zA-Z0-9_.-]+", "_", key).strip("._") or "unknown"
    return os.path.join(_video_source_claim_root(), safe_key + ".claim")


def _candidate_is_used(candidate):
    key = _candidate_unique_key(candidate)
    if key in USED_VIDEO_IDS:
        return True
    if str(candidate.get("provider") or "pexels") == "pexels" and candidate.get("id") in USED_VIDEO_IDS:
        return True
    return os.path.exists(_candidate_claim_path(candidate))


def _mark_candidate_used(candidate):
    key = _candidate_unique_key(candidate)
    if _candidate_is_used(candidate):
        return False
    claim_path = _candidate_claim_path(candidate)
    try:
        fd = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(key))
    USED_VIDEO_IDS.add(key)
    if str(candidate.get("provider") or "pexels") == "pexels":
        video_id = candidate.get("id")
        if video_id is not None:
            USED_VIDEO_IDS.add(video_id)
    return True
'''
text = replace_once(text, old_helpers, new_helpers, "cross-process provider source claims")
text = replace_once(text, '''        video_id = best.get("id")
        _mark_candidate_used(best)

        print(
            "🎥 Pexels 검색 후보 "
''', '''        video_id = best.get("id")
        if not _mark_candidate_used(best):
            print("[VIDEO_SOURCE_CLAIM_CONFLICT] " f"provider=pexels source_id={video_id} scene=general")
            continue

        print(
            "🎥 Pexels 검색 후보 "
''', "legacy pexels atomic claim")
text = replace_once(text, '''        if not best:
            continue
        _mark_candidate_used(best)
        provider = str(best.get("provider") or "pexels")
        source_id = best.get("source_id", best.get("id"))
        print(f"[VIDEO_SELECTED] provider={provider} source_id={source_id} scene=general")
        return best["url"]
''', '''        if not best:
            continue
        provider = str(best.get("provider") or "pexels")
        source_id = best.get("source_id", best.get("id"))
        if not _mark_candidate_used(best):
            print("[VIDEO_SOURCE_CLAIM_CONFLICT] " f"provider={provider} source_id={source_id} scene=general")
            continue
        print(f"[VIDEO_SELECTED] provider={provider} source_id={source_id} scene=general")
        return best["url"]
''', "unified provider atomic claim")
final_binding_marker = "# CROSS_PROCESS_VIDEO_DEDUPE_FINAL_BINDING_V2"
if final_binding_marker not in text:
    text = text.rstrip() + "\n\n" + final_binding_marker + "\n" + new_helpers + "\n"
path.write_text(text, encoding="utf-8")
print("✅ Cross-process video source dedupe hotfix applied")

main_text = Path("main.py").read_text(encoding="utf-8")
if "FINAL_VISUAL_SEMANTIC_QA_V1" in main_text:
    import ci_visual_quality_v1_hotfix  # noqa: F401,E402
    import ci_subtitle_director_completion_hotfix  # noqa: F401,E402
    import ci_candidate_competition_completion_hotfix  # noqa: F401,E402
    import ci_visual_quality_v1_completion_hotfix  # noqa: F401,E402
    import ci_visual_explanation_retrieval_v1_hotfix  # noqa: F401,E402
    import ci_visual_diversity_preflight_hotfix  # noqa: F401,E402
    # Apply after all visual completion installers so the subject-anchor contract
    # is the final retrieval/semantic boundary in production composition.
    import ci_visual_subject_anchor_contract_v1_hotfix  # noqa: F401,E402
