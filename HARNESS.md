# PayloadGuard — Regression Harness

Reference implementation for validating CI/CD consequence analysis tools under adversarial conditions.

**Repository:** `payloadguard-plg/payloadguard-test-harness`  
**Analyser:** `payloadguard-plg/payload-consequence-analyser`

---

## Overview

This harness registers 41 test cases across 38 active branches. Three cases (T23–T25) are reserved and have no branches — they will be created when the GitHub 2026 APIs they depend on are available. A full regression cycle reopens all active branches as pull requests, waits for PayloadGuard to scan each, closes them, and ingests the results into a local SQLite database for analysis.

| Category | Count | Purpose |
|---|---|---|
| `safe` | 3 | Zero-noise baseline — any DESTRUCTIVE result is a false positive |
| `destructive` | 2 | Canonical payloads — any non-DESTRUCTIVE result is a miss |
| `boundary` | 1 | Metrics just above threshold — confirms score crosses boundary |
| `semantic` | 2 | Transparency and description alignment |
| `multilang` | 1 | Parser stress test across JS, TS, Go |
| `adversarial` | 14 | Static evasion techniques: deletion obfuscation, threshold gaming, workflow poisoning bypasses |
| `red-team` | 5 | Live red-team findings from the 2026-05-25 session — confirmed detections and known bypasses |
| `runtime` | 3 | L5c eBPF agent event coverage — procmem, egress, ptrace (advisory, no score impact) |
| `workflow-security` | 10 | L2c signal coverage (7 active) + pending GitHub 2026 API features (3 reserved) |

---

## Test Case Matrix

