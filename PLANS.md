# Execution Plans for Shorts Bot

Use an execution plan for work that is multi-step, crosses subsystems, investigates an uncertain root cause, changes production composition, or is likely to require more than one edit/test cycle.

The plan is a living engineering record, not a promise. Update it when evidence disproves an assumption.

## Plan template

### Goal
State the observable end state. Prefer a verifiable result over an implementation description.

### Boundaries
List what must not change. Include interface, quality, cost, production, publishing, and scope constraints relevant to the task.

### Authority / starting state
Record:

- latest `main` SHA
- relevant PR number/head/base
- authoritative failing run/job/artifact IDs
- exact first failing step or observed human-quality defect

Do not copy stale values forward without re-checking GitHub.

### Evidence collected
Record facts from logs, artifacts, runtime-composed code, source, and tests. Keep facts separate from hypotheses.

### Hypotheses
For each hypothesis record:

- why it could explain the evidence
- what observation would falsify it
- result of that falsification attempt

Discard falsified hypotheses instead of patching them.

### Root cause
Only fill this section when the evidence is sufficient to explain the observed failure path. If not confirmed, write `UNCONFIRMED` and continue investigation.

### Minimal change
Describe the smallest proposed change and why it addresses the confirmed cause without relaxing existing invariants.

### Verification
Use a checklist appropriate to the change. Typical order:

- focused counterexample regression
- neighboring regression(s)
- production-hotfix composition test when runtime installers are involved
- relevant full regression suite
- exact-head GitHub CI
- PR diff review for blast radius
- protected landing
- post-merge latest-main verification

A green test is not enough if it did not exercise the changed path. Verify execution/path coverage where material.

### Progress log
Keep short timestamped or ordered notes for important discoveries, rejected hypotheses, commits, CI results, and head changes. When the PR head changes, record that prior exact-head approvals are stale.

### Outcome
Record the final merge SHA/main SHA and what was proven. State explicitly which boundary actions were not performed (for example production generation or YouTube upload) when those were excluded.

## Default investigation rules

1. Read before writing.
2. Reproduce or inspect the authoritative failure before editing when possible.
3. Prefer raw job/step logs over summaries for deterministic CI failures.
4. Inspect runtime-composed code when hotfix installers mutate production behavior.
5. Do not infer absence from a truncated log or partial artifact.
6. Do not repair an unrelated failure just because it is nearby.
7. Add a regression from the real counterexample when practical.
8. Keep changes minimal and reversible.
9. Never weaken a quality gate, increase the cost/API budget, or bypass protected landing to obtain a green result.
10. Continue through verification and landing without unnecessary user interruptions when the next action is within the authorized boundary.

## Repository-specific protected invariants

All plans inherit `AGENTS.md`. In particular, preserve `main.py`/video architecture and `create_scene`, established quality thresholds, API/cost ceilings, source lineage, and explicit production/publishing boundaries.
