---
name: pr-landing
description: Safely land an already-approved pull request without calling connector merge_pull_request directly. Uses the repo-local scripts/pr_land.py helper as the only authorized landing mutation surface.
---

# PR Landing

Use this skill when a pull request is ready to land and direct connector merge mutations are forbidden by the active GitHub work rules.

## Contract

- Never call `merge_pull_request`, `enable_auto_merge`, raw merge REST endpoints, or raw GraphQL merge mutations directly from the assistant/tool layer.
- Never use admin bypass, protection bypass, force-push, or history rewrite.
- The sole authorized landing mutation surface for this repository is `.github/skills/pr-landing/scripts/pr_land.py`.
- A landing request must be bound to the exact current PR head SHA.
- Explicit approval for that PR/head must already exist before `--confirm` is used.
- Any head change invalidates the approval and requires a fresh readiness check and fresh approval.

## Normal flow

1. Read the PR and record repository, PR number, base branch, current head SHA, draft state, mergeability, required checks, and review state.
2. Require all applicable required checks to pass. Do not lower gates to make landing succeed.
3. Run the helper without `--confirm` to obtain a fail-closed plan:

```bash
python3 .github/skills/pr-landing/scripts/pr_land.py \
  --repo OWNER/REPO \
  --pr 123 \
  --head EXPECTED_HEAD_SHA \
  --mode auto \
  --method squash
```

4. If the user has explicitly approved this exact PR/head, rerun the same command with `--confirm`.
5. After the helper reports a submitted landing request, re-read the PR until GitHub reports `merged=true`. Do not claim merge success before observing it.

## Merge queue

If repository policy requires a merge queue, use `--mode queue` and omit `--method`:

```bash
python3 .github/skills/pr-landing/scripts/pr_land.py \
  --repo OWNER/REPO \
  --pr 123 \
  --head EXPECTED_HEAD_SHA \
  --mode queue \
  --confirm
```

## Failure behavior

Stop rather than bypass when any of the following is true:

- current head differs from `--head`
- PR is closed, merged, or draft
- required checks are not successful
- repository or PR cannot be read
- merge method is unsupported
- GitHub rejects auto-merge or queue enrollment

The helper intentionally uses the authenticated GitHub CLI protected path and `--match-head-commit` so a stale approval cannot land a newer head.
