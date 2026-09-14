# Shorts Bot

## Stable recovery checkpoint

This repository has a known-good recovery checkpoint for the current spoiler-video engine state.

- Backup branch: `backup/stable-spoiler-2026-09-14`
- Exact recovery SHA: `91002ebcc24a8fe201f931f95def45c0a5014bf9`
- Created: 2026-09-14
- Purpose: restore the engine if later changes cause a visual-quality or production regression.

### Recovery rule

Do **not** develop directly on or repoint the backup branch. Treat it as a frozen reference point.

If a future change degrades the engine and a rollback is explicitly required, restore `main` to the exact recovery SHA above (or compare against the backup branch first) rather than guessing which later commit caused the regression.

### What this checkpoint represents

At this checkpoint, the current spoiler-topic recovery work had restored a materially better visual result than the earlier regressed builds: the spoiler itself is visible again in the opening/mechanism portion of the video. It is still a recovery baseline, not a claim that every scene or every future topic is perfect.

Before replacing this checkpoint with a newer one, require:

1. Relevant CI/regressions are green.
2. Production runs from the intended exact `main` SHA.
3. YouTube upload remains disabled unless explicitly authorized.
4. The final MP4 is manually inspected, not accepted only from machine QA.
5. The new result is at least as good as this checkpoint with no major regression.

## Development safety notes

- Preserve the existing `main.py` / video-module structure and `create_scene` interface unless a change is explicitly approved.
- Do not lower quality gates just to make production pass.
- Do not raise cost, retry, API-call, or generation budgets without explicit approval.
- Prefer root-cause fixes plus exact counterexample regressions over topic-specific hacks.
- If production is machine-GREEN but the rendered MP4 looks wrong, treat it as a failure.
