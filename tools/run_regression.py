#!/usr/bin/env python3
"""
Trigger a PayloadGuard regression cycle:
  1. Reopen test PRs  → scans fire automatically
  2. Wait for all scans to complete (polls check runs)
  3. Close all PRs again
  4. Optionally run ingest to hydrate SQLite

Modes
-----
  stable   (default) — runs the 16 stable test cases with strict pass/fail
  temporal           — runs only the 4 aging cases as observation (no pass/fail)
  full               — runs all active cases; stable=strict, aging=observational

Usage:
    export GITHUB_TOKEN=ghp_...
    python tools/run_regression.py
    python tools/run_regression.py --mode temporal
    python tools/run_regression.py --mode full --ingest
    python tools/run_regression.py --timeout 600
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

OWNER = "payloadguard-plg"
REPO = "payloadguard-test-harness"
TOOLS_DIR = Path(__file__).parent
TEST_CASES_FILE = TOOLS_DIR / "test_cases.json"

POLL_INTERVAL = 15   # seconds between status checks
DEFAULT_TIMEOUT = 300  # seconds before giving up


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(token, url, **params):
    resp = requests.get(url, headers=_headers(token), params=params or None, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _patch(token, url, body):
    resp = requests.patch(url, headers=_headers(token), json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_closed_test_prs(token, known_branches):
    """Return all closed PRs whose head branch is a known test branch."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
    results = []
    page = 1
    while True:
        prs = _get(token, url, state="closed", per_page=100, page=page)
        if not prs:
            break
        for pr in prs:
            branch = pr["head"]["ref"]
            if branch in known_branches:
                results.append(pr)
        if len(prs) < 100:
            break
        page += 1
    return results


def reopen_pr(token, pr_number):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}"
    return _patch(token, url, {"state": "open"})


def close_pr(token, pr_number):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}"
    return _patch(token, url, {"state": "closed"})


def get_check_runs(token, sha):
    """Return check runs for a given commit SHA filtered to PayloadGuard."""
    data = _get(
        token,
        f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{sha}/check-runs",
        check_name="PayloadGuard",
        per_page=10,
    )
    return data.get("check_runs", [])


# ── Polling ───────────────────────────────────────────────────────────────────

def wait_for_scans(token, pr_sha_map, timeout, reopen_time):
    """
    Poll until every PR in pr_sha_map has a completed PayloadGuard check run
    whose started_at is after reopen_time.  Returns dict of pr_number → conclusion.
    """
    deadline = time.time() + timeout
    pending = dict(pr_sha_map)   # pr_number → head_sha
    results = {}

    print(f"\nWaiting for {len(pending)} scan(s) to complete (timeout {timeout}s) ...")

    while pending and time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        done_now = []

        for pr_num, sha in pending.items():
            try:
                checks = get_check_runs(token, sha)
            except Exception:
                continue

            for check in checks:
                if check["status"] != "completed":
                    continue
                # Ignore stale check runs from before the reopen
                started = check.get("started_at", "")
                if started < reopen_time:
                    continue
                conclusion = check.get("conclusion", "unknown")
                results[pr_num] = conclusion
                done_now.append(pr_num)
                print(f"  PR #{pr_num}: {conclusion}")
                break

        for pr_num in done_now:
            del pending[pr_num]

        if pending:
            remaining = int(deadline - time.time())
            print(f"  {len(pending)} pending — {remaining}s left ...")

    if pending:
        print(f"\nWARNING: timed out waiting for PR(s): {sorted(pending)}")

    return results


# ── Pass/fail evaluation ──────────────────────────────────────────────────────

def _conclusion_matches(conclusion, expected_exit_code):
    """True if the GitHub check conclusion matches the expected exit code."""
    if expected_exit_code == 2:
        return conclusion == "failure"
    return conclusion == "success"


