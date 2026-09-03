"""Exact Run 33691170895 viewer-term and Scene 2 visual-subject regressions."""
from copy import deepcopy
import importlib
import runpy
import sys


AUTHORITY_SCENE2 = {
    "text": "그런데 노즐 체브론의 독특한 형상이 제트 엔진에서 어떤 역할을 할까요?",
    "visual_goal": "제트 엔진 뒤쪽 노즐의 톱니 모양 체브론을 실제로 확인",
    "keyword": "jet engine nozzle chevron",
    "role": "question",
    "scene_role": "question",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "canonical_terms": ["jet", "engine", "nozzle", "chevron"],
        "visual_discriminators": ["rear", "nozzle", "chevron", "serrated"],
    },
}


def _candidate(source_id, *, provider="pixabay", tags=""):
    return {
        "id": source_id,
        "provider": provider,
        "source_id": source_id,
        "page_url": f"https://example.invalid/{source_id}",
        "source_url": f"https://example.invalid/{source_id}",
        "download_url": f"https://example.invalid/{source_id}.mp4",
        "url": f"https://example.invalid/{source_id}.mp4",
        "tags": tags,
        "metadata_text": tags,
        "search_position": 1,
        "duration": 8.0,
    }


def _term_plan():
    return {
        "topic": "jet engine nacelle/nozzle chevrons",
        "angle": "why the serrated trailing edge exists",
        "contracts": [
            {"locked_text": "제트 엔진의 노즐 끝에 있는 체브론을 확인할 수 있습니다.", "role": "phenomenon", "required_concepts": ["jet engine nozzle chevron"]},
            {"locked_text": AUTHORITY_SCENE2["text"], "role": "question", "required_concepts": ["jet engine nozzle chevron"]},
            {"locked_text": "", "role": "mechanism_input", "required_concepts": ["flow interface"]},
            {"locked_text": "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.", "role": "reveal", "required_concepts": ["chevron mixing"]},
        ],
    }


