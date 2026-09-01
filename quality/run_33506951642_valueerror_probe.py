from __future__ import annotations

import hashlib
import traceback
from pathlib import Path

from video import still_image_fallback as still


SCENE = {
    "role": "phenomenon",
    "scene_role": "phenomenon",
    "text": "제트 엔진의 노즐 끝에 있는 치프론을 자세히 살펴보면, 그 형상이 독특하다는 것을 알 수 있습니다.",
    "visual_goal": "치프론의 독특한 형상",
    "keyword": "jet engine nacelle nozzle chevron serrated",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron", "chevrons"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    },
}
DURATION = 6.86


def main() -> None:
    print("RUN_33506951642_PROBE_INPUT", repr(SCENE))
    print("RUN_33506951642_PROBE_DURATION", repr(DURATION), type(DURATION).__name__)
    print("RUN_33506951642_PROMPT", still._prompt(SCENE))
    print("RUN_33506951642_CONTRACT", still._canonical_still_contract(SCENE))

    try:
        image_bytes, prompt = still._generate_image(SCENE)
        print("PROBE_STAGE generation PASS", type(image_bytes).__name__, len(image_bytes))
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        temp_dir = Path("workspace/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        image_path = temp_dir / f"run33506951642_probe_{digest}.png"
        image_path.write_bytes(image_bytes)
        print("PROBE_STAGE image_write PASS", image_path, image_path.stat().st_size)

        output_path = temp_dir / "run33506951642_probe.mp4"
        still._motion_clip(image_path, output_path, DURATION)
        print("PROBE_STAGE motion_clip PASS", output_path, output_path.stat().st_size)

        verified, evidence = still._verify_motion_clip(SCENE, output_path)
        print("PROBE_STAGE validator PASS", verified, repr(evidence))
    except Exception as exc:
        print("PROBE_EXCEPTION_TYPE", type(exc).__name__)
        print("PROBE_EXCEPTION_MESSAGE", str(exc))
        print("PROBE_TRACEBACK_BEGIN")
        traceback.print_exc()
        print("PROBE_TRACEBACK_END")
        raise


if __name__ == "__main__":
    main()
