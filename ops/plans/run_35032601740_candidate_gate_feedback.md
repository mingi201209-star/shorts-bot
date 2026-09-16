# Run 35032601740 — Automatic Candidate Gate Feedback Recovery

### Goal
A new production run from current main must stop repeating the same broad/weak automatic Candidate classes without downstream feedback, while preserving all Candidate Gate, FACT, quality, retry, API, and cost boundaries.

### Boundaries
- Preserve `main.py` architecture, video module structure, and `create_scene`.
- Do not lower Candidate Gate or any downstream quality threshold.
- Do not increase Candidate attempts, API-call ceiling, generation budget, or cost ceiling.
- Do not invent deterministic topic answers or bypass grounding/fact checks.
- Production validation uses `youtube_upload=false`.

### Authority / starting state
- main: `1f72bd6e0677144c44b0dd13930bd5e3c8f851b8`
- open PRs before work: 0
- failing production run: `35032601740`
- failing job: `104594321067`
- first failing step: `Generate Shorts`
- production hotfix composition and pre-generation regressions passed.

### Evidence collected
- Seven existing automatic Candidate attempts were available.
- Explorer repeatedly returned `SELECTED`, so zero-supply recovery was not the relevant path.
- Candidate Gate rejected selected topics for broad/generic framing, predictable payoff, weak causal specificity, or unsupported/fabricated linkage.
- Existing automatic Gate-feedback propagation in `ci_aviation_context_signature_compat_hotfix.py` was restricted to `SHORTS_CANDIDATE_SCOPE=aviation`.
- The failing production used default automatic scope, so downstream Gate reasons were not propagated to later Explorer attempts.
- Existing grounded recovery correctly refuses to revive hard novelty/grounding failures; weakening it would bypass an authoritative rejection boundary.

### Hypotheses
1. Candidate Gate is too strict. Falsified: its rejections match the channel's existing specificity/non-obviousness/fact-safety contract, including a fabricated final candidate.
2. Supply recovery is broken. Falsified: that path only applies to Explorer `REGENERATE`/zero usable supply, while this run repeatedly returned `SELECTED` candidates.
3. Default automatic attempts lack Gate feedback. Confirmed by the scope guard in the installed compatibility hotfix and the seven-attempt production trace.

### Root cause
The existing downstream Candidate Gate feedback loop was scoped only to aviation. Default automatic discovery therefore received rejected topic names but not the actual downstream Gate reasons, allowing later attempts to repeat the same classes of broadness, predictable payoff, causal weakness, and unsupported claims.

### Minimal change
Generalize the already-existing automatic Gate-feedback propagation to every non-fixed automatic scope. Preserve fixed-topic feedback behavior. Normalize and bound each reason, attach it to the existing `rejected_topics` execution context, and explicitly instruct the next attempt to choose a materially different concrete subject/detail while preserving Gate and anti-fabrication rules.

### Verification
- [ ] Focused counterexample regression.
- [ ] Production hotfix composition gate.
- [ ] Existing Candidate/FACT/Hook/visual regressions.
- [ ] Exact-head PR CI.
- [ ] Diff/blast-radius review.
- [ ] Protected landing.
- [ ] Verify latest main.
- [ ] NEW production with `youtube_upload=false`.
- [ ] Final MP4 + Visual Semantic QA + Director QA + diversity preflight if production reaches render.

### Progress log
1. Reconfirmed main SHA and open PR count.
2. Re-read Run 35032601740 job logs.
3. Compared zero-supply recovery, grounded recovery, fixed-topic feedback, and automatic aviation feedback paths.
4. Root cause narrowed to aviation-only condition on an otherwise appropriate feedback mechanism.
5. Implemented scope-generalized feedback and focused regression on a current-main branch.

### Outcome
PENDING exact-head CI, protected landing, and new production verification.
