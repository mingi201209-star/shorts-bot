# Shorts Bot Agent Operating Contract

This file is the repository-level operating constitution for every coding agent working in
`mingi201209-star/shorts-bot` — Codex, Claude Code, or any other agent. It is not a
model-specific prompt. Rules are written as MUST / MUST NOT so they survive being read by a
different model, a different session, or an agent with no memory of past conversations.

Two companion sources this file depends on:

- **`operations/`** — the Operations Graph: structured, evidence-backed records of past
  incidents (failure → root cause → fix → regression → PR → verification). Query it with
  `python operations/query.py` before re-diagnosing a failure signature you haven't seen
  before in this session. See `operations/README.md`.
- **Canonical production configuration** — the actual current numeric thresholds and budgets.
  This file intentionally does not hardcode most of them (see Quality and Budget below); go
  read the source.

## Authority

MUST, before modifying code or claiming a fact about the repository's current state:

- Fetch and confirm the current `main` HEAD SHA.
- Confirm the target PR/branch head SHA and its current CI/mergeable state.
- Read the actual current source at that SHA — not a remembered summary, not an older SHA,
  not this file's own prose.
- Treat GitHub Actions run/job/step logs and produced artifacts as higher authority than any
  agent's prior summary of them.

MUST NOT:

- Treat a past chat message, an old SHA, or a prior agent's summary as a current fact.
- Assume a constant, threshold, or behavior is still what an earlier PR description said —
  values in this codebase are frequently rewritten at CI runtime by `ci_*_hotfix.py` scripts
  (see Quality). Re-read the composed value, don't recall it.

Authority order, highest first: (1) current GitHub repository state at an exact SHA, (2) actual
run/job logs and artifacts, (3) runtime-composed code after the production hotfix chain has
been applied, (4) source and regression tests at the exact SHA under investigation, (5)
historical reports/hypotheses — leads only, never proof.

## Minimal Change

MUST follow this loop for any failure or quality regression:

`evidence -> hypothesis -> attempt to falsify -> root cause -> minimal fix -> counterexample regression -> related regression -> PR -> exact-head CI -> approval -> protected landing -> verify main`

MUST discard a hypothesis the evidence falsifies and keep going — do not stop at "plausible."
MUST verify the intended code path actually executed; a green check is not proof by itself.
MUST prefer the smallest change that fixes the confirmed root cause.
MUST NOT perform a large refactor without evidence that the smaller fix is insufficient.
MUST NOT delete a working feature as a shortcut to a passing check.
MUST NOT broaden scope to unrelated failures that don't block the current work — report them
separately instead (an Operations Graph incident is a good place for that report).

## Engine Contracts

MUST NOT change any of the following without the user's explicit authorization for that exact
boundary:

- `main.py`'s top-level structure.
- The video module architecture (`video/*.py` responsibilities and boundaries).
- The `create_scene` interface.

These are stable interfaces many other files depend on; changing them silently has repeatedly
produced multi-file blast radius in this repo's history (see `operations/` for examples).

## Quality

MUST NOT lower an established quality gate — semantic match, subject visibility, mobile
clarity, Hook floors, action-match, visual-dominance, obstruction-risk, or any other existing
acceptance threshold — to make a CI check or a production run pass.

MUST NOT hardcode a specific threshold number in a prompt, a memory note, or this file as if it
were permanently fixed. This codebase composes its real runtime values from checked-in source
**plus** ~48 `ci_*_hotfix.py` scripts applied in a fixed order (see
`quality/production_hotfix_chain.py`), and several floors are domain-conditional, not a single
flat number (for example `quality/final_visual_director.py`'s `semantic_match` floor varies by
domain). A number copied into a doc today has already gone stale at least three times in this
repo's history — three independent regression assertions expected `MAX_TOPIC_REGENERATIONS = 6`
long after production had moved to `19` (see `operations/incidents/`).

**Canonical production configuration is authority, not this file.** Before asserting what a
threshold currently is, read it from its real source:

- Hook dominance floors: `video/hook_visual_dominance.py` (`HOOK_SUBJECT_DOMINANCE_MIN`,
  `HOOK_ACTION_MATCH_MIN`, `HOOK_MAX_COMPETING_SUBJECT_RISK`) — stable, checked-in constants.
- Visual/semantic floors: `quality/final_visual_director.py` — domain-conditional, read the
  actual dict for the domain in question.
