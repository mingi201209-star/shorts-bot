# Operations Graph V1

Structured, evidence-backed memory of real production/CI incidents in this repository:
failure → root cause → fix → regression → PR → verification, and the relationships between
incidents. This exists so a long-running agent can look up what actually happened before,
without depending on chat history it may never have seen, and without trusting a prior agent's
own summary as if it were proof.

**Core principle: summary is not authority. Evidence is authority.** Every claim this graph
lets an agent trust is backed by a GitHub-native identifier — a run ID, job ID, commit SHA, PR
number, or a real test file — not prose alone.

This is deliberately **not** a graph database. V1 is plain JSON files plus a small deterministic
Python query/validate layer. No Neo4j, no vector DB, no embeddings, no LLM calls anywhere in
this directory.

## Layout

```
operations/
  README.md          this file
  schema.json         JSON Schema (draft 2020-12) for one incident record
  incidents/          one JSON file per incident, *.json, source of truth
  query.py            deterministic local query CLI (no network, no LLM)
  validate.py         schema + evidence-completeness + relationship-integrity validator
```

There is no separate `index.jsonl` cache in this V1: `incidents/*.json` is the single source of
truth, `query.py` and `validate.py` both read it directly. A second denormalized index file
would be exactly the kind of drift-prone duplication `AGENTS.md`'s Quality section warns
against (see `operations/incidents/INC-2026-001-*.json` for a real example of duplicated values
going stale independently in three places) — with only a few incidents, scanning the directory
is fast enough that a cache buys nothing but a new way to go stale.

## The confidence field is not a feeling

`confidence` is a **limited enum describing evidence completeness**, never an agent's
subjective certainty:

- **`VERIFIED`** — all three evidence categories are present and internally consistent:
  1. **Failure evidence**: `run_id` and/or `job_id` set, and `failure_signature` non-empty.
  2. **Fix evidence**: `fix.commits` non-empty (real commit SHAs).
  3. **Regression/verification evidence**: `regressions.test_files` non-empty **and**
     `verification.workflow_runs` non-empty with `verification.result == "PASS"`.

  `operations/validate.py` enforces all three mechanically. An agent cannot mark an incident
  `VERIFIED` by asserting it in `root_cause.summary` — the fields have to actually be populated
  with real identifiers, and the validator checks the SHA/run-id/job-id shapes look real (regex
  pattern), not just "any string."

- **`PARTIAL`** — some evidence exists but the incident does not meet the full `VERIFIED` bar.
  Common cases: the fix landed but hasn't been re-verified by a post-fix green run yet; a root
  cause is evidence-backed but no regression test was added; a PR is still open. `PARTIAL`
  incidents MUST still have `failure_signature`, `failure_stage`, and `root_cause.summary`
  populated — those are never allowed to be guessed-and-skipped, only the fix/regression/
  verification side may be incomplete while the fix is in flight.

- **`UNVERIFIED`** — a symptom/signature was observed but root cause, fix, or verification is
  still a hypothesis, not evidence. `root_cause.evidence` may be empty. This is the correct
  status for "we saw this happen once, haven't investigated yet" — recording that state
  honestly is more useful than inventing a root cause to look complete.

## Null policy: never guess, mark it

When a field's true value cannot currently be established from real evidence:

- Use `null` for a value the schema types as nullable (`authority_main_sha`, `run_id`, `job_id`,
  `verified_sha`, `regressions.counterexample`, `regressions.result`).
- Use an empty array (`[]`) for a list with genuinely nothing to report yet (`fix.commits`,
  `regressions.test_files`, `pull_requests`, `relationships`) — never a fabricated placeholder
  entry.
- **Never fill an unknown field with a plausible-looking guess.** A guessed SHA, run ID, or PR
  number is worse than `null`: it looks like evidence and isn't. If you cannot re-verify a value
  against GitHub right now, record `null`/`[]` and set `confidence` accordingly — do not carry
  forward a number from an old chat message, prompt, or draft without re-checking it live. (This
  exact mistake — trusting a stale SHA instead of re-checking GitHub — is itself a real,
  evidence-backed pattern in this repository's incident history.)

## Adding a new incident

1. Confirm the real evidence first: the failing run/job ID, the exact failure text, the fix
   commit SHA(s), the PR number, and (once landed) a post-fix green run ID — pulled live from
   GitHub, not recalled.
2. Copy an existing file in `incidents/` as a starting shape, or build one against
   `schema.json`.
3. Pick the next `incident_id`: `INC-<year>-<3-digit-seq>-<SHORT-SLUG>`, sequential within the
   year, not reused.
4. Set `confidence` honestly per the policy above — `VERIFIED` only when all three evidence
   categories are real and complete.
5. Run `python operations/validate.py`. Fix anything it flags before committing.
6. If this incident is related to an existing one (same failure signature recurring, a
   regression of an earlier fix, a fix that supersedes an older one), add a `relationships`
   entry with a controlled `type` — do not invent a new relationship type outside
   `RELATED_TO` / `SAME_SIGNATURE_AS` / `REGRESSION_OF` / `SUPERSEDES`.

## Querying

```
python operations/query.py --failure-signature "HTTP 429"
python operations/query.py --file video/video_engine.py
python operations/query.py --root-cause PROVIDER_AVAILABILITY
python operations/query.py --related INC-2026-001-PEXELS-429
python operations/query.py --list
```

Every query is a local, deterministic scan over `incidents/*.json` — no network access, no LLM
call. Output always includes the incident, its root cause, fix commit(s), regression coverage,
verification result, and the underlying evidence so the caller can go re-check the primary
source directly rather than trusting the printed line.

## Validating

```
python operations/validate.py
```

Exits non-zero on any violation: schema invalidity, duplicate incident IDs, malformed SHA/run
ID/job ID shapes, an unknown relationship type, a dangling relationship (target incident ID that
doesn't exist), missing required evidence for the declared `confidence`, or an invalid
`status`/`confidence` value. See the module docstring in `validate.py` for the full check list.
This is wired into CI as a cheap, fully deterministic, network-free gate — it never calls
OpenAI, Pexels, YouTube, or any other external API, and never generates a video.