def main():
    # Compose only established production layers needed by these two boundaries.
    for script in (
        "ci_video_provider_hotfix.py",
        "ci_visual_specificity_hotfix.py",
        "ci_query_semantic_integrity_hotfix.py",
        "ci_concrete_visual_evidence_hotfix.py",
        "ci_visible_evidence_provenance_hotfix.py",
        "ci_general_scene_visual_parity_hotfix.py",
        "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    ):
        runpy.run_path(script, run_name="__main__")

    # ci_script_v2_gunggeum... invokes #275; the new composition hook must install
    # the exact Run 33691170895 guard as well.
    runner_source = open("content/script_engine_v2_runner.py", encoding="utf-8").read()
    downloader_source = open("video/video_downloader.py", encoding="utf-8").read()
    assert "RUN_33691170895_VIEWER_TERM_CONSISTENCY_V1" in runner_source
    assert "RUN_33691170895_DISCRIMINATIVE_SUBJECT_GUARD_V1" in downloader_source

    sys.modules.pop("content.script_engine_v2_runner", None)
    runner = importlib.import_module("content.script_engine_v2_runner")

    # Exact term counterexample. Only viewer-facing narration may change.
    before = {
        "title": "test",
        "scenes": [
            {"text": "제트 엔진의 노즐 끝에 있는 체브론을 확인할 수 있습니다.", "visual_goal": "VG1 셰브론 표기 유지", "keyword": "jet engine chevron rear", "quote": "셰브론 quoted metadata"},
            {"text": AUTHORITY_SCENE2["text"], "visual_goal": "VG2", "keyword": "jet engine nozzle chevron"},
            {"text": "엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 만납니다.", "visual_goal": "VG3", "keyword": "jet engine flow interface"},
            {"text": "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.", "visual_goal": "VG4 셰브론 metadata unchanged", "keyword": "jet engine chevron mixing", "metadata": {"label": "셰브론"}},
        ],
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
    }
    metadata_snapshot = deepcopy(before)
    normalized = runner._run_33691170895_normalize_viewer_terms(deepcopy(before), _term_plan())
    assert "셰브론" not in normalized["scenes"][3]["text"]
    assert "체브론" in normalized["scenes"][0]["text"]
    assert "체브론" in normalized["scenes"][1]["text"]
    assert "체브론" in normalized["scenes"][3]["text"]
    assert normalized["scenes"][1]["text"] == AUTHORITY_SCENE2["text"]
    for i in range(len(before["scenes"])):
        assert normalized["scenes"][i]["visual_goal"] == metadata_snapshot["scenes"][i]["visual_goal"]
        assert normalized["scenes"][i]["keyword"] == metadata_snapshot["scenes"][i]["keyword"]
    assert normalized["scenes"][0]["quote"] == "셰브론 quoted metadata"
    assert normalized["scenes"][3]["metadata"] == {"label": "셰브론"}
    assert normalized["canonical_subject"] == before["canonical_subject"]
    unrelated = {"scenes": [{"text": "셰브론이라는 이름의 전혀 다른 고유명사입니다.", "visual_goal": "x", "keyword": "unrelated subject"}]}
    assert runner._run_33691170895_normalize_viewer_terms(deepcopy(unrelated), {"topic": "unrelated architecture", "contracts": []}) == unrelated
    print("RUN_33691170895_TERM_COUNTEREXAMPLE=PASS")
    print("TERM_FALSE_POSITIVES=PASS")
    print("PRIMARY_VIEWER_FACING_TERM=체브론")

    sys.modules.pop("video.video_downloader", None)
    downloader = importlib.import_module("video.video_downloader")

    bad = _candidate(284014, tags="airplane aircraft propeller flight")
    allowed, reason = downloader.run_33691170895_discriminative_subject_acceptance(bad, AUTHORITY_SCENE2)
    assert allowed is False
    assert reason == "MISSING_REQUIRED_DISCRIMINATIVE_SUBJECT_EVIDENCE"
    print("RUN_33691170895_SCENE2_VISUAL_COUNTEREXAMPLE=PASS")

    # A. same verified physical subject evidence is allowed. #268 remains the
    # production-preferred reuse path; this only verifies the acceptance policy.
    same = _candidate("still-run33691170895-scene1", provider="verified_still")
    downloader.register_visual_evidence(
        same,
        visible_components=["jet engine", "rear nozzle", "chevron", "serrated trailing edge"],
        source="verified_still_vision",
        definitive=True,
    )
    assert downloader.run_33691170895_discriminative_subject_acceptance(same, AUTHORITY_SCENE2)[0] is True
    print("SAME_VERIFIED_ASSET=PASS")

    # B. different asset is allowed when trusted evidence proves the same subject.
    different = _candidate("different-chevrons", provider="pexels")
    downloader.register_visual_evidence(
        different,
        visible_components=["aircraft", "jet engine", "rear nozzle", "chevron", "serrated edge"],
        source="existing_vision",
        definitive=True,
    )
    assert downloader.run_33691170895_discriminative_subject_acceptance(different, AUTHORITY_SCENE2)[0] is True
    print("DIFFERENT_VERIFIED_CHEVRON_ASSET=PASS")

    # C-E. Generic metadata cannot manufacture discriminative visible proof.
    generic_engine = _candidate("generic-engine", tags="aircraft jet engine nozzle")
    assert downloader.run_33691170895_discriminative_subject_acceptance(generic_engine, AUTHORITY_SCENE2)[0] is False
    print("GENERIC_JET_ENGINE_WITHOUT_CHEVRON=REJECT_PASS")

    propeller = _candidate(284014, tags="airplane propeller aircraft")
    assert downloader.run_33691170895_discriminative_subject_acceptance(propeller, AUTHORITY_SCENE2)[0] is False
    print("PROPELLER_AIRPLANE=REJECT_PASS")

    generic_airplane = _candidate("generic-airplane", tags="airplane aircraft flight")
    assert downloader.run_33691170895_discriminative_subject_acceptance(generic_airplane, AUTHORITY_SCENE2)[0] is False
    print("GENERIC_AIRPLANE=REJECT_PASS")

    # Even chevron-like provider tags are not trusted visual evidence.
    metadata_only = _candidate("metadata-only", tags="jet engine rear nozzle chevron serrated")
    assert downloader.run_33691170895_discriminative_subject_acceptance(metadata_only, AUTHORITY_SCENE2)[0] is False

    unrelated_scene = {
        "text": "비행기 창문 밖으로 구름이 보입니다.",
        "visual_goal": "비행기 창문과 구름",
        "keyword": "aircraft window clouds",
        "_canonical_visual_supply": {"canonical_subject": "aircraft passenger window"},
    }
    assert downloader.run_33691170895_discriminative_subject_acceptance(generic_airplane, unrelated_scene) == (True, "NOT_APPLICABLE")
    print("UNRELATED_SCENE_FALSE_POSITIVE=PASS")

    hotfix = open("ci_run_33691170895_term_visual_subject_hotfix.py", encoding="utf-8").read()
    for forbidden in (
        "authorize_call(", "openai.", "chat.completions", "responses.create(",
        "client.images.generate(", "V3_MAX_COST_USD", "MAX_RETRIES", "MAX_SCRIPT_API_CALLS =",
    ):
        assert forbidden not in hotfix, forbidden
    print("NEW_LLM_CALLS=0")
    print("NEW_VISION_CALLS=0")
    print("NEW_IMAGE_GENERATION_CALLS=0")
    print("API_COST_CHANGE=NONE")
    print("RETRY_CHANGE=NONE")


if __name__ == "__main__":
    main()
