#!/usr/bin/env python3
"""
Collect the scan history of every harness fixture from GitHub check runs.

Each PayloadGuard scan posts a "PayloadGuard" check run on the fixture PR's head
commit. Workflow artifacts, and the results.db that ingest.py builds from them,
expire after 90 days; check runs do not. This script reads every PayloadGuard
check run on each fixture's head commit, resolves the analyser version that the
harness workflow pinned for the scan, and appends one record per check run to
regression-reports/scan_history.jsonl (deduplicated by check run id). It then
rewrites regression-reports/latest_regression_summary.md from the full history.

The analyser pin is read from .github/workflows/payloadguard.yml at the target
commit the report names, so the harness clone needs main's history (git fetch).
Scans on commits that are no longer a fixture PR's head are not reachable.
Pass/fail is judged against the current tools/test_cases.json.

Usage:
    python tools/collect_history.py --analyser-dir ../payload-consequence-analyser
    GITHUB_TOKEN=ghp_... python tools/collect_history.py   # 5000 requests/h instead of 60
    python tools/collect_history.py --save-raw DIR          # keep the API responses
    python tools/collect_history.py --from-raw DIR          # rebuild from saved responses
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

OWNER = "payloadguard-plg"
REPO = "payloadguard-test-harness"
CHECK_NAME = "PayloadGuard"
HARNESS_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_FILE = HARNESS_ROOT / "tools" / "test_cases.json"
REPORTS_DIR = HARNESS_ROOT / "regression-reports"
HISTORY_NAME = "scan_history.jsonl"
SUMMARY_NAME = "latest_regression_summary.md"
SWEEP_GAP = datetime.timedelta(minutes=30)
VERDICT_LETTER = {"SAFE": "S", "REVIEW": "R", "CAUTION": "C", "DESTRUCTIVE": "D"}


# ── GitHub API (or saved responses) ───────────────────────────────────────────

class Source:
    def __init__(self, token=None, save_raw=None, from_raw=None):
        self.token, self.save_raw, self.from_raw = token, save_raw, from_raw
        self.requests = 0

    def get(self, name, url, params):
        if self.from_raw:
            return json.loads((self.from_raw / name).read_text(encoding="utf-8"))
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        self.requests += 1
        resp.raise_for_status()
        data = resp.json()
        if self.save_raw:
            self.save_raw.mkdir(parents=True, exist_ok=True)
            (self.save_raw / name).write_text(json.dumps(data), encoding="utf-8")
        return data

    def pulls(self):
        prs, page = [], 1
        while True:
            batch = self.get(f"pulls_{page}.json", f"https://api.github.com/repos/{OWNER}/{REPO}/pulls",
                             {"state": "all", "per_page": 100, "page": page})
            prs.extend(batch)
            if len(batch) < 100:
                return prs
            page += 1

    def check_runs(self, case_id, sha):
        runs, page = [], 1
        while True:
            data = self.get(f"checks_{case_id}_{page}.json",
                            f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{sha}/check-runs",
                            {"check_name": CHECK_NAME, "filter": "all", "per_page": 100, "page": page})
            runs.extend(data["check_runs"])
            if len(runs) >= data["total_count"] or not data["check_runs"]:
                return runs
            page += 1


# ── Report parsing ────────────────────────────────────────────────────────────

def _num(text):
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", text or "")
    if not m:
        return None
    value = float(m.group().replace(",", ""))
    return int(value) if value.is_integer() and "." not in m.group() else value


def _sections(summary):
    """Map each '### <icon> <title> (Layer n)' heading to (body, {row label: value}), keyed by title."""
    out = {}
    for block in summary.split("\n### ")[1:]:
        heading, _, body = block.partition("\n")
        title = re.sub(r"\s*\(Layer \w+\)$", "", heading.split(" ", 1)[-1].strip())
        out[title] = (body, dict(re.findall(r"^\| ([^|`]+?) \| ([^|]+?) \|", body, re.M)))
    return out


def _section(sections, title):
    return sections.get(title, ("", {}))


def _status(body):
    m = re.search(r"\*\*(?:Status|Severity):\*\*[^`\n]*`(\w+)`", body)
    return m.group(1) if m else None


def parse_report(summary):
    summary = summary or ""
    head = re.search(r"PayloadGuard — `(SAFE|REVIEW|CAUTION|DESTRUCTIVE)` \[(\w+)\]", summary)
    sections = _sections(summary)
    _, temporal = _section(sections, "Temporal")
    _, files = _section(sections, "File Changes")
    _, lines = _section(sections, "Line Changes")
    struct_body, _ = _section(sections, "Structural Drift")
    drift_body, drift = _section(sections, "Temporal Drift")
    sem_body, _ = _section(sections, "Semantic Transparency")
    target = re.search(r"\| Target commit \| `([0-9a-f]+)`", summary)
    mci = re.search(r"\*\*MCI score:\*\* `([\d.]+)`", sem_body)
    return {
        "verdict": head.group(1) if head else None,
        "severity": head.group(2) if head else None,
        "target_sha": target.group(1) if target else None,
        "branch_age_days": _num(temporal.get("Branch age")),
        "files": {k.lower(): _num(files.get(k)) for k in ("Added", "Deleted", "Modified")},
        "lines": {"added": _num(lines.get("Added")), "deleted": _num(lines.get("Deleted")),
                  "deletion_ratio_pct": _num(lines.get("Deletion ratio"))},
        "structural_severity": _status(struct_body),
        "temporal_status": _status(drift_body),
        "drift_score": _num(drift.get("Drift score")),
        "semantic_status": _status(sem_body),
        "mci_score": float(mci.group(1)) if mci else None,
        "consequence_detectors": sorted(set(re.findall(r"\bD\d{2}_[A-Z][A-Z_]*[A-Z]", summary))),
    }


# ── Analyser version resolution ───────────────────────────────────────────────

def _git(cwd, *args):
    res = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return res.stdout.strip() if res.returncode == 0 else None


class AnalyserResolver:
    def __init__(self, analyser_dir):
        self.analyser_dir = analyser_dir
        self._pins, self._versions = {}, {}

    def workflow_pin(self, target_sha):
        """The analyser ref that payloadguard.yml at target_sha uses (a SHA or a branch name)."""
        if target_sha not in self._pins:
            text = _git(HARNESS_ROOT, "show", f"{target_sha}:.github/workflows/payloadguard.yml") or ""
            m = re.search(r"payload-consequence-analyser@([\w.\-/]+)", text)
            self._pins[target_sha] = m.group(1) if m else None
        return self._pins[target_sha]

    def resolve(self, ref, started_at):
        """Return (analyser commit, version) for a pinned SHA or a branch tracked at scan time."""
        if not self.analyser_dir or not ref:
            return None, None
        if re.fullmatch(r"[0-9a-f]{7,40}", ref):
            sha = _git(self.analyser_dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        else:
            sha = _git(self.analyser_dir, "rev-list", "-1", "--first-parent",
                       f"--before={started_at}", f"origin/{ref}")
        if not sha:
            return None, None
        if sha not in self._versions:
            source = _git(self.analyser_dir, "show", f"{sha}:analyze.py") or ""
            m = re.search(r'__version__\s*=\s*"([^"]+)"', source)
            self._versions[sha] = m.group(1) if m else None
        return sha, self._versions[sha]


# ── Collection ────────────────────────────────────────────────────────────────

def collect(source, resolver, test_cases):
    heads = {}
    for pr in sorted(source.pulls(), key=lambda p: p["number"]):
        heads[pr["head"]["ref"]] = (pr["number"], pr["head"]["sha"])

    records = []
    for branch, tc in test_cases.items():
        if branch not in heads:
            continue
        pr_number, head_sha = heads[branch]
        group = tc.get("temporal_group", "stable")
        for run in source.check_runs(tc["id"], head_sha):
            if run["status"] != "completed":
                continue
            report = parse_report(run["output"].get("summary"))
            ref = resolver.workflow_pin(report["target_sha"]) if report["target_sha"] else None
            analyser_sha, version = resolver.resolve(ref, run["started_at"])
            exit_match = (run["conclusion"] == "failure") == (tc["expected_exit_code"] == 2)
            records.append({
                "check_run_id": run["id"],
                "started_at": run["started_at"],
                "completed_at": run["completed_at"],
                "app": run["app"]["slug"],
                "test_case_id": tc["id"],
                "branch": branch,
                "category": tc.get("category"),
                "temporal_group": group,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "analyser_ref": ref,
                "analyser_sha": analyser_sha,
                "analyser_version": version,
                "conclusion": run["conclusion"],
                **report,
                "expected_verdict": tc["expected_verdict"],
                "expected_exit_code": tc["expected_exit_code"],
                "exit_code_match": None if group == "aging" else exit_match,
                "verdict_match": None if group == "aging" else report["verdict"] == tc["expected_verdict"],
                "summary_md": run["output"].get("summary"),
            })
    return records


def append_history(records, reports_dir):
    reports_dir.mkdir(parents=True, exist_ok=True)
    history_file = reports_dir / HISTORY_NAME
    history = []
    if history_file.exists():
        history = [json.loads(line) for line in history_file.read_text(encoding="utf-8").splitlines() if line]
    known = {r["check_run_id"] for r in history}
    new = sorted((r for r in records if r["check_run_id"] not in known),
                 key=lambda r: (r["started_at"], r["check_run_id"]))
    with open(history_file, "a", encoding="utf-8", newline="\n") as fp:
        for r in new:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    return history + new, len(new)


# ── Summary ───────────────────────────────────────────────────────────────────

def _ts(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _analyser_label(r):
    sha = (r.get("analyser_sha") or r.get("analyser_ref") or "?")[:7]
    version = r.get("analyser_version") or ("unversioned" if r.get("analyser_sha") else "?")
    if r.get("analyser_ref") and not re.fullmatch(r"[0-9a-f]{7,40}", r["analyser_ref"]):
        return f"{version} (`{r['analyser_ref']}` @ `{sha}`)"
    return f"{version} (`{sha}`)"


def sweeps(history):
    """Group scans into sweeps: a new sweep starts after a gap longer than SWEEP_GAP."""
    groups, last = [], None
    for r in sorted(history, key=lambda r: r["started_at"]):
        t = _ts(r["started_at"])
        if last is None or t - last > SWEEP_GAP:
            groups.append([])
        groups[-1].append(r)
        last = t
    return groups


def write_summary(history, test_cases, reports_dir):
    if not history:
        return
    ordered = sorted(history, key=lambda r: r["started_at"])
    lines = [
        "# PayloadGuard Harness — Scan History",
        "",
        f"- **Collected (UTC):** `{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}`",
        f"- **Check runs recorded:** `{len(history)}` from `{ordered[0]['started_at'][:10]}` to "
        f"`{ordered[-1]['started_at'][:10]}`, across `{len({r['test_case_id'] for r in history})}` fixtures",
        "- **Source:** the `PayloadGuard` check run of every scan on each fixture PR's head commit "
        "(`regression-reports/scan_history.jsonl`, one record per check run with the full report)",
        "- **Judged against:** the current `tools/test_cases.json`. Exit-code match is the live regression "
        "criterion (DESTRUCTIVE ⇔ expected exit 2); verdict match also compares SAFE/REVIEW/CAUTION. "
        "Aging cases are observational and excluded from both.",
        "",
        "## Sweeps",
        "",
        "| Started (UTC) | Analyser | Scans | Exit-code match | Verdict match | Exit-code mismatches |",
        "|---|---|---|---|---|---|",
    ]
    for group in sweeps(history):
        judged = [r for r in group if r["exit_code_match"] is not None]
        analysers = sorted({_analyser_label(r) for r in group})
        misses = sorted({r["test_case_id"] for r in judged if not r["exit_code_match"]})
        lines.append(
            f"| {group[0]['started_at'][:16].replace('T', ' ')} | {', '.join(analysers)} | {len(group)} | "
            f"{sum(r['exit_code_match'] for r in judged)}/{len(judged)} | "
            f"{sum(bool(r['verdict_match']) for r in judged)}/{len(judged)} | "
            f"{', '.join(misses) or '—'} |"
        )

    lines += [
        "",
        "## Latest scan per case",
        "",
        "| ID | Expected | Latest | Analyser | Scanned (UTC) | Consequence detectors | Exit code | "
        "History (oldest → newest) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    by_case = {}
    for r in ordered:
        by_case.setdefault(r["test_case_id"], []).append(r)
    for tc in test_cases.values():
        runs = by_case.get(tc["id"])
        if not runs:
            continue
        last = runs[-1]
        status = ("observing" if last["exit_code_match"] is None
                  else "match" if last["exit_code_match"] else "**MISMATCH**")
        history_str = "".join(VERDICT_LETTER.get(r["verdict"], "?") for r in runs)
        lines.append(
            f"| `{tc['id']}` | `{tc['expected_verdict']}` | `{last['verdict']}` | {_analyser_label(last)} | "
            f"{last['started_at'][:16].replace('T', ' ')} | "
            f"{', '.join(f'`{d}`' for d in last['consequence_detectors']) or '—'} | {status} | `{history_str}` |"
        )
    lines += ["", "History letters: S = SAFE, R = REVIEW, C = CAUTION, D = DESTRUCTIVE.", ""]
    (reports_dir / SUMMARY_NAME).write_text("\n".join(lines), encoding="utf-8", newline="\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Collect fixture scan history from PayloadGuard check runs")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--analyser-dir", type=Path,
                        help="Local analyser clone, used to resolve pinned SHAs to versions")
    parser.add_argument("--save-raw", type=Path, help="Write each API response to this directory")
    parser.add_argument("--from-raw", type=Path, help="Read API responses from this directory instead")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR,
                        help=f"Output directory (default: {REPORTS_DIR.relative_to(HARNESS_ROOT)})")
    args = parser.parse_args()

    test_cases = json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))
    source = Source(args.token, args.save_raw, args.from_raw)
    resolver = AnalyserResolver(args.analyser_dir.resolve() if args.analyser_dir else None)

    records = collect(source, resolver, test_cases)
    history, added = append_history(records, args.reports_dir)
    write_summary(history, test_cases, args.reports_dir)

    unresolved = sum(1 for r in records if not r["analyser_sha"])
    print(f"{len(records)} check runs read ({source.requests} API requests); {added} new, "
          f"{len(history)} in {args.reports_dir / HISTORY_NAME}")
    if args.analyser_dir and unresolved:
        print(f"WARNING: analyser commit unresolved for {unresolved} check runs", file=sys.stderr)


if __name__ == "__main__":
    main()
