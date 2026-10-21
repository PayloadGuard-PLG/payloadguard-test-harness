#!/usr/bin/env python3
"""
validate_manifest.py — Schema v1/v2 Validator & Consequence Oracle Verifier
===========================================================================

Validates `tools/test_cases.json` for:
  1. Legacy v1 compatibility (`id`, `category`, `temporal_group`,
     `expected_verdict`, `expected_exit_code`, `description`) and SQLite
     `seed_expected_verdicts` ingestion compatibility.
  2. Schema v2 fields (`schema_version`, `legacy_expected_verdict`,
     `legacy_expected_exit_code`, `security_desired_outcome`,
     `consequence_class`, `expected_findings`, `forbidden_findings`,
     `required_capabilities`).
  3. Git branch existence for all non-pending cases.
  4. Optional live consequence oracle verification (`--verify-consequence <analyser_dir>`)
     checking `expected_findings`, `forbidden_findings`, and `security_desired_outcome`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
MANIFEST_PATH = TOOLS_DIR / "test_cases.json"

VALID_VERDICTS = {"SAFE", "REVIEW", "CAUTION", "DESTRUCTIVE"}
VALID_EXIT_CODES = {0, 1, 2}
REQUIRED_V1_KEYS = {
    "id",
    "category",
    "temporal_group",
    "expected_verdict",
    "expected_exit_code",
    "description",
}
REQUIRED_V2_KEYS = {
    "schema_version",
    "legacy_expected_verdict",
    "legacy_expected_exit_code",
    "security_desired_outcome",
    "consequence_class",
    "expected_findings",
    "forbidden_findings",
    "required_capabilities",
}


def validate_manifest(manifest_path: Path = MANIFEST_PATH, check_git_branches: bool = True) -> list[str]:
    errors: list[str] = []
    if not manifest_path.exists():
        return [f"Manifest file not found: {manifest_path}"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"Invalid JSON in {manifest_path}: {e}"]

    if not isinstance(data, dict) or not data:
        return ["Top-level manifest must be a non-empty JSON object keyed by branch name."]

    seen_ids: set[str] = set()
    for branch, tc in data.items():
        if not isinstance(tc, dict):
            errors.append(f"{branch}: entry must be a JSON object")
            continue

        missing_v1 = REQUIRED_V1_KEYS - set(tc.keys())
        if missing_v1:
            errors.append(f"{branch}: missing required v1 keys {sorted(missing_v1)}")

        missing_v2 = REQUIRED_V2_KEYS - set(tc.keys())
        if missing_v2:
            errors.append(f"{branch}: missing required v2 keys {sorted(missing_v2)}")

        tc_id = tc.get("id")
        if tc_id in seen_ids:
            errors.append(f"{branch}: duplicate test case id '{tc_id}'")
        elif tc_id:
            seen_ids.add(tc_id)

        if tc.get("expected_verdict") not in VALID_VERDICTS:
            errors.append(f"{branch} ({tc_id}): invalid expected_verdict '{tc.get('expected_verdict')}'")
        if tc.get("legacy_expected_verdict") not in VALID_VERDICTS:
            errors.append(f"{branch} ({tc_id}): invalid legacy_expected_verdict '{tc.get('legacy_expected_verdict')}'")
        if tc.get("security_desired_outcome") not in VALID_VERDICTS:
            errors.append(f"{branch} ({tc_id}): invalid security_desired_outcome '{tc.get('security_desired_outcome')}'")
        if tc.get("expected_exit_code") not in VALID_EXIT_CODES:
            errors.append(f"{branch} ({tc_id}): invalid expected_exit_code '{tc.get('expected_exit_code')}'")
        if tc.get("schema_version") != "2.0":
            errors.append(f"{branch} ({tc_id}): expected schema_version '2.0', got '{tc.get('schema_version')}'")
        if not isinstance(tc.get("expected_findings"), list):
            errors.append(f"{branch} ({tc_id}): expected_findings must be a list")
        if not isinstance(tc.get("forbidden_findings"), list):
            errors.append(f"{branch} ({tc_id}): forbidden_findings must be a list")
        if not isinstance(tc.get("required_capabilities"), list) or not tc.get("required_capabilities"):
            errors.append(f"{branch} ({tc_id}): required_capabilities must be a non-empty list")

    # Verify compatibility with tools/ingest.py SQLite seeding
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE expected_verdicts (
                test_case_id TEXT PRIMARY KEY,
                category TEXT,
                temporal_group TEXT,
                expected_verdict TEXT,
                expected_exit_code INTEGER,
                description TEXT
            )"""
        )
        for branch, tc in data.items():
            conn.execute(
                """INSERT OR REPLACE INTO expected_verdicts
                   (test_case_id, category, temporal_group, expected_verdict, expected_exit_code, description)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    tc["id"],
                    tc["category"],
                    tc.get("temporal_group", "stable"),
                    tc["expected_verdict"],
                    tc["expected_exit_code"],
                    tc["description"],
                ),
            )
        conn.commit()
    except Exception as e:
        errors.append(f"SQLite ingest compatibility check failed: {e}")

    # Verify active branches exist in git (local or origin/)
    if check_git_branches:
        try:
            proc = subprocess.run(
                ["git", "branch", "-a", "--format=%(refname:short)"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            refs = set(proc.stdout.splitlines())
            for branch, tc in data.items():
                if tc.get("status") == "pending-2026-api":
                    continue
                if branch not in refs and f"origin/{branch}" not in refs:
                    errors.append(f"{branch} ({tc.get('id')}): branch not found in local or origin refs")
        except Exception as e:
            errors.append(f"Git branch check failed: {e}")

    return errors


def verify_consequence_oracle(analyser_dir: Path, manifest_path: Path = MANIFEST_PATH) -> list[str]:
    sys.path.insert(0, str(analyser_dir.resolve()))
    from analyze import PayloadAnalyzer, load_config

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for branch, tc in data.items():
        if tc.get("status") == "pending-2026-api":
            continue
        tc_id = tc["id"]
        cfg = load_config(str(REPO_ROOT))
        cfg.consequence["mode"] = "enforce"
        rep = PayloadAnalyzer(str(REPO_ROOT), branch, "main", config=cfg).analyze(
            pr_description=tc.get("pr_description", "")
        )
        if "error" in rep:
            failures.append(f"{tc_id} ({branch}): analyzer error: {rep['error']}")
            continue

        ca = rep.get("consequence_analysis", {})
        findings = ca.get("findings", [])
        actual_detectors = {f["detector_id"] for f in findings}
        actual_classes = {f["consequence_class"] for f in findings}

        # Check expected findings
        for exp in tc.get("expected_findings", []):
            exp_det = exp.get("detector_id")
            exp_cls = exp.get("consequence_class")
            matched = [
                f for f in findings
                if (not exp_det or f["detector_id"] == exp_det)
                and (not exp_cls or f["consequence_class"] == exp_cls)
            ]
            if not matched:
                failures.append(
                    f"{tc_id} ({branch}): missing expected finding {exp} "
                    f"(actual detectors={sorted(actual_detectors)}, classes={sorted(actual_classes)})"
                )

        # Check forbidden findings
        for forb in tc.get("forbidden_findings", []):
            if forb in actual_detectors or forb in actual_classes:
                failures.append(
                    f"{tc_id} ({branch}): forbidden finding '{forb}' fired "
                    f"(actual detectors={sorted(actual_detectors)}, classes={sorted(actual_classes)})"
                )

        # Check security_desired_outcome exit-code equivalence in enforce mode for non-aging cases
        if tc.get("temporal_group") == "stable":
            desired = tc["security_desired_outcome"]
            actual_enforce_verdict = rep["verdict"]["status"]
            if desired == "DESTRUCTIVE" and actual_enforce_verdict != "DESTRUCTIVE":
                failures.append(
                    f"{tc_id} ({branch}): security_desired_outcome is DESTRUCTIVE, "
                    f"but enforce mode returned {actual_enforce_verdict}"
                )
            elif desired == "SAFE" and actual_enforce_verdict == "DESTRUCTIVE":
                failures.append(
                    f"{tc_id} ({branch}): security_desired_outcome is SAFE, "
                    f"but enforce mode returned DESTRUCTIVE"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tools/test_cases.json Schema v2 and consequence oracle.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH, help="Path to test_cases.json")
    parser.add_argument("--no-git-check", action="store_true", help="Skip git branch existence check")
    parser.add_argument("--verify-consequence", type=Path, default=None, metavar="ANALYSER_DIR",
                        help="Run live consequence oracle checks using PayloadAnalyzer from ANALYSER_DIR")
    args = parser.parse_args()

    errors = validate_manifest(args.manifest, check_git_branches=not args.no_git_check)
    if errors:
        print(f"Manifest validation FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(f"OK: {len(data)} test case entries in {args.manifest.name} passed Schema v1+v2 and SQLite validation.")

    if args.verify_consequence:
        oracle_failures = verify_consequence_oracle(args.verify_consequence, args.manifest)
        if oracle_failures:
            print(f"Consequence oracle verification FAILED with {len(oracle_failures)} error(s):", file=sys.stderr)
            for fail in oracle_failures:
                print(f"  - {fail}", file=sys.stderr)
            return 1
        print("OK: All active permanent branches passed Consequence Engine v1 oracle assertions.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
