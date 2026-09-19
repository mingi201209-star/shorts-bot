from __future__ import annotations

import sys
import traceback
import builtins

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
from quality.production_execution_trace import (
    input_fingerprint,
    record_event,
    snapshot_runtime_state,
    write_summary,
)


def run() -> None:
    initialize_progress()
    record_event(
        "generator_runner_start",
        input=input_fingerprint(),
        runtime_state_before=snapshot_runtime_state(),
    )
    artifact_log = BoundedArtifactLog()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = TeeStream(original_stdout, artifact_log)
    sys.stderr = TeeStream(original_stderr, artifact_log)

    try:
        before_modules = set(sys.modules)
        import_events = []
        original_import = builtins.__import__

        def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
            module = original_import(name, globals, locals, fromlist, level)
            root_name = str(name or "").split(".", 1)[0]
            if root_name in {
                "analytics",
                "content",
                "diagnostics",
                "integrations",
                "quality",
                "video",
                "main",
                "config",
            }:
                import_events.append(
                    {
                        "name": name,
                        "fromlist": list(fromlist or ()),
                        "level": level,
                    }
                )
            return module

        builtins.__import__ = traced_import
        try:
            import main as generator_main
        finally:
            builtins.__import__ = original_import

        after_modules = set(sys.modules)
        record_event(
            "generator_import_complete",
            imported_modules=sorted(after_modules - before_modules),
            import_call_count=len(import_events),
            import_calls=import_events[:500],
        )

        original_create_scene = generator_main.create_scene

        def observed_create_scene(idx, item, create_voice):
            record_event(
                "scene_start",
                scene_index=idx,
                scene=item if isinstance(item, dict) else {},
                runtime_state=snapshot_runtime_state(),
            )
            scene_started(idx, item if isinstance(item, dict) else {})
            try:
                result = original_create_scene(idx, item, create_voice)
            except Exception as exc:
                scene_failed(idx, item if isinstance(item, dict) else {}, exc)
                record_event(
                    "scene_failed",
                    scene_index=idx,
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    runtime_state=snapshot_runtime_state(),
                )
                raise
            scene_completed(idx, item if isinstance(item, dict) else {})
            record_event(
                "scene_complete",
                scene_index=idx,
                runtime_state=snapshot_runtime_state(),
            )
            return result

        generator_main.create_scene = observed_create_scene
        generator_main.main()
        mark_success()
        record_event(
            "generator_success",
            runtime_state_after=snapshot_runtime_state(),
        )
        write_summary("success")
    except Exception as exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        capture_failure(exc, tb)
        record_event(
            "generator_failure",
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            runtime_state_after=snapshot_runtime_state(),
        )
        write_summary(
            "failed",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
        raise
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        artifact_log.close()


if __name__ == "__main__":
    run()
