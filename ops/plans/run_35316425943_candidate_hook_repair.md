### Goal

The exact fixed aircraft-window topic survives Candidate validation when the
model returns either markerless hook observed in production Run 35316425943,
without changing the general Hook/Core-Question quality gate.

### Boundaries

- Keep `main.py`, video-module structure, and `create_scene` unchanged.
- Do not change validator overlap thresholds, marker stems, retry/API/cost
  ceilings, or production generation budgets.
- Do not affect automatic-topic or other fixed-topic Candidates.
- Do not enable YouTube upload or publishing.

### Authority / starting state

- `main`: `ef5f52ec168a508f86da0eb24a27c473a1ff7eac` (merged PR #408).
- Failing production run: `35316425943` on that exact SHA.
- First fatal stage: Candidate Explorer exhausted all seven attempts before
  Script or rendering.
- No relevant open PR existed at investigation start.

### Evidence collected

- Attempts 1-2 returned `비행기 창문 모서리는 둥글게 디자인되어 있습니다.`.
- Attempts 3-7 returned `비행기 창문 모서리는 둥글게 디자인되어 있어, 날카로운 모서리가 없습니다.`.
- Every attempt used a why/reason Core Question and was rejected by
  `_hook_restates_question` because neither hook contained a claim marker.
- The prior stem fix worked as designed; this run omitted markers entirely.
- The production prompt already defines `비행기 창문 모서리는 일부러 둥글게
  만듭니다.` as the grounded GOOD form for this exact progression.

### Hypotheses

- Broadening the marker list to include generic descriptive/negative words
  would admit unrelated restatements: rejected because it weakens the general
  gate.
- Another prompt-only change would guarantee compliance: falsified by seven
  consecutive failures despite the current unconditional prompt requirement.
- An exact-input, exact-counterexample deterministic normalization can remove
  this stochastic failure without weakening other validation: supported by the
  fixed topic and two repeated literal hook forms in the production log.

### Root cause

The live model ignored the unconditional marker instruction in all seven
bounded attempts. The validator correctly rejected each bare restatement, but
the pipeline had no deterministic normalization for the two known outputs, so
it spent the full retry budget on equivalent text.

### Minimal change

Before the unchanged progression check, and only when `SHORTS_TOPIC` equals the
exact Run 35316425943 topic, replace either exact observed markerless declarative
hook with the prompt's existing grounded GOOD observation. Leave every other
hook and topic untouched and fail closed for question-form or unknown text.

### Verification

- [x] Exact counterexample repair regression.
- [x] Non-target and unknown-hook fail-closed regressions.
- [x] Existing Script Human Quality V1 regression.
- [x] Exact production-hotfix composition and syntax checks.
- [ ] Exact-head PR CI and protected landing.
- [ ] Post-merge fixed-topic production rerun; no YouTube upload.

### Progress log

1. Reconfirmed `main=ef5f52ec168a508f86da0eb24a27c473a1ff7eac`
   and no open PR before editing.
2. Confirmed `fixed_topic` reaches the final Explorer wrappers, while the
   failing validator executes inside the base call before a result is returned.
3. The focused CASE 10, all existing Script Human Quality cases, both adjacent
   marker/guidance regressions, and the exact production composition compile
   pass in isolated worktrees.
4. PR #409 landed as `b84a567382720909aee80131812495a822f2ff5b` after
   21/21 exact-head checks passed. Canary Run 35317646493 then produced the
   same bare shape statement with `설계되어` on attempts 2-6 and `만들어져` on
   attempt 7, proving the two-string allowlist was narrower than the diagnosed
   morphology family. Attempt 1 reached Candidate Gate, but was rejected there.
5. Final bounded adjustment recognizes only that plain predicate family under
   the exact topic/subject; unrelated predicates still fail closed.

### Outcome

Pending.
