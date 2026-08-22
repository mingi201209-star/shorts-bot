# Repo-local PR landing fallback

This directory exists for environments where direct connector merge mutations are visible but forbidden by the active GitHub work rules.

Use `SKILL.md` as the operating contract and `scripts/pr_land.py` as the sole landing helper.

The helper is intentionally fail-closed:

- exact expected head SHA is mandatory
- draft/closed/stale-head PRs are rejected
- failing or pending checks are rejected
- dangerous merge states are rejected
- the PR is re-read immediately before mutation
- `--admin` and protection-bypass behavior are not implemented
- `gh pr merge --match-head-commit` is used so GitHub rejects a moved head

A dry run (no `--confirm`) prints a landing plan and performs no mutation.