The `temporal_group` column indicates how each case is treated by the regression runner:
- **stable** — strict pass/fail, always compared against `expected_verdict`
- **aging** — observational only; verdict will drift as branches age (see [Temporal Groups](#temporal-groups))

| ID | Branch | Category | Group | Expected | Description |
|---|---|---|---|---|---|
| T01 | safe/small-additive | safe | aging | SAFE | Add health_check() — zero-noise baseline |
| T02 | safe/docs-only | safe | aging | SAFE | README additions only |
| T12 | safe/large-rename | safe | aging | SAFE | Three class renames — L4 false positive check |
| T03 | destructive/mass-deletion | destructive | stable | DESTRUCTIVE | Delete auth.py + database.py |
| T04 | destructive/april-2026-replica | destructive | stable | DESTRUCTIVE | April 2026 incident replica |
| T05 | boundary/structural-threshold | boundary | stable | DESTRUCTIVE | 4 methods removed from auth.py (~23.5% ratio) |
| T09 | semantic/no-description | semantic | stable | DESTRUCTIVE | No PR description, database.py deleted |
| T10 | semantic/honest-critical | semantic | stable | DESTRUCTIVE | Honest BREAKING CHANGE description, auth deleted |
| T11 | multilang/structural-js-ts-go | multilang | stable | DESTRUCTIVE | Structural deletions across JS, TS, Go |
| A01 | adversarial/keyword-evasion | adversarial | stable | DESTRUCTIVE | Deceptive description, no benign trigger words |
| A02 | adversarial/rename-smuggling | adversarial | stable | DESTRUCTIVE | auth.py renamed to identity.py, contents gutted |
| A03 | adversarial/slow-deletion | adversarial | stable | DESTRUCTIVE | 1 function removed from each of 5 files |
| A04 | adversarial/addition-camouflage | adversarial | stable | DESTRUCTIVE | 300-line api.js addition + auth.py deleted |
| A05 | adversarial/nested-gutting | adversarial | stable | DESTRUCTIVE | Auth class shell preserved, all methods deleted |
| A06 | adversarial/threshold-gaming | adversarial | stable | DESTRUCTIVE | Every metric tuned just below threshold (known miss) |
| A07 | adversarial/new-file-replacement | adversarial | stable | DESTRUCTIVE | auth.py deleted, auth_v2.py stub added |
| A09 | adversarial/config-only-deletion | adversarial | stable | DESTRUCTIVE | settings.yml + requirements.txt deleted |
| A10 | adversarial/unicode-payload | adversarial | aging | SAFE | Hostile Unicode in comments, +4/-1 — robustness test |
| WS01 | workflow-security/base64-payload | workflow-security | stable | DESTRUCTIVE | base64_payload CRITICAL — L2c signal test |
| WS02 | workflow-security/credential-harvest | workflow-security | stable | DESTRUCTIVE | credential_harvest CRITICAL — AWS metadata + env dump |
| WS03 | workflow-security/dormant-trigger | workflow-security | stable | DESTRUCTIVE | dormant_trigger_with_payload HIGH + L2b content scan |
| WS04 | workflow-security/forged-bot-author | workflow-security | stable | CAUTION | forged_bot_author HIGH — git config bot identity |
| WS05 | workflow-security/oidc-elevation | workflow-security | stable | CAUTION | oidc_elevation_no_consumer HIGH — no OIDC consumer |
| WS06 | workflow-security/prt-write-permissions | workflow-security | stable | DESTRUCTIVE | pull_request_target + write permissions CRITICAL |
| WS07 | workflow-security/safe-clean-workflow | workflow-security | stable | SAFE | Clean workflow — no false positive check |
| AW01 | adversarial/workflow-yaml-folded-block | adversarial | stable | DESTRUCTIVE | base64 split across YAML folded block lines |
| AW02 | adversarial/workflow-prt-only | adversarial | stable | CAUTION | pull_request_target alone (no write perms) HIGH |
| AW03 | adversarial/workflow-typosquatted-oidc | adversarial | stable | DESTRUCTIVE | oidc_elevation_typosquatted CRITICAL — aws-actions-unofficial/ |
| AW04 | adversarial/workflow-legitimate-oidc | adversarial | stable | SAFE | Legitimate aws-actions/ consumer — no false positive |
| AW05 | adversarial/workflow-modified-poison | adversarial | stable | DESTRUCTIVE | Poisoned workflow via M-type diff (not just A-type) |
| RTA01 | rta/push-rm-rf | red-team | stable | REVIEW | rm -rf in workflow — L2 content scan |
| RTA02 | rta/schedule-curl-exfil | red-team | stable | DESTRUCTIVE | Fixed in v1.2.0 — `_normalize_yaml_content()` applied to credential_harvest loop |
| RTA03 | rta/prt-untrusted-checkout | red-team | stable | CAUTION | pull_request_target + untrusted head.sha checkout |
| RTA04 | rta/github-env-injection | red-team | stable | CAUTION | PATH/LD_PRELOAD via $GITHUB_ENV — Signal 7 |
| RTA05 | rta/variable-obfuscated-b64 | red-team | stable | DESTRUCTIVE | Variable-obfuscated base64 payload |
| RT01 | runtime/procmem-read | runtime | stable | SAFE | Opens /proc/self/mem — eBPF emits procmem_open event (advisory) |
| RT02 | runtime/postinstall-curl | runtime | stable | SAFE | Curls loopback 127.0.0.1:9999 — eBPF emits egress_connect (loopback allowed) |
| RT03 | runtime/ptrace-self | runtime | stable | SAFE | PTRACE_TRACEME self-attach — eBPF emits ptrace_attach event (advisory) |
| T23 | workflow-security/dependency-lock-tampering | workflow-security | stable | DESTRUCTIVE | **Pending GitHub 2026 API** |
| T24 | workflow-security/policy-bypass | workflow-security | stable | DESTRUCTIVE | **Pending GitHub 2026 API** |
| T25 | workflow-security/secret-exfiltration | workflow-security | stable | DESTRUCTIVE | **Pending GitHub 2026 API** |

---

## Running a Regression

### Prerequisites

```bash
pip install requests PyGithub
export GITHUB_TOKEN=ghp_...   # needs: repo, pull_requests, actions:read
```

### Full cycle

```bash
# Standard regression — 34 stable cases, strict pass/fail
python tools/run_regression.py --token "$GITHUB_TOKEN" --ingest

# Observe temporal drift — 4 aging cases, no pass/fail
python tools/run_regression.py --token "$GITHUB_TOKEN" --mode temporal

# Full audit — all active cases (stable=strict, aging=observational)
python tools/run_regression.py --token "$GITHUB_TOKEN" --mode full --ingest

# L5c runtime cases only (RT01–RT03)
python tools/run_regression.py --token "$GITHUB_TOKEN" --mode runtime

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
  --mode MODE         stable (default) | temporal | full | runtime
  --ingest            Chain to ingest.py after all scans complete
  --dry-run           Print what would be reopened without acting
  --timeout N         Seconds to wait for scans (default: 300)

ingest.py
  --token TOKEN       GitHub token
  --db PATH           SQLite path (default: tools/db/results.db)
  --since YYYY-MM-DD  Only ingest runs on or after this date

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

## Temporal Groups

PayloadGuard's branch age scoring adds +1 to the verdict score after 90 days, +2 after 180, +3 after 365. For DESTRUCTIVE-expected cases this is harmless — the verdict doesn't change. For SAFE-expected cases the verdict can drift to REVIEW (and eventually CAUTION) as branches age, even though the diff itself is unchanged.

The harness handles this with two groups:

| Group | Cases | Behaviour |
|---|---|---|
| **stable** | All DESTRUCTIVE-expected cases | Strict pass/fail — regression fails if verdict is wrong |
| **aging** | T01, T02, T12, A10 (SAFE-expected) | Observational — verdicts recorded but not checked against expected |

**Why keep the aging cases at all?** They are a longitudinal dataset. Running `--mode temporal` every few weeks lets you watch exactly when and how the branch age signal fires, which is useful for tuning the `branch_age_days` thresholds in `payloadguard.yml`. The drift progression SAFE → REVIEW → CAUTION is the tool working correctly — not a bug.

**When aging cases need refreshing:** If T01/T02/T12/A10 reach CAUTION (score 3–4) and you want to reset the clock, create fresh branches off current main, open new PRs, and update `test_cases.json` with the new branch names. The old branches can be archived (left closed) for historical reference.

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
