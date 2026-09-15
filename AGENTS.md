# Shorts Bot Agent Operating Contract

This file is the repository-level operating contract for coding agents working in `mingi201209-star/shorts-bot`.

## Authority order

Use evidence, not guesses. For repository work, authority is:

1. Current GitHub repository state and exact commit SHA.
2. Actual GitHub Actions run/job/step logs and produced artifacts.
3. Runtime-composed code after production hotfix installers.
4. Source code and regression tests at the exact SHA being investigated.
5. Historical reports and hypotheses only as leads, never as proof.

Before modifying code, re-check the latest `main` HEAD, relevant PR head/base, CI state, and the failing run/log when applicable.

## Working method

For failures and quality regressions use this loop:

`evidence -> hypothesis -> attempt to falsify -> root cause -> minimal fix -> counterexample regression -> relevant/full regression -> PR -> exact-head CI -> approval -> protected landing -> verify main`

Do not stop at a plausible hypothesis. If evidence falsifies it, discard it and continue. Do not declare success merely because a check is green; verify that the intended code path actually ran and that the requested invariant is covered.

For complex work, maintain an execution plan following `PLANS.md`. Keep the plan current as evidence changes.

## Change discipline

- Prefer the smallest change that fixes the confirmed root cause.
- Preserve working behavior and existing interfaces.
- Do not refactor `main.py`, the video module structure, or the `create_scene` interface unless the user explicitly authorizes that boundary change.
- Do not delete working features as a shortcut.
- Do not broaden scope to unrelated failures unless they block the requested work; report unrelated failures separately.
- Convert confirmed production counterexamples into regression coverage when practical.
- Preserve source/candidate/render/publish/outcome lineage and provenance when touching media or publishing paths.

## Quality and cost invariants

Do not weaken quality gates to make CI or production pass. In particular, do not lower established semantic, subject-visibility, mobile-clarity, hook, action-match, visual-dominance, or obstruction-risk standards.

Known protected operating constants include:

- `ENABLE_HOOK_EXPERIMENT=1`
- `V3_MAX_API_CALLS=60`
- Hook threshold `7.2`
- `semantic_match >= 7`
- `subject_visibility >= 7`
- `mobile_clarity >= 8`
- `obstruction_risk <= 4`
- `HOOK_ACTION_MATCH_MIN=7.0`
- `HOOK_SUBJECT_DOMINANCE_MIN=8.0`
- `HOOK_MAX_COMPETING_SUBJECT_RISK=4.0`
- `V3_MAX_COST_USD=0.05`

Do not increase API-call or generation budgets, increase the cost ceiling, bypass validators, or replace a root-cause fix with repeated production lottery.

## First-five-seconds contract

When relevant to Shorts generation, preserve the established opening contract:

- 0-2 seconds: result/oddity assertion.
- 2-5 seconds: why/physical clue.
- No greeting, channel introduction, or preview before the hook.
- First visual directly shows the subject/phenomenon.
- Narration and visual evidence must correspond directly.
- Korean Shorts narration uses natural honorific speech; hook assertion may follow the established concise `~다` ending where required by validators.

## Visual evidence contract

Prefer visual evidence in this order:

1. Footage that directly shows the claim/action.
2. Correct subject plus a bounded explanatory overlay.
3. Deterministic explanatory visual.
4. Generated still.
5. Generic material only as a last resort, never as a substitute for a known semantic bug.

For scenes requiring observable action/change, a static image that merely contains the subject must not pass when the required action/change is absent.

## CI and landing

- Work from exact SHAs.
- After a branch head changes, treat approvals for older heads as stale.
- Required exact-head CI must be green before approval/landing.
- Use the repository's protected landing process. Do not bypass it with a direct merge API.
- After landing, verify `merged=true`, record the merge commit, and verify latest `main` is the expected commit before declaring completion.
- If landing fails, inspect the actual landing job stdout/stderr and helper code before retrying or modifying anything.

## Production and publishing boundary

Production generation, reruns, YouTube upload, OAuth live tests, public publishing, quality-threshold relaxation, and cost-cap increases are explicit boundary actions. Do not perform them unless the user's current instruction authorizes them.

Never expose secrets. Secret values are not evidence that should appear in logs, comments, reports, or committed files.

## Completion standard

A task is complete only when the requested outcome is verified at the authoritative layer. Report concrete SHAs, run/job IDs, artifacts, and invariant checks where relevant. Clearly separate confirmed facts from hypotheses or unverified assumptions.
