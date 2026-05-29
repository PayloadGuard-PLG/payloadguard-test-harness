# PayloadGuard Test Harness — Claude Code Context

## Handover (update this block at the end of every session)

- **Branch for next work:** create a new branch from main
- **Status:** 41 test cases, 9 categories, 38 active branches + 3 pending GitHub 2026 API. Docs in sync.
- **PLI enabled (2026-05-29):** `payloadguard.yml` now pins analyser at `76139e9` (v1.3.0) with `pli-analysis: true` and `PLI_API_KEY` secret. All PR scans now run PLI Layer L4b full mode. Merged via PR #62.
- **Next action:** Run PLI comparison regression — `python tools/run_regression.py --token "$GITHUB_TOKEN" --mode stable --ingest`. Check `payloadguard-report.json` artifacts for `"pli"` key: `mode`, `consistency_score`, `findings`. Cases where verdict shifts vs v1.2.0 baseline measure PLI detection improvement. Semantic category cases are the primary signal.
- **Secrets required:** `PLI_API_KEY` (Anthropic API key) must be set in this repo's secrets for full L2/LLM mode.
- **Regression trigger:** `regression.yml` now accepts `repository_dispatch` (type: `analyser-updated`) fired by the analyser on push to main. Runs `stable` mode (34 cases, strict). Daily schedule at 02:00 UTC runs `full` mode for drift observation. Requires `REGRESSION_PAT` secret in both repos.

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
