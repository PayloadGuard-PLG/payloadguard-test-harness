# PayloadGuard Test Harness — Public Brief

**Adversarial validation framework for CI/CD security tools.**

---

## Problem

Security detection tools need adversarial validation — not just unit tests. A tool that catches obvious attacks but misses subtle evasion techniques provides false confidence. The test harness exists to systematically probe PayloadGuard's detection logic under realistic adversarial conditions, document bypass vectors, and drive detection improvements.

---

## Methodology

Each test case is a controlled PR against a known baseline. The harness:

1. Opens the PR (triggering PayloadGuard to scan it)
2. Waits for the scan verdict
3. Compares the actual verdict against the expected verdict
4. Closes the PR (no merge — test data only)
5. Records the result for regression tracking

This is not fuzzing. Each case is hand-crafted to probe a specific detection boundary, evasion technique, or signal interaction.

---

## Coverage

41 test cases across 9 categories and 38 active branches:

| Category | Count | Purpose |
|----------|-------|---------|
| **safe** | 3 | Zero-noise baseline — any DESTRUCTIVE result is a confirmed false positive |
| **destructive** | 2 | Canonical payloads — any non-DESTRUCTIVE result is a confirmed miss |
| **boundary** | 1 | Metrics tuned to threshold boundaries — confirms score transitions |
| **semantic** | 2 | PR description vs diff content alignment |
| **multilang** | 1 | AST parser stress test across JavaScript, TypeScript, Go |
| **adversarial** | 14 | Static evasion techniques: deletion obfuscation, threshold gaming, YAML manipulation |
| **red-team** | 5 | Live adversarial session findings — confirmed detections and addressed bypasses |
| **runtime** | 3 | eBPF agent event coverage (advisory, no score impact) |
| **workflow-security** | 10 | GitHub Actions poisoning signal validation (7 active + 3 reserved) |

---

## Adversarial Tracks

### Track 2 — Static Evasion

14 cases testing techniques an attacker might use to evade detection:

- Keyword evasion in PR descriptions
- Rename-based smuggling (auth.py → identity.py, contents gutted)
- Slow deletion (1 function per file across many files)
- Addition camouflage (large addition masks critical deletion)
- Nested gutting (class shell preserved, all methods removed)
- Threshold gaming (every metric tuned just below detection boundaries)
- New-file replacement (delete original, add stub with same interface)
- YAML folded-block manipulation to break line-by-line regex
- Typosquatted action consumers to bypass allowlist matching

### Track 4 — Red Team (RTA01–RTA05)

5 findings from a live adversarial session conducted against the detection engine. Each finding either:
- Confirmed a detection (true positive validation), or
- Documented a bypass that was subsequently fixed and regression-tested

All bypass vectors discovered during red-teaming have been addressed. The test cases remain as permanent regression guards.

---

## Regression Automation

```
Modes:
  stable   — 34 cases with strict pass/fail (standard regression)
  temporal — Observational-only cases that drift with branch age
  full     — All 38 active cases
  runtime  — eBPF agent event coverage only (RT01–RT03)
```

Results are ingested into SQLite for historical tracking. A Dash-based dashboard provides regression matrix visualisation, history graphs, and threshold simulation.

Automated triggers:
- `repository_dispatch` from the analyser on push to main (tests latest changes)
- Daily schedule at 02:00 UTC (drift observation)

---

## Temporal Groups

Some test cases are designed to observe how verdicts change over time:

- **stable** — Same expected verdict on every run. Failures are regressions.
- **aging** — Verdicts drift as branches age (temporal drift score increases). These document the temporal analysis layer's behavior, not detection failures.

---

## Technology Stack

- **Runner:** Python (`tools/run_regression.py`)
- **Storage:** SQLite (result ingestion and history)
- **Visualisation:** Dash dashboard
- **CI:** GitHub Actions (scheduled + dispatch triggers)
- **Ground truth:** `tools/test_cases.json` — canonical test case registry

---

## Development Context

- **Timeline:** 3 months (March–May 2026)
- **Developer:** Solo — Steven Dark (Aberdeen, Scotland)
- **Method:** AI-directed development. Human designs attack scenarios and expected outcomes; AI implements branch content and tooling.
- **Adversarial sessions:** 5 red-team findings documented, all addressed

---

## What This Demonstrates

1. **Adversarial security testing** — systematic probing of detection boundaries, not just happy-path validation
2. **Red-team methodology** — live adversarial sessions against own tooling with findings documented and addressed
3. **Regression engineering** — automated, repeatable validation across 41 cases with temporal tracking
4. **Test design discipline** — each case probes a specific boundary with documented rationale and expected layers
5. **Responsible disclosure** — bypass vectors are documented internally and fixed before any external discussion

---

## Note on Sensitivity

The specific evasion techniques and bypass details documented in this harness are classified as Tier 2 (selective sharing) under the PayloadGuard disclosure strategy. The methodology and coverage statistics are Tier 1 (public). See `payload-consequence-analyser/DISCLOSURE_STRATEGY.md` for the full classification.

---

## Contact

For enquiries: see the [portfolio page](https://payloadguard-plg.github.io/payload-consequence-analyser/) or contact Steven Dark directly via [GitHub](https://github.com/DarkVader-PLG).
