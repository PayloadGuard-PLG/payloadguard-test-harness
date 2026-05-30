# PayloadGuard Test Harness — Public Brief

**Author:** Steven Dark | Aberdeen, Scotland

---

## Purpose

Controlled test environment for validating PayloadGuard's detection capabilities across a comprehensive matrix of attack vectors, edge cases, and evasion techniques. The harness provides systematic, reproducible verification that the analyser behaves as specified — detecting what it should detect, and not flagging what it should pass.

---

## Structure

41 test cases across 5 tracks:

### Track 1 — Validation
**Directories:** `safe/`, `destructive/`, `boundary/`, `semantic/`, `multilang/`

Confirms PayloadGuard behaves as specified on canonical inputs. Includes:
- Known-safe PRs that must produce SAFE verdicts
- Known-destructive PRs that must produce DESTRUCTIVE verdicts
- Boundary cases at scoring thresholds (REVIEW ↔ CAUTION ↔ DESTRUCTIVE transitions)
- Semantic mismatch cases (PR description contradicts diff content)
- Multi-language targets (Python, JavaScript, TypeScript, Go)

### Track 2 — Adversarial
**Directory:** `adversarial/`

Static evasion techniques designed to bypass detection without triggering alerts:
- Deletion obfuscation — distributing mass deletion across many small commits
- Threshold gaming — staying just below scoring thresholds
- Workflow poisoning bypasses — structuring malicious workflow changes to avoid L2c signals

### Track 3 — Workflow Security
**Directory:** `workflow-security/`

L2c Actions Poisoning signal coverage:
- 7 active test cases covering base64 payloads, credential harvesting, OIDC elevation, dormant triggers, forged bot authors, pull_request_target abuse, and typosquatted action consumers
- 3 cases reserved for pending GitHub 2026 API features

### Track 4 — Red Team
**Directory:** `rta/`

Live findings from the 2026-05-25 red team session:
- Confirmed detections documented with expected verdicts
- Known bypasses documented alongside the detection gaps they exploit
- Each finding has a unique identifier (RTA01–RTA05) cross-referenced with `AUDIT_LOG.md`

### Track 5 — Runtime
**Directory:** `runtime/`

L5c eBPF agent event coverage:
- `procmem` — process memory access monitoring
- `egress` — outbound network connection detection
- `ptrace` — debugger attachment and process tracing

---

## Multi-Language Targets

Test cases include payloads in:
- **Python** — primary language, full AST analysis via tree-sitter
- **JavaScript** — variable declarator tracking, function/class deletion
- **TypeScript** — type-annotated function and interface deletion
- **Go** — function and type deletion in Go source files

Each language exercises the structural parser (`structural_parser.py`) to verify cross-language AST extraction.

---

## Regression System

Automated daily regression at 02:00 UTC:
1. Each test case has an **expected verdict** (SAFE, REVIEW, CAUTION, or DESTRUCTIVE)
2. PayloadGuard runs against each test case
3. Actual verdict is compared against expected verdict
4. Pass: actual matches expected. Fail: mismatch detected.
5. Results are aggregated and reported

The regression system catches two categories of breakage:
- **False negatives** — a destructive payload that no longer triggers DESTRUCTIVE
- **False positives** — a safe payload that now triggers CAUTION or DESTRUCTIVE

---

## What This Project Demonstrates

- **Systematic adversarial testing methodology** — test cases designed to challenge detection logic, not just confirm it works on easy inputs
- **Red team discipline** — confirmed detections documented alongside known bypasses, not just the successes
- **Regression engineering for security tools** — automated daily verification that detection capabilities are preserved across code changes
- **Multi-language test matrix design** — structured coverage across four languages with language-specific edge cases

---

## Note on Disclosure

Specific bypass techniques and evasion details are **Tier 2** content per the controlled disclosure strategy (`DISCLOSURE_STRATEGY.md` in the main PayloadGuard repository). They are not included in this brief.

Tier 2 content is available under controlled disclosure to:
- Prospective employers (under NDA or mutual confidentiality)
- Security companies (Snyk, Socket.dev, StepSecurity, Chainguard, GitGuardian)
- GitHub Security team
