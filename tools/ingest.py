#!/usr/bin/env python3
"""
Pull PayloadGuard JSON artifacts from GitHub Actions and write to SQLite.

Usage:
    export GITHUB_TOKEN=ghp_...
    python tools/ingest.py
    python tools/ingest.py --since 2026-04-24
    python tools/ingest.py --db /path/to/custom.db
"""
import argparse
import io
import json
import os
import sqlite3
import sys
import zipfile
from pathlib import Path

import requests

OWNER = "payloadguard-plg"
REPO = "payloadguard-test-harness"
WORKFLOW_FILE = "payloadguard.yml"
ARTIFACT_NAME = "payloadguard-results"

TOOLS_DIR = Path(__file__).parent
DEFAULT_DB = TOOLS_DIR / "db" / "results.db"
TEST_CASES_FILE = TOOLS_DIR / "test_cases.json"


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
    return resp


def list_workflow_runs(token, since=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    params = {"per_page": 100, "status": "completed"}
    if since:
        params["created"] = f">={since}"

    runs = []
    while url:
        resp = _get(token, url, **params)
        data = resp.json()
        runs.extend(data.get("workflow_runs", []))
        url = resp.links.get("next", {}).get("url")
        params = {}
    return runs


def list_artifacts(token, run_id):
    resp = _get(token, f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/artifacts")
    return resp.json().get("artifacts", [])


def download_artifact_zip(token, artifact_id):
    resp = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/artifacts/{artifact_id}/zip",
        headers=_headers(token),
        allow_redirects=True,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def extract_json(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".json"):
                return json.loads(z.read(name))
    return None


# ── SQLite ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_runs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id         TEXT    UNIQUE NOT NULL,
    pr_number               INTEGER,
    branch                  TEXT    NOT NULL,
    test_case_id            TEXT,
    category                TEXT,
    temporal_group          TEXT,
    run_at                  TEXT    NOT NULL,
    ingested_at             TEXT    DEFAULT CURRENT_TIMESTAMP,

    verdict_status          TEXT,
    verdict_severity        TEXT,
    verdict_score           REAL,
    exit_code               INTEGER,

    files_added             INTEGER,
    files_deleted           INTEGER,
    files_modified          INTEGER,

    lines_added             INTEGER,
    lines_deleted           INTEGER,
    deletion_ratio_pct      REAL,

    structural_severity     TEXT,
    structural_max_ratio    REAL,

    branch_age_days         INTEGER,
    temporal_status         TEXT,
    temporal_score          REAL,

    semantic_status         TEXT,
    semantic_is_deceptive   INTEGER,
    semantic_keyword        TEXT,

    raw_json                TEXT
);

CREATE TABLE IF NOT EXISTS structural_flags (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              INTEGER REFERENCES scan_runs(id) ON DELETE CASCADE,
    file_path           TEXT,
    status              TEXT,
    severity            TEXT,
    deleted_node_count  INTEGER,
    deletion_ratio_pct  REAL,
    deleted_components  TEXT
);

CREATE TABLE IF NOT EXISTS expected_verdicts (
    test_case_id        TEXT PRIMARY KEY,
    category            TEXT,
    temporal_group      TEXT,
    expected_verdict    TEXT,
    expected_exit_code  INTEGER,
    description         TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_branch    ON scan_runs(branch);
CREATE INDEX IF NOT EXISTS idx_runs_tc        ON scan_runs(test_case_id);
CREATE INDEX IF NOT EXISTS idx_runs_run_at    ON scan_runs(run_at);
"""


def init_db(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def seed_expected_verdicts(conn, test_cases):
    for branch, tc in test_cases.items():
        conn.execute(
            """INSERT OR REPLACE INTO expected_verdicts
               (test_case_id, category, temporal_group, expected_verdict, expected_exit_code, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tc["id"], tc["category"], tc.get("temporal_group", "stable"),
             tc["expected_verdict"], tc["expected_exit_code"], tc["description"]),
        )
    conn.commit()


def insert_run(conn, run, report, test_cases):
    branch = run.get("head_branch", "")
    tc = test_cases.get(branch, {})

    verdict   = report.get("verdict", {})
    files     = report.get("files", {})
    lines     = report.get("lines", {})
    struct    = report.get("structural", {})
    td        = report.get("temporal_drift", {})
    td_m      = td.get("metrics", {})
    sem       = report.get("semantic", {})

    status = verdict.get("status", "")
    exit_code = 2 if status == "DESTRUCTIVE" else (1 if "error" in report else 0)

    pr_number = None
    if run.get("pull_requests"):
        pr_number = run["pull_requests"][0]["number"]

    cur = conn.execute(
        """INSERT OR IGNORE INTO scan_runs (
               workflow_run_id, pr_number, branch, test_case_id, category, temporal_group, run_at,
               verdict_status, verdict_severity, verdict_score, exit_code,
               files_added, files_deleted, files_modified,
               lines_added, lines_deleted, deletion_ratio_pct,
               structural_severity, structural_max_ratio,
               branch_age_days, temporal_status, temporal_score,
               semantic_status, semantic_is_deceptive, semantic_keyword,
               raw_json
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(run["id"]), pr_number, branch,
            tc.get("id"), tc.get("category"), tc.get("temporal_group", "stable"), run["created_at"],
            verdict.get("status"), verdict.get("severity"),
            verdict.get("severity_score"), exit_code,
            files.get("added"), files.get("deleted"), files.get("modified"),
            lines.get("added"), lines.get("deleted"),
            lines.get("deletion_ratio_percent"),
            struct.get("overall_severity"), struct.get("max_deletion_ratio_pct"),
            report.get("temporal", {}).get("branch_age_days"),
            td.get("status"), td_m.get("calculated_drift_score"),
            sem.get("status"), int(sem.get("is_deceptive", False)),
            sem.get("matched_keyword"),
            json.dumps(report),
        ),
    )
    conn.commit()

    if cur.lastrowid:
        for flag in struct.get("flagged_files", []):
            m = flag.get("metrics", {})
            conn.execute(
                """INSERT INTO structural_flags
                   (run_id, file_path, status, severity,
                    deleted_node_count, deletion_ratio_pct, deleted_components)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    cur.lastrowid, flag.get("file"),
                    flag.get("status"), flag.get("severity"),
                    m.get("deleted_node_count"),
                    m.get("structural_deletion_ratio"),
                    json.dumps(flag.get("deleted_components", [])),
                ),
            )
        conn.commit()
        return True
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest PayloadGuard scan results into SQLite")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--since", metavar="YYYY-MM-DD",
                        help="Only ingest runs created on or after this date")
    parser.add_argument("--db", default=str(DEFAULT_DB),
                        help=f"SQLite path (default: {DEFAULT_DB})")
    args = parser.parse_args()

    if not args.token:
        print("Error: set GITHUB_TOKEN or pass --token", file=sys.stderr)
        sys.exit(1)

    test_cases = json.loads(TEST_CASES_FILE.read_text())

    conn = init_db(args.db)
    seed_expected_verdicts(conn, test_cases)

    print(f"Fetching workflow runs from {OWNER}/{REPO} ...")
    runs = list_workflow_runs(args.token, args.since)
    print(f"Found {len(runs)} completed run(s)\n")

    new_count = skip_count = error_count = 0

    for run in runs:
        run_id = run["id"]
        branch = run.get("head_branch", "unknown")

        already = conn.execute(
            "SELECT 1 FROM scan_runs WHERE workflow_run_id = ?", (str(run_id),)
        ).fetchone()
        if already:
            skip_count += 1
            continue

        print(f"  [{branch}] run {run_id} ...", end="", flush=True)

        artifacts = list_artifacts(args.token, run_id)
        artifact = next((a for a in artifacts if a["name"] == ARTIFACT_NAME), None)

        if not artifact:
            print(" no artifact, skipping")
            error_count += 1
            continue

        try:
            zip_bytes = download_artifact_zip(args.token, artifact["id"])
            report = extract_json(zip_bytes)
            if report:
                verdict = report.get("verdict", {}).get("status", "?")
                inserted = insert_run(conn, run, report, test_cases)
                if inserted:
                    new_count += 1
                    print(f" {verdict}")
                else:
                    skip_count += 1
                    print(" duplicate")
            else:
                print(" empty artifact")
                error_count += 1
        except Exception as e:
            print(f" ERROR: {e}")
            error_count += 1

    conn.close()
    print(f"\nDone — {new_count} ingested, {skip_count} skipped, {error_count} errors")


if __name__ == "__main__":
    main()
