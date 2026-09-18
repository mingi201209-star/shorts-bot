### Goal

The fixed aircraft-window topic reaches all five scenes without exhausting the
three-transform deterministic explanation ceiling, while preserving distinct
and verified visual evidence for the Scene-2 shape question.

### Boundaries

- Keep `main.py`, video-module structure, and `create_scene` unchanged.
- Do not change quality thresholds, retry/API/cost ceilings, still-generation
  ceiling, or `MAX_EXPLANATION_TRANSFORMS_PER_VIDEO=3`.
- Do not change YouTube upload/publish behavior.
- Keep the three grounded causal claims and their deterministic presentations.

### Authority / starting state

- `main`: `a05a74a56dcf2f568b211b15ee062d6221835016` (merged PR #407).
- Failing production run: `35314305498`, job `105502579251`, step
  `Run Shorts Generator V3.2`.
- First fatal error: Scene 5 `squarish_window_fatigue_rupture` routed to
  `AIRCRAFT_WINDOW_STRESS_V1`, then
  `[VisualExplanation] status=budget_exhausted count=3`.

### Evidence collected

- PR #407 worked: Candidate/Script completed and rendering reached Scene 5.
- Scene 1 consumed verified-still slot 1.
- Scene 2 skipped still supply and consumed deterministic explanation 1 for a
  neutral shape-comparison question.
- Scenes 3 and 4 consumed deterministic explanations 2 and 3.
- Scene 5 correctly rejected raw stills because fatigue/rupture action was not
  visible, but no deterministic explanation slot remained.
- The protected runtime already permits two still generations and three
  explanation transforms; the failure came from routing the neutral question
  onto the scarce causal-explanation budget.

### Hypotheses

- Increasing the explanation ceiling would make the run pass: rejected because
  it violates the protected budget and would allow four repeated template-family
  transforms.
- Reusing Scene 1's verified still for Scene 2 would reserve the slot: rejected
  because earlier human QA proved a single-state reuse cannot establish the
  requested two-shape comparison.
- A fresh, verified Scene-2 comparison still can use existing still slot 2 and
  reserve all three explanation transforms for Scenes 3-5: supported by the
  existing neutral comparison grounding and current still/explanation ceilings.

### Root cause

`WINDOW_COMPARISON_INTENT_SKIP_V1` skips the entire still path for the grounded
Scene-2 comparison. That includes both unsafe reuse and safe fresh generation,
so a non-causal question consumes one of only three deterministic explanation
transforms needed by the three causal claims.

### Minimal change

Keep both verified-still reuse paths blocked for this exact grounded comparison,
but call the existing still generator with a copied, explicit neutral
square-vs-rounded comparison goal. Fresh generation and existing Vision gates
remain mandatory. No ceiling changes.

### Verification

- [x] Exact Run 35314305498 routing regression.
- [x] Existing Run 34675233154 visual-progression regression.
- [x] Aircraft-window deterministic renderer regression.
- [x] Exact `main.yml` production hotfix composition and syntax checks.
- [ ] Exact-head PR CI and protected landing.
- [ ] Post-merge fixed-topic Development Engine rerun; no YouTube upload.

### Progress log

1. PR #407 landed; `main=a05a74a56dcf2f568b211b15ee062d6221835016`.
2. Run 35314305498 proved the hook-marker fix and exposed the downstream visual
   supply allocation failure described above.
3. Focused reservation and Run-524 progression regressions pass; exact main
   production hotfix sequence composes and the final runtime contains the V2
   fresh-still routing marker. Aircraft-window renderer regression also passes.
4. Two older broad regressions are stale independently of this change: the
   Phase-1 parser test still asserts the production renderer is not wired, and
   the Run-527 test still classifies the now-authoritative rounded-corner query
   as non-comparison. Neither is used as evidence for this change.

### Outcome

Pending.
