import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video import video_downloader as vd


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def candidate(provider, source_id, search_position=1):
    return {
        "id": source_id,
        "provider": provider,
        "source_id": source_id,
        "provider_key": f"{provider}:{source_id}",
        "url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "download_url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "page_url": f"https://example.test/{provider}/{source_id}",
        "metadata_text": "aircraft wing winglet",
        "tags": "aircraft wing winglet",
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
        "search_position": search_position,
    }


def test_cross_process_claim_survives_memory_reset():
    # Production counterexample: Run 32819796413 reused Pixabay 6522 for
    # Scenes 0-2 because each Scene worker had its own USED_VIDEO_IDS set.
    repeated = candidate("pixabay", 6522, 1)
    alternate = candidate("pixabay", 14252, 2)

    old_claim_dir = os.environ.get("VIDEO_SOURCE_CLAIM_DIR")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["VIDEO_SOURCE_CLAIM_DIR"] = temp_dir
            vd.USED_VIDEO_IDS.clear()

            check("A first worker claims production source 6522", vd._mark_candidate_used(repeated) is True)

            # Simulate a fresh Scene worker: process-local memory is empty but the
            # run-scoped filesystem claim must remain authoritative.
            vd.USED_VIDEO_IDS.clear()
            check("B second worker sees persisted source claim", vd._candidate_is_used(repeated) is True)
            check("C duplicate atomic claim is rejected", vd._mark_candidate_used(repeated) is False)

            selected = vd.choose_best_candidate(
                [repeated, alternate],
                relevant_top_n=2,
                historical=False,
                subject_filter_query="aircraft wing winglet",
            )
            check(
                "D claimed source is excluded and alternate remains selectable",
                selected is not None and selected.get("source_id") == 14252,
            )
    finally:
        vd.USED_VIDEO_IDS.clear()
        if old_claim_dir is None:
            os.environ.pop("VIDEO_SOURCE_CLAIM_DIR", None)
        else:
            os.environ["VIDEO_SOURCE_CLAIM_DIR"] = old_claim_dir


def main():
    test_cross_process_claim_survives_memory_reset()
    print("✅ CROSS-PROCESS VIDEO DEDUPE REGRESSION PASS")


if __name__ == "__main__":
    main()
