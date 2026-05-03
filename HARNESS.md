# PayloadGuard — Regression Harness

Reference implementation for validating CI/CD consequence analysis tools under adversarial conditions.

**Repository:** `payloadguard-plg/payloadguard-test-harness`  
**Analyser:** `payloadguard-plg/payload-consequence-analyser`

---

## Overview

This harness maintains 18 permanent branches, each representing a distinct scenario that PayloadGuard must handle correctly. A full regression cycle reopens all 18 as pull requests, waits for PayloadGuard to scan each, closes them, and ingests the results into a local SQLite database for analysis.

The suite covers five scenario families:

| Category | Count | Purpose |
|---|---|---|
| `safe` | 3 | Zero-noise baseline — any DESTRUCTIVE result is a false positive |
| `destructive` | 2 | Canonical payloads — any non-DESTRUCTIVE result is a miss |
| `boundary` | 1 | Metrics just above threshold — confirms score crosses boundary |
| `semantic` | 2 | Transparency and description alignment |
| `multilang` | 1 | Parser stress test across JS, TS, Go |
| `adversarial` | 9 | Purpose-built evasion techniques |
| `workflow-security` | 3 | Reserved for GitHub 2026 API features (pending) |

---

## Test Case Matrix

| ID | Branch | Category | Expected | Description |
|---|---|---|---|---|
| T01 | safe/small-additive | safe | SAFE | Add health_check() — zero-noise baseline |
| T02 | safe/docs-only | safe | SAFE | README additions only |
| T12 | safe/large-rename | safe | SAFE | Three class renames — L4 false positive check |
| T03 | destructive/mass-deletion | destructive | DESTRUCTIVE | Delete auth.py + database.py |
| T04 | destructive/april-2026-replica | destructive | DESTRUCTIVE | April 2026 incident replica |
| T05 | boundary/structural-threshold | boundary | DESTRUCTIVE | 4 methods removed from auth.py (~23.5% ratio) |
| T09 | semantic/no-description | semantic | DESTRUCTIVE | No PR description, database.py deleted |
| T10 | semantic/honest-critical | semantic | DESTRUCTIVE | Honest BREAKING CHANGE description, auth deleted |
| T11 | multilang/structural-js-ts-go | multilang | DESTRUCTIVE | Structural deletions across JS, TS, Go |
| A01 | adversarial/keyword-evasion | adversarial | DESTRUCTIVE | Deceptive description, no benign trigger words |
| A02 | adversarial/rename-smuggling | adversarial | DESTRUCTIVE | auth.py renamed to identity.py, contents gutted |
| A03 | adversarial/slow-deletion | adversarial | DESTRUCTIVE | 1 function removed from each of 5 files |
| A04 | adversarial/addition-camouflage | adversarial | DESTRUCTIVE | 300-line api.js addition + auth.py deleted |
| A05 | adversarial/nested-gutting | adversarial | DESTRUCTIVE | Auth class shell preserved, all methods deleted |
| A06 | adversarial/threshold-gaming | adversarial | DESTRUCTIVE | Every metric tuned just below threshold (known miss) |
| A07 | adversarial/new-file-replacement | adversarial | DESTRUCTIVE | auth.py deleted, auth_v2.py stub added |
| A09 | adversarial/config-only-deletion | adversarial | DESTRUCTIVE | settings.yml + requirements.txt deleted |
| A10 | adversarial/unicode-payload | adversarial | SAFE | Hostile Unicode in comments, +4/-1 — robustness test |
| T23 | workflow-security/dependency-lock-tampering | workflow-security | DESTRUCTIVE | **Pending GitHub 2026 API** |
| T24 | workflow-security/policy-bypass | workflow-security | DESTRUCTIVE | **Pending GitHub 2026 API** |
| T25 | workflow-security/secret-exfiltration | workflow-security | DESTRUCTIVE | **Pending GitHub 2026 API** |

---

## Running a Regression

### Prerequisites

```bash
pip install requests PyGithub
export GITHUB_TOKEN=ghp_...   # needs: repo, pull_requests, actions:read
```

### Full cycle

