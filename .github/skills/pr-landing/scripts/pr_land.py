#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import sys


def run(cmd, *, check=True):
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or f"command failed: {' '.join(cmd)}")
    return proc


def gh_json(args):
    proc = run(["gh", *args])
    raw = proc.stdout.strip()
    return json.loads(raw) if raw else None


def fail(message, code=2):
    print(json.dumps({"status": "blocked", "reason": message}, ensure_ascii=False))
    raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description="Fail-closed PR landing helper")
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head", required=True, help="Expected exact PR head SHA")
    parser.add_argument("--mode", choices=["auto", "queue"], required=True)
    parser.add_argument("--method", choices=["merge", "squash", "rebase"])
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if shutil.which("gh") is None:
        fail("GitHub CLI 'gh' is unavailable")

    if args.mode == "auto" and not args.method:
        fail("--method is required for --mode auto")
    if args.mode == "queue" and args.method:
        fail("--method must be omitted for --mode queue")

    try:
        pr = gh_json([
            "pr", "view", str(args.pr),
            "--repo", args.repo,
            "--json", "number,url,state,isDraft,headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup"
        ])
    except Exception as exc:
        fail(f"unable to read PR: {exc}")

    if not pr:
        fail("empty PR response")
    if pr.get("state") != "OPEN":
        fail(f"PR state is {pr.get('state')}, expected OPEN")
    if pr.get("isDraft"):
        fail("PR is still draft")
    current_head = pr.get("headRefOid")
    if current_head != args.head:
        fail(f"head changed: expected {args.head}, got {current_head}")

    failing = []
    pending = []
    for check in pr.get("statusCheckRollup") or []:
        name = check.get("name") or check.get("context") or check.get("workflowName") or "unknown-check"
        conclusion = check.get("conclusion")
        status = check.get("status") or check.get("state")
        if conclusion in {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}:
            failing.append(name)
        elif conclusion in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            continue
        elif status in {"COMPLETED"} and conclusion:
            continue
        else:
            pending.append(name)

    if failing:
        fail("failing checks: " + ", ".join(sorted(set(failing))))
    if pending:
        fail("pending checks: " + ", ".join(sorted(set(pending))))

    merge_state = pr.get("mergeStateStatus")
    if merge_state in {"DIRTY", "BLOCKED", "BEHIND", "DRAFT", "UNKNOWN"}:
        fail(f"mergeStateStatus is {merge_state}")

    plan = {
        "status": "ready",
        "repo": args.repo,
        "pr": args.pr,
        "url": pr.get("url"),
        "head": current_head,
        "mode": args.mode,
        "method": args.method,
        "reviewDecision": pr.get("reviewDecision"),
        "mergeStateStatus": merge_state,
        "warning": "This request may merge immediately if repository protections are already satisfied.",
    }

    if not args.confirm:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    # Re-read immediately before mutation so approval is bound to the exact current head.
    try:
        fresh = gh_json([
            "pr", "view", str(args.pr),
            "--repo", args.repo,
            "--json", "state,isDraft,headRefOid,mergeStateStatus"
        ])
    except Exception as exc:
        fail(f"unable to revalidate PR: {exc}")

    if fresh.get("state") != "OPEN" or fresh.get("isDraft"):
        fail("PR became non-landable during revalidation")
    if fresh.get("headRefOid") != args.head:
        fail(f"head changed during revalidation: expected {args.head}, got {fresh.get('headRefOid')}")
    if fresh.get("mergeStateStatus") in {"DIRTY", "BLOCKED", "BEHIND", "DRAFT", "UNKNOWN"}:
        fail(f"mergeStateStatus changed to {fresh.get('mergeStateStatus')}")

    cmd = ["gh", "pr", "merge", str(args.pr), "--repo", args.repo, "--match-head-commit", args.head]
    if args.mode == "auto":
        cmd += ["--auto", f"--{args.method}"]
    else:
        # With merge queue protection, GitHub/gh enrolls the PR through the normal protected path.
        # No admin or bypass flags are ever permitted here.
        pass

    proc = run(cmd, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        fail("landing request rejected by GitHub: " + detail)

    print(json.dumps({
        "status": "landing_requested",
        "repo": args.repo,
        "pr": args.pr,
        "head": args.head,
        "mode": args.mode,
        "method": args.method,
        "message": (proc.stdout or proc.stderr).strip(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
