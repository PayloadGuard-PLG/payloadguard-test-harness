# PayloadGuard Test Harness

A controlled test repository for validating and adversarially testing [PayloadGuard](https://github.com/PayloadGuard-PLG/payload-consequence-analyser).

## Purpose

This repo exists to:
- Generate repeatable, controlled PRs that PayloadGuard scans
- Validate consistent verdicts across identical inputs
- Stress test edge cases and known limitations
- Record scan results in `tools/db/results.db` for regression history and the dashboard

## Structure

```
payloadguard-test-harness/
├── .github/workflows/   # PayloadGuard CI workflow
├── auth.py              # Python: Auth class, login/logout
├── database.py          # Python: Database class, connect/query/disconnect
├── api.js               # JS: fetchUser, createUser, deleteUser
├── services.ts          # TS: UserService, ApiClient interfaces
├── utils.go             # Go: HandleRequest, NewConfig, Server
├── test_auth.py         # 5 auth tests
├── test_database.py     # 5 database tests
├── settings.yml         # App configuration
├── HARNESS.md           # Full test case matrix (41 cases, 9 categories + Consequence Engine v1 oracle)
├── TEST_SPEC.md         # Per-branch specifications: change, expected layers, verdict, consequence oracle
├── tools/
│   ├── test_cases.json      # Schema v2 (2.0) ground-truth manifest with expected_consequence assertions
│   ├── validate_manifest.py # Schema v1+v2 validator & --verify-consequence oracle runner
│   ├── run_regression.py    # Automated PR regression runner
│   ├── ingest.py            # SQLite ingestion for scan artifacts
│   └── dashboard.py         # Dash visual regression & threshold simulator
└── requirements.txt
```

## Consequence Engine (`consequence.v1`) Validation

`tools/test_cases.json` (Schema v2 `2.0`) defines both legacy L3 expected verdicts (`expected_verdict`, `expected_exit`) and SCG Consequence Engine assertions (`expected_consequence`) for cases such as `A03` (`adversarial/slow-deletion`), `A06` (`adversarial/threshold-gaming`), `T12` (`safe/large-rename`), and `T01` (`safe/small-additive`).

Run the local manifest and consequence oracle verifier across all 38 active permanent branches:

```bash
python tools/validate_manifest.py --verify-consequence ../payload-consequence-analyser
```

## Test Branches

41 test cases across 9 categories. See [`HARNESS.md`](HARNESS.md) for the full matrix and [`TEST_SPEC.md`](TEST_SPEC.md) for per-branch specifications.

**Track 1 — Validation** (`safe/`, `destructive/`, `boundary/`, `semantic/`, `multilang/`)
Confirms PayloadGuard behaves as specified on canonical inputs.

**Track 2 — Adversarial** (`adversarial/`)
Static evasion techniques: deletion obfuscation, threshold gaming, workflow poisoning bypasses.

**Track 3 — Workflow Security** (`workflow-security/`)
L2c signal coverage — 7 active cases, 3 reserved for pending GitHub 2026 API features.

**Track 4 — Red Team** (`rta/`)
Live findings from the 2026-05-25 red-team session. Confirmed detections (RTA01–RTA05); RTA02 was a bypass until analyser v1.2.0 and is now detected (DESTRUCTIVE).

**Track 5 — Runtime** (`runtime/`)
L5c eBPF agent event coverage — procmem, egress, and ptrace scenarios. Static verdict is SAFE; layer fires advisory events only.

## Reports

Each scan uploads its JSON report as the `payloadguard-results` workflow artifact. `tools/run_regression.py --ingest` collects the artifacts into `tools/db/results.db`, which `tools/dashboard.py` reads.

Offline checks that need no live PRs: `tools/validate_manifest.py --verify-consequence <analyser_dir>` (consequence oracle) and `tools/run_mutation_suite.py --analyser-dir <analyser_dir>` (writes `mutation-reports/`). Against analyser v1.6.0: 41/41 and 16/16.

---

*This repo contains no production code. All source files exist solely as diff targets.*
