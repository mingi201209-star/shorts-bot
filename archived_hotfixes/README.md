# Archived hotfixes

Files here are `ci_*.py` scripts that used to live at the repo root alongside
the active production hotfixes, but are confirmed **not reachable** by
production. They are kept (not `git rm`'d) so their history and intent stay
visible, per Publish Engine Stabilization V1's retirement policy: "retire
(not silently delete — move to an archived/ location or clearly mark) the
now-redundant hotfix scripts."

## Reachability check performed before archiving

A file only lands here after confirming it is **not** reached by any of the
mechanisms this codebase actually uses to compose the production hotfix
chain, checked against `quality/production_hotfix_chain.py` (the single
source of truth, see Publish Engine Stabilization V1 Phase 0):

- Direct membership in `PRODUCTION_HOTFIX_CHAIN`.
- `from ci_X_hotfix import ...` / plain `import ci_X_hotfix` inside a
  chain-reachable hotfix (several hotfixes chain-apply others this way).
- `runpy.run_path("ci_X_hotfix.py", ...)` inside a chain-reachable hotfix.
- `exec(compile(Path("ci_X_hotfix.py").read_text(), ...))` inside a
  chain-reachable hotfix.
- Direct invocation from any `.github/workflows/*.yml` step (several
  per-topic regression workflows apply one specific hotfix standalone,
  outside `main.yml`'s chain, on purpose).
- Reference from any `quality/*_test.py` regression test or any other
  source file anywhere in the repo (a full-repo, all-file-type grep, not
  just `.py`/`.yml`).

## Files

### `ci_script_causal_retry_grounding_hotfix.py`

A 7-line probe, not a hotfix: it reads `ci_script_validation_recovery_hotfix.py`
(which *is* in the production chain) and asserts a few marker strings are
present in it. That exact check now lives properly in a real, CI-wired
regression test — `quality/script_causal_retry_grounding_regression_test.py`,
run by `.github/workflows/script_causal_retry_grounding_regression.yml` —
which checks the same markers plus several more. This file was fully
superseded and had zero references anywhere in the repo.

### `ci_script_closing_lock_hotfix.py`

Patches `content/script_generator.py` to add a `_script_closing_lock_apply`
call mirroring an `_script_opening_lock_apply` call it expects to already be
present. Neither `SCRIPT_OPENING_LOCK_V1` nor `SCRIPT_CLOSING_LOCK_V1`, nor
any `_script_opening_lock_apply` call, exist anywhere in the current
`content/script_generator.py` — the anchor text this hotfix requires to
apply itself is gone, so running it today would raise
`RuntimeError: script closing lock validation marker mismatch`. It was never
part of `PRODUCTION_HOTFIX_CHAIN` and had zero references anywhere else in
the repo, so this was never shipped and would not run successfully if it
were added to the chain as-is.
