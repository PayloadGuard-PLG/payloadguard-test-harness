# PayloadGuard Test Harness — Claude Code Context

## Handover (update this block at the end of every session)

- **Branch for next work:** `claude/oidc-typosquat-detection-UBCOJ` (both repos)
- **Status:** 41 test cases, 9 categories, 38 active branches + 3 pending GitHub 2026 API. `payloadguard.yml` pins analyser at `fe68338` (main v1.3.0). WS03 corrected DESTRUCTIVE→CAUTION (PR #71, merged 2026-05-31). A03+A06 corrected DESTRUCTIVE→SAFE (PR #72, 2026-06-01).

- **A03/A06 resolved (2026-06-01):** The "SHA regression" framing from the prior session was incorrect. analyze.py is functionally identical between `5dd6a072` and `fe68338` — only cleanup changes separate them (unused import, dead hasattr guard, _iter_workflow_file_diffs helper), none affecting scoring. A03 and A06 are documented bypass cases where SAFE is the correct result. A03's cross-file structural ratio is ~8%, below the 20% threshold. A06 has all metrics sub-threshold with no compound detection rule. Both were temporarily returning DESTRUCTIVE only while PLI was active (2026-05-29); after PLI was reverted the expectations were not corrected. Fixed: test_cases.json, HARNESS.md updated DESTRUCTIVE→SAFE. TEST_SPEC.md was already correct.

- **Regression verification — 2026-05-31 14:12 UTC (analyser SHA fe68338):**
  - PASS (30 confirmed after expectation fix): T03 (#8), T04 (#9), T05 (#10), T09 (#11), T10 (#12), T11 (#13), A01 (#14), A02 (#15), **A03 (#16)**, A04 (#17), A05 (#18), **A06 (#19)**, WS01 (#34), WS02 (#35), WS03 (#36), WS04 (#37), WS05 (#38), WS06 (#39), WS07 (#40), AW01 (#41), AW02 (#42), AW03 (#43), AW04 (#44), AW05 (#45), RTA01 (#49), RTA02 (#50), RTA05 (#53), RT03 (#66)
  - FAIL: none
  - UNVERIFIED (6 — MCP token expired mid-run): A07 PR #20, A09 PR #21, RTA03 PR #51, RTA04 PR #52, RT02 PR #64, RT01 PR #65. Re-verify on next regression run.

- **PR map (stable cases):** PR #8=T03, #9=T04, #10=T05, #11=T09, #12=T10, #13=T11, #14=A01, #15=A02, #16=A03, #17=A04, #18=A05, #19=A06, #20=A07, #21=A09, #34=WS01, #35=WS02, #36=WS03, #37=WS04, #38=WS05, #39=WS06, #40=WS07, #41=AW01, #42=AW02, #43=AW03, #44=AW04, #45=AW05, #49=RTA01, #50=RTA02, #51=RTA03, #52=RTA04, #53=RTA05, #64=RT02, #65=RT01, #66=RT03

- **PLI evaluation summary (2026-05-29):** 34-case stable regression with PLI full L2/LLM mode active. True positives: A03 SAFE→DESTRUCTIVE, A06 SAFE→DESTRUCTIVE. False positives: WS07 SAFE→DESTRUCTIVE, RT02 SAFE→DESTRUCTIVE, RTA03 CAUTION→DESTRUCTIVE. Root cause: PLI L2 LLM treats diff summaries as blank AI responses. PLI reverted. Net score unchanged at 30/34 pass.

- **Regression trigger:** `regression.yml` is `workflow_dispatch` only (schedule and `repository_dispatch` removed). Requires `REGRESSION_PAT` secret in both repos.

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
tools/test_cases.json       — ground truth: all registered cases with IDs, categories, expected verdicts
tools/run_regression.py     — regression runner (modes: stable | temporal | full | runtime)
tools/ingest.py             — ingests scan results into SQLite
tools/dashboard.py          — Dash dashboard: regression matrix, history, threshold simulator
tools/gen_test_registry.py  — regenerates test registry from live pytest run (not used in harness)
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
