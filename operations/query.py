#!/usr/bin/env python3
"""Operations Graph V1 deterministic query CLI.

Local, deterministic scan over operations/incidents/*.json. No network access, no LLM call --
every answer traces back to a real file in this repository, printed alongside its evidence so
the caller can go re-verify the primary GitHub source directly.

Usage:
    python operations/query.py --list
    python operations/query.py --failure-signature "HTTP 429"
    python operations/query.py --file video/video_engine.py
    python operations/query.py --root-cause PROVIDER_AVAILABILITY
    python operations/query.py --related INC-2026-001-PEXELS-429
    python operations/query.py --incident-id INC-2026-001-PEXELS-429

Flags may be combined; matches must satisfy every provided flag (AND, not OR).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OPERATIONS_DIR = Path(__file__).resolve().parent
INCIDENTS_DIR = OPERATIONS_DIR / "incidents"


def load_incidents(incidents_dir: Path | None = None) -> list[dict]:
    incidents_dir = incidents_dir or INCIDENTS_DIR
    incidents = []
    for path in sorted(incidents_dir.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            incidents.append(json.load(f))
    return incidents


def _matches(incident: dict, args: argparse.Namespace) -> bool:
    if args.incident_id and incident.get("incident_id") != args.incident_id:
        return False
    if args.failure_signature:
        needle = args.failure_signature.lower()
        haystack = " ".join(
            [
                incident.get("failure_signature", ""),
                " ".join(incident.get("symptoms", [])),
            ]
        ).lower()
        if needle not in haystack:
            return False
    if args.file:
        affected = set(incident.get("affected_files", []))
        fix_files = set((incident.get("fix") or {}).get("files", []))
        if args.file not in affected and args.file not in fix_files:
            return False
    if args.root_cause:
        if (incident.get("root_cause") or {}).get("category") != args.root_cause:
            return False
    if args.status and incident.get("status") != args.status:
        return False
    if args.confidence and incident.get("confidence") != args.confidence:
        return False
    return True


def _print_incident(incident: dict, *, verbose: bool = True) -> None:
    print(f"[{incident.get('incident_id')}] {incident.get('failure_signature')}")
    print(f"  timestamp:        {incident.get('timestamp')}")
    print(f"  status/confidence: {incident.get('status')} / {incident.get('confidence')}")
    print(f"  failure_stage:    {incident.get('failure_stage')}")
    if incident.get("run_id") or incident.get("job_id"):
        print(f"  evidence:         run_id={incident.get('run_id')} job_id={incident.get('job_id')} "
              f"workflow={incident.get('workflow')}")
    root_cause = incident.get("root_cause") or {}
    print(f"  root_cause:       [{root_cause.get('category')}] {root_cause.get('summary')}")
    for ev in root_cause.get("evidence", []):
        print(f"                    evidence: {ev.get('kind')}={ev.get('value')}"
              + (f"  ({ev.get('note')})" if ev.get("note") else ""))
    if not verbose:
        return
    fix = incident.get("fix") or {}
    commits = ", ".join(fix.get("commits", [])) or "(none)"
    print(f"  fix commit(s):    {commits}")
    print(f"  fix summary:      {fix.get('summary')}")
    regressions = incident.get("regressions") or {}
    tests = ", ".join(regressions.get("test_files", [])) or "(none)"
    print(f"  regression tests: {tests}")
    print(f"  counterexample:   {regressions.get('counterexample')}")
    print(f"  regression result:{regressions.get('result')}")
    for pr in incident.get("pull_requests", []):
        print(f"  PR:               #{pr.get('number')} [{pr.get('status')}]"
              + (f" merge_commit={pr.get('merge_commit')}" if pr.get("merge_commit") else ""))
    verification = incident.get("verification") or {}
    print(f"  verification:     result={verification.get('result')} "
          f"verified_sha={verification.get('verified_sha')}")
    for run in verification.get("workflow_runs", []):
        print(f"                    run_id={run.get('run_id')} job_id={run.get('job_id')} "
              f"conclusion={run.get('conclusion')}")
    for rel in incident.get("relationships", []):
        print(f"  relationship:     --{rel.get('type')}--> {rel.get('target_incident_id')}"
              + (f"  ({rel.get('note')})" if rel.get("note") else ""))


def _cmd_related(incidents: list[dict], target_id: str) -> int:
    by_id = {inc.get("incident_id"): inc for inc in incidents}
    target = by_id.get(target_id)
    if target is None:
        print(f"No incident found with incident_id={target_id!r}")
        return 1

    print(f"Relationships for {target_id}:")
    found_any = False
    for rel in target.get("relationships", []):
        found_any = True
        other = by_id.get(rel.get("target_incident_id"))
        label = other.get("failure_signature") if other else "(unknown incident)"
        print(f"  {target_id} --{rel.get('type')}--> {rel.get('target_incident_id')}  ({label})")

    for inc in incidents:
        if inc.get("incident_id") == target_id:
            continue
        for rel in inc.get("relationships", []):
            if rel.get("target_incident_id") == target_id:
                found_any = True
                print(f"  {inc.get('incident_id')} --{rel.get('type')}--> {target_id}  "
                      f"({inc.get('failure_signature')})")

    if not found_any:
        print("  (no relationships recorded)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List every incident (summary line only).")
    parser.add_argument("--failure-signature", help="Substring match against failure_signature + symptoms.")
    parser.add_argument("--file", help="Exact match against affected_files or fix.files.")
    parser.add_argument("--root-cause", help="Exact match against root_cause.category.")
    parser.add_argument("--status", help="Exact match against status.")
    parser.add_argument("--confidence", help="Exact match against confidence.")
    parser.add_argument("--related", metavar="INCIDENT_ID", help="Show relationship edges for one incident_id.")
    parser.add_argument("--incident-id", help="Exact match against incident_id.")
    parser.add_argument("--json", action="store_true", help="Emit matches as JSON instead of formatted text.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not INCIDENTS_DIR.exists():
        print(f"No incidents directory at {INCIDENTS_DIR}")
        return 1

    incidents = load_incidents()

    if args.related:
        return _cmd_related(incidents, args.related)

    if args.list:
        if args.json:
            print(json.dumps(
                [{"incident_id": i.get("incident_id"), "failure_signature": i.get("failure_signature"),
                  "status": i.get("status"), "confidence": i.get("confidence")} for i in incidents],
                ensure_ascii=False, indent=2,
            ))
        else:
            for incident in incidents:
                print(f"[{incident.get('incident_id')}] {incident.get('status')}/{incident.get('confidence')}  "
                      f"{incident.get('failure_signature')}")
        return 0

    filters_given = any([
        args.failure_signature, args.file, args.root_cause, args.status, args.confidence, args.incident_id,
    ])
    if not filters_given:
        parser.print_help()
        return 1

    matches = [i for i in incidents if _matches(i, args)]

    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return 0 if matches else 1

    if not matches:
        print("No matching incidents.")
        return 1

    for i, incident in enumerate(matches):
        if i:
            print()
        _print_incident(incident)

    return 0


if __name__ == "__main__":
    sys.exit(main())
