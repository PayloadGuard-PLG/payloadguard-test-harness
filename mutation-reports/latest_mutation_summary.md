# PayloadGuard Adversarial Harness — Mutation Testing Report

- **Timestamp (UTC):** `2026-10-23T18:35:19.514746+00:00`
- **Analyser Version:** `1.4.0`
- **Total Mutations Evaluated:** `12` (`7` adversarial, `5` benign refactors)
- **Pass Rate (Enforce Mode):** `12/12`
- **False Positives Discovered:** `0`
- **False Negatives / Evasions Discovered:** `0`

## Mutation Results Matrix

| ID | Kind | Branch | Legacy L3 (`shadow`) | Consequence (`enforce`) | Detectors Fired | Status |
|---|---|---|---|---|---|---|
| `MUT-ADV-01` | `adversarial` | `mut/adv-guard-constant-false` | `SAFE` | `DESTRUCTIVE` | `D06_GUARD_REGRESSION` | PASS |
| `MUT-ADV-02` | `adversarial` | `mut/adv-try-except-hollow` | `SAFE` | `DESTRUCTIVE` | `D06_GUARD_REGRESSION` | PASS |
| `MUT-ADV-03` | `adversarial` | `mut/adv-polyglot-distributed-delete` | `SAFE` | `DESTRUCTIVE` | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | PASS |
| `MUT-ADV-04` | `adversarial` | `mut/adv-comment-padded-hollow` | `REVIEW` | `DESTRUCTIVE` | `D02_BODY_WEAKENING` | PASS |
| `MUT-ADV-05` | `adversarial` | `mut/adv-js-guard-removal` | `SAFE` | `DESTRUCTIVE` | `D06_GUARD_REGRESSION` | PASS |
| `MUT-ADV-06` | `adversarial` | `mut/adv-go-state-guard-removal` | `SAFE` | `DESTRUCTIVE` | `D06_GUARD_REGRESSION` | PASS |
| `MUT-ADV-07` | `adversarial` | `mut/adv-signature-arity-break` | `SAFE` | `DESTRUCTIVE` | `D04_PUBLIC_API_BREAK` | PASS |
| `MUT-BEN-01` | `benign` | `mut/ben-extract-guard-helper` | `SAFE` | `SAFE` | *(none)* | PASS |
| `MUT-BEN-02` | `benign` | `mut/ben-cross-file-class-move` | `SAFE` | `SAFE` | *(none)* | PASS |
| `MUT-BEN-03` | `benign` | `mut/ben-combine-guards` | `SAFE` | `SAFE` | *(none)* | PASS |
| `MUT-BEN-04` | `benign` | `mut/ben-ts-method-rename` | `SAFE` | `SAFE` | *(none)* | PASS |
| `MUT-BEN-05` | `benign` | `mut/ben-additive-tests` | `SAFE` | `SAFE` | *(none)* | PASS |
