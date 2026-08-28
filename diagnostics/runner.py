from __future__ import annotations

import sys
import traceback

from diagnostics.failure_diagnostics import (
    BoundedArtifactLog,
    TeeStream,
    capture_failure,
    initialize_progress,
    mark_success,
    scene_completed,
    scene_failed,
    scene_started,
)


def run() -> None:
    initialize_progress()
    artifact_log = BoundedArtifactLog()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = TeeStream(original_stdout, artifact_log)
    sys.stderr = TeeStream(original_stderr, artifact_log)

    try:
        import main as generator_main

        original_create_scene = generator_main.create_scene

        def observed_create_scene(idx, item, create_voice):
            scene_started(idx, item if isinstance(item, dict) else {})
            try:
                result = original_create_scene(idx, item, create_voice)
            except Exception as exc:
                scene_failed(idx, item if isinstance(item, dict) else {}, exc)
                raise
            scene_completed(idx, item if isinstance(item, dict) else {})
            return result

        generator_main.create_scene = observed_create_scene
        generator_main.main()
        mark_success()
    except Exception as exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        capture_failure(exc, tb)
        raise
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        artifact_log.close()


if __name__ == "__main__":
    run()
