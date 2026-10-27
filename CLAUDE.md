# PayloadGuard Test Harness — Claude Code Context

## Handover (update this block at the end of every session)

- **Branch for next work:** create a new branch from main (both repos)
- **Analyser pin moved to the §H1 fix (2026-10-27, branch `pin/analyser-h1-fix`):** `.github/workflows/payloadguard.yml` pins analyser `a4bcaa4` (head of analyser PR #116: v1.6.0 + branch age can no longer decide DESTRUCTIVE; previously `6c3df91`, v1.6.0). Offline against harness `main` trees dated 2026-11-30 and 2027-06-01, v1.6.0 fails WS03/WS04/WS05/AW02/RTA03/RTA04 for age alone while this commit keeps them CAUTION and matches all 38 exit codes; at today's `main` both versions agree on every case. The pinned commit stays on analyser `main` when PR #116 is merged with a merge commit. No release yet: PyPI lists 1.6.0 and the GitHub Marketplace v1.5.0.
- **Scan history + live regression attempt (2026-10-26, branch `data/scan-history`):**
  - `tools/collect_history.py` writes `regression-reports/scan_history.jsonl` (one record per `PayloadGuard` check run on each fixture's head commit: verdict, severity, metrics, consequence detectors, analyser commit and version resolved from the workflow pin at the report's target commit, full report markdown) and `latest_regression_summary.md` (sweeps and latest scan per case). Workflow artifacts expire after 90 days, so the April–May `results.db` data is gone; the check runs are the surviving record. Collected: 423 scans, 2026-04-24 to 2026-05-31, 17 sweeps. The last sweep (2026-05-31 14:11 UTC, analyser `fe68338`) matches 34/34 exit codes and 33/34 verdicts against the current manifest (RTA01 SAFE, expected REVIEW). Unauthenticated collection costs about 40 API requests (limit 60/h).
  - Live regression run #27 (`40359379620`, full mode, `main` `defb060`) failed before reopening any PR: `REGRESSION_PAT` returns 401 (expired or revoked). The secret must be replaced before `regression.yml` can run.
  - Live sweep on the v1.6.0 pin (2026-10-26 16:45 UTC, `main` `defb060`): the 34 closed fixture PRs were reopened from the browser under the repository owner's session, scanned, and closed again without merging (REGRESSION_PAT returns 401, so `regression.yml` could not be used). 34/34 exit codes and 27/34 verdicts match; the seven mismatches (A03, A06, WS07, AW04, RT01–RT03) are SAFE-expected cases reading REVIEW through branch age alone, exactly as the offline preflight predicted. Reports now carry consequence-engine findings (shadow mode): D02/D03/D04 on the structural cases, D03/D04/D06 on A03, D03/D04 on A06, D08 on WS06, AW03, AW04 and RTA03. History now holds 457 scans, 18 sweeps.
  - `REGRESSION_PAT` replaced (2026-10-26). Run #27 attempt 3 (20:27 UTC) completed through `regression.yml`: 34 PRs reopened, scanned and closed, pass/fail enforcement skipped (no failures). The sweep is identical to the 16:45 browser sweep (34/34 exit codes, 27/34 verdicts, same seven age-only mismatches). History: 491 scans, 19 sweeps.
  - Offline preflight against `main` `defb060` (analyser v1.6.0, live PR bodies): 38/38 exit codes match. Fixture aging: Branch age is the target commit's date minus the fixture's commit date, so every new commit on `main` ages all fixtures at once (merging PR #78 on 2026-10-26 moved them from 4–37 days against the previous `main` commit, dated 2026-05-31, to 152–185 days). The stable group is not immune: CAUTION-expected stable cases (WS03, WS04, WS05, AW02, RTA03, RTA04) score 3 without age, 4 with the +1 beyond 90 days, and 5 = DESTRUCTIVE (exit 2) once the +2 beyond 180 days applies (`days_old > 180`, whole days). All six fixtures were committed on 2026-05-25, so any live run against a `main` commit dated from 2026-11-22 fails them for age alone. SAFE-expected stable cases (A03, A06, WS07, AW04, RT01–RT03) already read REVIEW; their exit code stays 0 until the +3 beyond 365 days lifts them to CAUTION, which still exits 0.
- **Analyser v1.6.0 offline verification (2026-10-26):** `validate_manifest.py --verify-consequence` 41/41 and `run_mutation_suite.py` 16/16 (0 FP / 0 FN) against analyser v1.6.0 (`6c3df91`, published to PyPI). `mutation-reports/` refreshed. The live workflow (`.github/workflows/payloadguard.yml`) now pins analyser `6c3df91` (v1.6.0; previously `fe68338`, v1.3.0). Pin check: the CLI run as the workflow runs it (PR head SHA, base `main`, live PR bodies, default `shadow` mode) gives identical verdicts, exit codes and scores under v1.3.0 and v1.6.0 on all 38 active cases, matching `expected_exit_code` 38/38. No live regression has been run on the new pin yet. v1.6.0 changes that affect harness behaviour: policy files are read from the base branch, the head is scanned by PR head SHA (fork PRs work), the `verdict` output reports REVIEW/CAUTION, and a `consequence-mode` input exists.
- **Status:** 41 test cases, 9 categories, 38 active branches + 3 pending GitHub 2026 API. `tools/test_cases.json` upgraded to Schema v2 (`2.0`) with `expected_consequence` oracle fields (`expected_detectors`, `forbidden_detectors`, `enforce_verdict`, `enforce_exit`, `min_reconciled_symbols`) and `tools/validate_manifest.py` (`--verify-consequence`). **Consequence Engine v1 (`consequence.v1` + `D01`–`D06` v2) oracle verification: 38/38 PASS (PR #74 `4e8e1df`, PR #75 `dcc5522`).**
- **A03/A06 resolution in Consequence Engine (`consequence.v1`):**
  - Legacy L3 (`shadow` mode): `A03` (`adversarial/slow-deletion`) and `A06` (`adversarial/threshold-gaming`) remain `SAFE (0)` for backward compatibility with existing L3 thresholds.
  - Consequence Engine (`enforce` mode): Both `A03` and `A06` are deterministically caught by `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK`, and `D06_GUARD_REGRESSION` → `DESTRUCTIVE (2)` while `T12` (`safe/large-rename`) is reconciled via `D01_RENAME_MOVE` (`reconciled_symbols=12`) → `SAFE (0)`.

- **Regression verification — 2026-06-01 (analyser SHA fe68338, v1.3.0) — COMPLETE 34/34:**
  - PASS (34/34): T03 (#8), T04 (#9), T05 (#10), T09 (#11), T10 (#12), T11 (#13), A01 (#14), A02 (#15), A03 (#16), A04 (#17), A05 (#18), A06 (#19), A07 (#20), A09 (#21), WS01 (#34), WS02 (#35), WS03 (#36), WS04 (#37), WS05 (#38), WS06 (#39), WS07 (#40), AW01 (#41), AW02 (#42), AW03 (#43), AW04 (#44), AW05 (#45), RTA01 (#49), RTA02 (#50), RTA03 (#51), RTA04 (#52), RTA05 (#53), RT02 (#64), RT01 (#65), RT03 (#66)
  - FAIL: none

- **PR map (stable cases):** PR #8=T03, #9=T04, #10=T05, #11=T09, #12=T10, #13=T11, #14=A01, #15=A02, #16=A03, #17=A04, #18=A05, #19=A06, #20=A07, #21=A09, #34=WS01, #35=WS02, #36=WS03, #37=WS04, #38=WS05, #39=WS06, #40=WS07, #41=AW01, #42=AW02, #43=AW03, #44=AW04, #45=AW05, #49=RTA01, #50=RTA02, #51=RTA03, #52=RTA04, #53=RTA05, #64=RT02, #65=RT01, #66=RT03

- **A03/A06 resolved (2026-06-01):** Both are documented bypass cases — SAFE is correct. A03: cross-file structural ratio ~8% < 20% threshold. A06: all metrics sub-threshold, no compound detection rule. Were returning DESTRUCTIVE only while PLI was active. Fixed: test_cases.json + HARNESS.md (PR #72).

- **Regression trigger:** `regression.yml` is `workflow_dispatch` only. Requires `REGRESSION_PAT` secret in both repos. The harness secret was replaced on 2026-10-26 after returning 401; run #27 attempt 3 succeeded with it.

- **Branch inventory (clean as of 2026-06-01):**
  - Analyser: `main`, `release/v1.2.0`, `DarkVader-PLG-vericode` (R&D — keep), `claude/oidc-typosquat-detection-UBCOJ`
  - Harness: `main`, `claude/oidc-typosquat-detection-UBCOJ`, `test/megalodon-simulation`, all 38 permanent fixture branches

---

## What This Repo Is

A controlled test repository for adversarially validating [PayloadGuard](https://github.com/PayloadGuard-PLG/payload-consequence-analyser). It contains no production code — all source files exist solely as diff targets for PayloadGuard to scan.

**Repos:**
- `PayloadGuard-PLG/payloadguard-test-harness` — this repo
- `PayloadGuard-PLG/payload-consequence-analyser` — the analyser under test

---

## Architecture

### Permanent branches (38 active)

Each branch holds a specific scenario. The regression runner reopens each as a PR, waits for PayloadGuard to scan it, closes it, and records the result.

### Category breakdown

| Category | Count | Track |
|---|---|---|
| `safe` | 3 | 1 |
| `destructive` | 2 | 1 |
| `boundary` | 1 | 1 |
| `semantic` | 2 | 1 |
| `multilang` | 1 | 1 |
| `adversarial` | 14 | 2 |
| `workflow-security` | 10 | 3 (7 active + 3 pending) |
| `red-team` | 5 | 4 |
| `runtime` | 3 | 5 |

### Temporal groups

- **stable** — strict pass/fail in every regression run
- **aging** — observational only; verdict drifts with branch age (T01, T02, T12, A10)

### Known bypasses

None active. RTA02 (`rta/schedule-curl-exfil`) was a known bypass until v1.2.0 — fixed by applying `_normalize_yaml_content()` to the `credential_harvest` loop. Expected verdict is now DESTRUCTIVE.

---

## Key Files

```
HARNESS.md           — full test case matrix (41 cases) + regression runner docs
TEST_SPEC.md         — per-branch specifications: change, expected layers, verdict
README.md            — brief overview and track summary
tools/test_cases.json       — ground truth (Schema v2 / 2.0): all registered cases with IDs, categories, expected verdicts, and expected_consequence oracles
tools/validate_manifest.py  — validates Schema v1+v2 integrity, branch refs, and live Consequence Engine v1 oracles (--verify-consequence)
tools/run_regression.py     — regression runner (modes: stable | temporal | full | runtime)
tools/ingest.py             — ingests scan results into SQLite
tools/dashboard.py          — Dash dashboard: regression matrix, history, threshold simulator
tools/collect_history.py    — scan history from PayloadGuard check runs; appends regression-reports/scan_history.jsonl, writes latest_regression_summary.md
tools/run_mutation_suite.py — offline mutation suite (10 adversarial + 6 benign mutations, shadow and enforce modes); writes mutation-reports/mutation_runs.jsonl and latest_mutation_summary.md
mutation-reports/           — mutation suite results (latest: analyser 1.6.0, 16/16)
regression-reports/         — live scan history (check runs; 491 scans 2026-04-24 to 2026-10-26)
```

---

## Running a Regression

```bash
export GITHUB_TOKEN=ghp_...   # needs: repo, pull_requests, actions:read

# Standard (34 stable cases, strict pass/fail)
python tools/run_regression.py --token "$GITHUB_TOKEN" --ingest

# Runtime cases only (RT01–RT03)
python tools/run_regression.py --token "$GITHUB_TOKEN" --mode runtime

# Full audit (all 38 active cases)
python tools/run_regression.py --token "$GITHUB_TOKEN" --mode full --ingest

# Record the scans in the permanent history (commit regression-reports/ afterwards)
python tools/collect_history.py --token "$GITHUB_TOKEN" --analyser-dir ../payload-consequence-analyser
```

---

## Adding a Test Case

1. Create a branch off `main` with the scenario changes.
2. Open a PR and confirm PayloadGuard scans it.
3. Close the PR (do not merge).
4. Add an entry to `tools/test_cases.json` with the next sequential ID.
5. Add a row to the HARNESS.md matrix.
6. Add a specification to TEST_SPEC.md under the appropriate track.
7. Update the category count in this file.

---

## Development Rules

- **Documentation style:** Professional and concise throughout. No informal or casual language. State facts directly.
- **CLAUDE.md is updated on every change.** Every case addition, category change, or doc update goes into the Handover block.
- **test_cases.json is the ground truth.** HARNESS.md and TEST_SPEC.md must stay in sync with it.
- **Pending cases (T23–T25):** Do not create branches until the GitHub 2026 APIs they depend on are available.
