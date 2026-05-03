# PayloadGuard Test Harness

A controlled test repository for validating and adversarially testing [PayloadGuard](https://github.com/PayloadGuard-PLG/payload-consequence-analyser).

## Purpose

This repo exists to:
- Generate repeatable, controlled PRs that PayloadGuard scans
- Validate consistent verdicts across identical inputs
- Stress test edge cases and known limitations
- Feed scan reports into `payload-consequence-analyser/test-reports/`

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
├── TEST_SPEC.md         # 22 branch specifications
└── requirements.txt
```

## Test Branches

Branches are organised into two tracks:

**Track 1 — Validation** (`safe/`, `destructive/`, `boundary/`, `mixed/`, `semantic/`)
Confirms PayloadGuard behaves as designed.

**Track 2 — Adversarial** (`adversarial/`)
Deliberately crafted to probe limitations. Results are documented as known boundaries, not bugs.

## Reports

Each PayloadGuard scan produces a JSON report saved to:
`payload-consequence-analyser/test-reports/runs/`

See that repo for aggregated results and consistency analysis.

---

*This repo contains no production code. All source files exist solely as diff targets.*