- API/cost/experiment toggles (`V3_MAX_API_CALLS`, `V3_MAX_COST_USD`,
  `ENABLE_HOOK_EXPERIMENT`, `MAX_TOPIC_REGENERATIONS`, ...): not statically defined — they are
  set by workflow YAML env vars and/or rewritten by `ci_hotfix.py`/other hotfixes at CI runtime.
  Apply the production hotfix chain (`python quality/apply_production_hotfix_chain.py` in a
  disposable worktree) and read the composed file, or read the exact `grep`/assertion the
  relevant CI job itself uses as its live source of truth.

MUST NOT bypass a validator or replace a root-cause fix with repeated "production lottery"
reruns hoping a stochastic pass occurs.

## Budget

MUST NOT increase, in production configuration or CI:

- API call caps (e.g. `V3_MAX_API_CALLS`).
- Cost ceilings (e.g. `V3_MAX_COST_USD`).
- Any bounded retry/regeneration count into unbounded retry.

Widening a budget to make a failure go away is a boundary action — it needs the user's current,
explicit authorization, not an agent's own judgment call under CI pressure.

## Regression

MUST add a regression test that reproduces the exact failure being fixed (a counterexample)
whenever practical, so the same bug re-triggers a red check if it ever comes back.
MUST NOT delete, skip, or weaken an existing test to force green.
MUST convert a confirmed production counterexample into permanent regression coverage rather
than leaving it as a one-off manual verification.
SHOULD record the incident in `operations/` once fixed and verified (see `operations/README.md`)
so a future agent can find it by failure signature or affected file instead of re-diagnosing
from scratch.

## External Provider

MUST distinguish provider **availability** failures (HTTP 429, 5xx, timeout, network error) from
**semantic/query quality** failures (zero results, bad match). They are not the same failure
class and must not share a recovery path.
MUST NOT retry an unavailable provider with different queries — that is a semantic-failure
recovery strategy misapplied to an availability failure, and it makes an outage worse.
MUST bound recovery: each configured provider attempted at most once per fetch pass, no
provider retried within that pass.
MUST fail closed when every configured provider fails — return nothing / raise explicitly.
MUST NOT substitute an unrelated candidate just to "succeed with some video" when the correct
one is unavailable; a silently-wrong result is worse than an explicit failure.

## Secrets

MUST NOT print, log, commit, or otherwise surface a secret value.
MUST NOT request more credential scope or capability than the current task needs.
MUST treat "the log contains what looks like a key" as an incident to redact, not evidence to
quote.

## YouTube

Current default policy: automatic YouTube upload is OFF (`youtube_upload=false`) until the user
explicitly re-enables it for a specific task.
MUST NOT enable upload, touch upload-related secrets, or run a live OAuth/publish flow without
that explicit, current authorization.

## Jev

MUST verify Jev's actual current state before writing anything about it — do not assume this
section's snapshot is still accurate. As of the last verification (PR #435, `experiment/jev-shadow-v1`,
draft, **not merged to `main`**), Jev is a strictly shadow, non-authoritative evaluator: it may
log a parallel opinion but MUST NOT gate, block, or influence any production decision, and its
own PR states production budgets/thresholds/interfaces are unchanged by it.
MUST NOT promote a shadow experiment (Jev or any other) to production decision authority based
on its own logged output alone — that requires the user's explicit authorization plus comparison
evidence against the existing authoritative gate.
MUST NOT describe an unmerged experimental branch's behavior as a current production invariant.

## Landing

MUST NOT call a merge API directly. Use this repository's protected landing process.
MUST treat an approval given for one head SHA as stale the moment that branch's head changes;
re-request approval on the new head instead of reusing an old one.
MUST require green CI on the exact current head before requesting or acting on approval.
MUST, when a human approval token is required (e.g. `LAND-APPROVED:<sha>`), stop and wait at
that exact point rather than proceeding without it.
MUST, after landing, verify `merged=true`, record the merge commit, and confirm `main`'s new
HEAD is the expected commit before declaring the task complete.
MUST, if landing fails, inspect the actual landing job's stdout/stderr before retrying anything.

## Production and Publishing Boundary

The following are explicit boundary actions requiring the user's current, explicit
authorization — never taken on an agent's own initiative: production generation/reruns, YouTube
upload, OAuth live tests, public publishing, quality-threshold relaxation, and cost/API-cap
increases.

## Completion Standard

A task is complete only when its outcome is verified at the authoritative layer (exact SHA, real
CI run, real artifact) — not merely "a check went green." Report concrete SHAs, run/job IDs, and
artifacts. Clearly separate confirmed fact from hypothesis or unverified assumption.

---

**The core principle underneath every section above:** long conversation context is not memory,
and an agent's own summary is not authority. Evidence is authority. Rules that must hold live
here, in `AGENTS.md`. Verified facts about what actually happened live in `operations/`.
Enforcement lives in deterministic CI — not in a model remembering to follow a rule.
