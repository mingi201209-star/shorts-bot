# Production Premium Model Routing

## Contract

- Development, PR CI, regression workflows, and feature-branch dispatches keep the existing cheap model defaults.
- Premium script routing activates only during the `Shorts Generator` workflow, on `main`, for a `workflow_dispatch`, when the generator API key is present.
- Production Script V2 uses `gpt-5.6-sol` unless an explicit `V3_SCRIPT_MODEL` override is already supplied.
- Hook remains pinned to `gpt-4o-mini` so it cannot inherit the premium script model.
- Candidate and quality judge model settings are unchanged.
- `V3_MAX_API_CALLS` and `V3_MAX_COST_USD` are unchanged.

## Cost guard

`quality/budget_guard.py` registers GPT-5.6 Sol at the current standard text rates used by this change and accounts for cache-write tokens separately. Cache-write tokens are charged at 1.25x the uncached input rate.

## Promotion rule

Do not use the premium route to validate a feature branch. Validate changes with existing cheap-model CI first, merge the verified code to `main`, then production dispatch may activate the premium script route.