def evaluate_results(scan_results, pr_branch_map, test_cases, mode):
    """
    Print a per-PR verdict summary and return (passed, failed, observed) counts.

    stable  cases: strict pass/fail against expected_exit_code
    aging   cases: observational — printed but not counted in pass/fail
    """
    passed = failed = observed = 0

    print(f"\n{'─'*60}")
    print(f"{'ID':<6} {'Branch':<40} {'Result':<10} {'Status'}")
    print(f"{'─'*60}")

    for pr_num, conclusion in sorted(scan_results.items(), key=lambda x: x[0]):
        branch = pr_branch_map.get(pr_num, "unknown")
        tc = test_cases.get(branch, {})
        tc_id = tc.get("id", "?")
        group = tc.get("temporal_group", "stable")
        expected_exit = tc.get("expected_exit_code", 0)
        expected_verdict = tc.get("expected_verdict", "?")

        result_label = "DESTRUCTIVE" if conclusion == "failure" else "SAFE/OK"

        if group == "aging":
            status = f"[OBSERVING]  expected={expected_verdict}, age is accumulating"
            observed += 1
        elif _conclusion_matches(conclusion, expected_exit):
            status = "PASS"
            passed += 1
        else:
            expected_label = "DESTRUCTIVE" if expected_exit == 2 else "SAFE/OK"
            status = f"FAIL  expected={expected_label}, got={result_label}"
            failed += 1

        print(f"{tc_id:<6} {branch:<40} {result_label:<10} {status}")

    return passed, failed, observed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run a PayloadGuard regression cycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  stable   (default) — 16 stable cases, strict pass/fail
  temporal           — 4 aging cases, observational only (no pass/fail)
  full               — all active cases; stable=strict, aging=observational
        """,
    )
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Seconds to wait for scans (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--ingest", action="store_true",
                        help="Run ingest.py after closing PRs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without touching GitHub")
    parser.add_argument(
        "--mode", choices=["stable", "temporal", "full"], default="stable",
        help="stable=strict regression (default), temporal=aging observation, full=both",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: set GITHUB_TOKEN or pass --token", file=sys.stderr)
        sys.exit(1)

    test_cases = json.loads(TEST_CASES_FILE.read_text())

    # Filter branches by mode and skip pending cases
    if args.mode == "stable":
        active_branches = {
            b for b, tc in test_cases.items()
            if tc.get("temporal_group", "stable") == "stable"
            and tc.get("status") != "pending-2026-api"
        }
    elif args.mode == "temporal":
        active_branches = {
            b for b, tc in test_cases.items()
            if tc.get("temporal_group") == "aging"
        }
    else:  # full
        active_branches = {
            b for b, tc in test_cases.items()
            if tc.get("status") != "pending-2026-api"
        }

    print(f"Mode: {args.mode} — {len(active_branches)} branch(es) in scope")

    # ── 1. Find closed test PRs ───────────────────────────────────────────────
    print("Fetching closed test PRs ...")
    prs = list_closed_test_prs(args.token, active_branches)
    if not prs:
        print("No closed test PRs found. Nothing to do.")
        sys.exit(0)

    print(f"Found {len(prs)} closed PR(s):")
    pr_branch_map = {}
    for pr in sorted(prs, key=lambda p: p["number"]):
        branch = pr["head"]["ref"]
        tc = test_cases.get(branch, {})
        group_tag = f"[{tc.get('temporal_group', 'stable')}]"
        print(f"  #{pr['number']:3d}  {branch}  {group_tag}")
        pr_branch_map[pr["number"]] = branch

    if args.dry_run:
        print("\n--dry-run: stopping here.")
        sys.exit(0)

    # ── 2. Reopen all PRs ────────────────────────────────────────────────────
    reopen_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pr_sha_map = {}

    print(f"\nReopening {len(prs)} PR(s) ...")
    for pr in prs:
        pr_num = pr["number"]
        sha = pr["head"]["sha"]
        try:
            reopen_pr(args.token, pr_num)
            pr_sha_map[pr_num] = sha
            print(f"  #{pr_num} reopened  ({pr['head']['ref']})")
        except Exception as e:
            print(f"  #{pr_num} FAILED to reopen: {e}")

    if not pr_sha_map:
        print("All reopens failed. Aborting.")
        sys.exit(1)

    # ── 3. Wait for scans ─────────────────────────────────────────────────────
    scan_results = wait_for_scans(
        args.token, pr_sha_map, args.timeout, reopen_time
    )

    # ── 4. Close all PRs ─────────────────────────────────────────────────────
    print(f"\nClosing {len(pr_sha_map)} PR(s) ...")
    for pr_num in sorted(pr_sha_map):
        try:
            close_pr(args.token, pr_num)
            print(f"  #{pr_num} closed")
        except Exception as e:
            print(f"  #{pr_num} FAILED to close: {e}")

    # ── 5. Evaluate and summarise ─────────────────────────────────────────────
    passed, failed, observed = evaluate_results(
        scan_results, pr_branch_map, test_cases, args.mode
    )

    missed = len(pr_sha_map) - len(scan_results)

    print(f"\n{'─'*60}")
    print(f"Regression complete ({args.mode} mode) — "
          f"{len(scan_results)}/{len(pr_sha_map)} scans finished")
    if args.mode != "temporal":
        print(f"  PASS     : {passed}")
        print(f"  FAIL     : {failed}")
    if observed:
        print(f"  OBSERVING: {observed}  (aging cases — no pass/fail)")
    if missed:
        print(f"  timed out: {missed}")

    # ── 6. Optional ingest ───────────────────────────────────────────────────
    if args.ingest:
        print("\nRunning ingest ...")
        ingest_script = TOOLS_DIR / "ingest.py"
        result = subprocess.run(
            [sys.executable, str(ingest_script)],
            env={**os.environ, "GITHUB_TOKEN": args.token},
        )
        if result.returncode != 0:
            print("ingest.py exited with errors")
            sys.exit(result.returncode)

    if args.mode != "temporal" and failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
