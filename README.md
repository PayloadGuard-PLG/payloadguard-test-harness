# PayloadGuard Test Harness

A controlled test repository for validating and adversarially testing [PayloadGuard](https://github.com/PayloadGuard-PLG/payload-consequence-analyser).

## Purpose

This repo exists to:
- Generate repeatable, controlled PRs that PayloadGuard scans
- Validate consistent verdicts across identical inputs
- Stress test edge cases and known limitations
- Feed scan reports into `payload-consequence-analyser/test-reports/`

## Installation

```bash
pip install payloadguard-plg
```

Or wire directly into your workflow:

```yaml
- uses: DarkVader-PLG/payload-consequence-analyser@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    app-id: ${{ secrets.APP_ID }}
    private-key: ${{ secrets.PRIVATE_KEY }}
```

## Quick Start

1. Install the PayloadGuard GitHub App on your repository
2. Add `.github/workflows/payloadguard.yml` (see the action repo for the template)
3. Open a pull request — PayloadGuard scans it automatically and posts a verdict

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
├── HARNESS.md           # Full test case matrix (41 cases, 9 categories)
├── TEST_SPEC.md         # Per-branch specifications: change, expected layers, verdict
└── requirements.txt
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
Live findings from the 2026-05-25 red-team session. Confirmed detections (RTA01, RTA03–05) and known bypass (RTA02).

**Track 5 — Runtime** (`runtime/`)
L5c eBPF agent event coverage — procmem, egress, and ptrace scenarios. Static verdict is SAFE; layer fires advisory events only.

## Reports

Each PayloadGuard scan produces a JSON report saved to:
`payload-consequence-analyser/test-reports/runs/`

See that repo for aggregated results and consistency analysis.

---

*This repo contains no production code. All source files exist solely as diff targets.*