```bash
# Reopen all PRs → wait for scans → close → ingest → display pass rate
python tools/run_regression.py --token "$GITHUB_TOKEN" --ingest

# Ingest only (if scans already ran)
python tools/ingest.py --token "$GITHUB_TOKEN"

# Launch dashboard
python tools/dashboard.py
# Open http://127.0.0.1:8050
```

### Options

```
run_regression.py
  --token TOKEN       GitHub token (or set GITHUB_TOKEN env var)
  --ingest            Chain to ingest.py after all scans complete
  --dry-run           Print what would be reopened without acting

ingest.py
  --token TOKEN       GitHub token
  --db PATH           SQLite path (default: tools/db/results.db)
  --limit N           Max runs to pull (default: 50)

dashboard.py
  --db PATH           SQLite path (default: tools/db/results.db)
  --port PORT         Dash server port (default: 8050)
  --host HOST         Bind address (default: 127.0.0.1)
```

---

## Dashboard

Three tabs:

**Regression Matrix** — pass/fail grid across all test cases and run dates. Green = correct verdict, red = wrong.

**Test History** — per-test-case score timeline with layer detail for the latest run. Threshold line overlaid at the expected verdict boundary.

**Threshold Simulator** — re-scores all stored raw JSON reports at adjustable thresholds (structural ratio, min nodes, temporal, score cutoffs). Shows which verdicts would flip before touching any code.

The **Last Run** card links directly to the GitHub Actions workflow run that produced the data.

---

## Database Schema

```sql
scan_runs (
    id                    INTEGER PRIMARY KEY,
    workflow_run_id       TEXT UNIQUE,
    test_case_id          TEXT,
    category              TEXT,
    run_at                TEXT,          -- ISO 8601 UTC
    ingested_at           TEXT,
    verdict_status        TEXT,          -- SAFE / REVIEW / CAUTION / DESTRUCTIVE
    verdict_score         REAL,
    exit_code             INTEGER,       -- 0 / 1 / 2
    files_deleted         INTEGER,
    lines_deleted         INTEGER,
    deletion_ratio_pct    REAL,
    structural_severity   TEXT,
    structural_max_ratio  REAL,
    semantic_status       TEXT,
    raw_json              TEXT           -- full payloadguard-report.json
)

structural_flags (
    id                    INTEGER PRIMARY KEY,
    scan_run_id           INTEGER REFERENCES scan_runs,
    file_path             TEXT,
    deleted_node_count    INTEGER,
    structural_del_ratio  REAL
)

expected_verdicts (
    test_case_id          TEXT PRIMARY KEY,
    expected_verdict      TEXT,
    expected_exit_code    INTEGER
)
```

---

## Adding a Test Case

1. Create a branch off `main` in this repo with your scenario changes.
2. Open a PR against `main` and confirm PayloadGuard scans it.
3. Close the PR (do not merge).
4. Add an entry to `tools/test_cases.json`:

```json
"your-category/branch-name": {
  "id": "T26",
  "category": "adversarial",
  "expected_verdict": "DESTRUCTIVE",
  "expected_exit_code": 2,
  "description": "What this tests and why it matters."
}
```

5. Run `python tools/ingest.py` to seed `expected_verdicts` with the new entry.
6. Run a full regression to confirm the new case passes.

---

## Known Limitations

**A06 (threshold-gaming)** is the only currently failing case. Every metric sits just below its individual threshold — the scoring model has no compound detection rule. This is a known limitation documented in the analyser's `WHITEPAPER.md §8.1` and `AUDIT_LOG.md`.

**T23–T25** are reserved for GitHub 2026 APIs not yet available. Their branches do not exist. They will be created when the relevant APIs ship (dependency locking, policy controls, egress firewall hooks).

---

## GitHub 2026 Roadmap Fit

This harness is designed to grow alongside GitHub's 2026 security roadmap:

| Roadmap Pillar | Harness Coverage |
|---|---|
| Hardened CI/CD infrastructure | T03, T04, A02, A07, A09 — binary, permission, config deletion |
| Policy controls | T09, T10, A01 — semantic transparency and deceptive description detection |
| Real-time observability | Dashboard shows per-run layer breakdown with drill-down |
| AI governance | Full suite validates PayloadGuard catches AI-generated destructive PRs |
| Workflow dependency security | T23–T25 (pending 2026 API) |
