# PayloadGuard Test Harness — Public Brief

A controlled test environment for adversarially validating PayloadGuard's detection capabilities across multiple attack categories and programming languages.

**Author:** Steven Dark | Systems Architect & Security Researcher | Aberdeen, Scotland

---

## Purpose

Security tooling that cannot be tested adversarially cannot be trusted. The test harness provides a structured, repeatable environment for validating that PayloadGuard produces correct verdicts across a comprehensive range of attack scenarios — including scenarios specifically designed to evade detection.

The harness contains no production code. All source files exist solely as diff targets for PayloadGuard to scan.

---

## Structure

41 test cases across 5 tracks and 9 categories:

### Track 1 — Validation

Confirms PayloadGuard behaves as specified on canonical inputs.

| Category | Count | Purpose |
|---|---|---|
| `safe` | 3 | Benign PRs that must produce SAFE verdicts — false positive prevention |
| `destructive` | 2 | Unambiguously destructive PRs that must produce DESTRUCTIVE verdicts |
| `boundary` | 1 | Edge cases at scoring thresholds |
| `semantic` | 2 | PR description vs diff mismatch detection |
| `multilang` | 1 | Cross-language structural analysis |

### Track 2 — Adversarial

Static evasion techniques probing detection boundaries:

| Category | Count | Purpose |
|---|---|---|
| `adversarial` | 14 | Deletion obfuscation, threshold gaming, workflow poisoning bypasses, slow-drip deletion, deceptive descriptions |

### Track 3 — Workflow Security

L2c GitHub Actions poisoning signal coverage:

| Category | Count | Purpose |
|---|---|---|
| `workflow-security` | 10 | 7 active cases covering base64 payloads, credential harvesting, dormant triggers, forged bot identity, OIDC escalation, pull_request_target misuse. 3 cases reserved for pending GitHub 2026 API features. |

### Track 4 — Red Team

Live adversarial findings from structured red-team exercises:

| Category | Count | Purpose |
|---|---|---|
| `red-team` | 5 | Live findings (RTA01-RTA05) from adversarial testing sessions. Confirmed detections and documented known bypasses exist — details are classified under Tier 2. |

### Track 5 — Runtime

L5c eBPF agent event coverage:

| Category | Count | Purpose |
|---|---|---|
| `runtime` | 3 | procmem access, egress connection, and ptrace scenarios. Static verdict is SAFE — layer fires advisory events only. |

---

## Multi-Language Coverage

Test cases span four languages to validate PayloadGuard's AST-aware structural analysis:

| Language | Test Files |
|---|---|
| Python | `auth.py`, `database.py`, `test_auth.py`, `test_database.py` |
| JavaScript | `api.js` |
| TypeScript | `services.ts` |
| Go | `utils.go` |

---

## Regression Runner

Automated regression testing validates verdict consistency across all cases:

- **Stable mode** (34 cases) — strict pass/fail on every run. Any verdict deviation fails the regression.
- **Temporal mode** — observational tracking for cases where branch age affects the verdict (expected drift).
- **Full mode** (38 active cases) — comprehensive audit including aging cases.
- **Runtime mode** — eBPF-specific cases requiring kernel support.

Each branch represents a permanent scenario. The regression runner reopens each as a PR, waits for PayloadGuard to scan it, closes the PR, and records the result. Results are ingested into SQLite for trend analysis.

---

## Red Team Methodology

Structured adversarial testing follows a controlled process:

1. Design an attack scenario targeting a specific detection layer
2. Implement the scenario on a dedicated branch
3. Open a PR and observe PayloadGuard's verdict
4. Document whether detection succeeded or failed
5. If a bypass is found, document it and develop a fix in the analyser
6. After fix deployment, verify the bypass is closed via regression

Known bypasses are documented and tracked. Specific evasion techniques and bypass details are classified under **Tier 2 (Selective)** and are available only to vetted security professionals. The existence and count of bypasses are public; the mechanics are not.

---

## What This Demonstrates

| Capability | Evidence |
|---|---|
| **Adversarial testing methodology** | Structured red-team process with documented findings, bypass tracking, and regression verification |
| **Test engineering** | 41 cases across 9 categories with automated regression, SQLite ingestion, and trend dashboard |
| **Security research discipline** | Controlled disclosure of bypass details — existence documented, mechanics restricted |
| **Multi-language awareness** | Coverage across Python, JavaScript, TypeScript, and Go |

---

## Classification

This brief contains **Tier 1 (Fully Public)** content only. Specific bypass techniques, evasion details, and red team findings are classified under Tier 2. See [`DISCLOSURE_STRATEGY.md`](https://github.com/PayloadGuard-PLG/payload-consequence-analyser/blob/main/DISCLOSURE_STRATEGY.md) in the PayloadGuard repository for the full classification framework.

---

*Built solo, from a phone, using AI-directed development. Three months. No team, no IDE, no desktop.*
