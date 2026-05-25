# PayloadGuard Test Harness — Branch Specification

**Version:** 1.1  
**Repo:** `payloadguard-test-harness`  
**Reports land in:** `payload-consequence-analyser/test-reports/runs/`

---

## How to Read This Document

Each branch is a controlled PR against `main`. For each:

- **What changes** — exactly what files/lines are modified
- **Layers expected to fire** — which of the 5 layers should trigger
- **Expected verdict** — SAFE / REVIEW / CAUTION / DESTRUCTIVE
- **Consistency target** — same branch scanned 3x should return identical verdict
- **Notes** — edge case rationale or known limitations

---

## Track 1 — Validation Branches

*These confirm PayloadGuard behaves as designed. All verdicts should be stable and repeatable.*

---

### T01 — `safe/small-additive`

| Field | Value |
|---|---|
| **Purpose** | Baseline clean pass — nothing fires |
| **Change** | Add 1 new function `health_check()` to `auth.py` (+8 lines) |
| **PR description** | "Add health check endpoint to auth module" |
| **Layers expected to fire** | None |
| **Expected verdict** | ✅ SAFE [LOW] |
| **Consistency target** | 3/3 identical |
| **Notes** | Establishes the zero-noise baseline. If this returns anything other than SAFE, something is wrong. |

---

### T02 — `safe/docs-only`

| Field | Value |
|---|---|
| **Purpose** | Documentation change — no structural impact |
| **Change** | Update `README.md` only (+15 lines, 0 deletions) |
| **PR description** | "Update README with installation instructions" |
| **Layers expected to fire** | None |
| **Expected verdict** | ✅ SAFE [LOW] |
| **Consistency target** | 3/3 identical |
| **Notes** | Confirms non-code changes don't trigger false positives |

---

### T03 — `destructive/mass-deletion`

| Field | Value |
|---|---|
| **Purpose** | Classic destructive merge — all layers fire |
| **Change** | Delete `auth.py`, `database.py`, `test_auth.py`, `test_database.py`, `settings.yml` (5 files, ~250 lines) |
| **PR description** | "Remove legacy authentication and database modules" |
| **Layers expected to fire** | L1 (file count), L2 (critical paths: tests, config), L3 (consequence), L4 (structural nodes gone) |
| **Expected verdict** | ❌ DESTRUCTIVE [CRITICAL] |
| **Consistency target** | 3/3 identical |
| **Notes** | Most signals fire simultaneously. Strong test of score accumulation. |

---

### T04 — `destructive/april-2026-replica`

| Field | Value |
|---|---|
| **Purpose** | Exact replica of the incident that motivated PayloadGuard |
| **Change** | Replace entire contents of `auth.py` and `database.py` with stubs (~200 lines deleted, ~10 added). Branch dated 300+ days old. |
| **PR description** | "Minor syntax fix in user module" |
| **Layers expected to fire** | L1 (deletion ratio ~95%), L3 (consequence), L4 (structural nodes gone), L5a (temporal — drift score ~1500), L5b (semantic — "minor syntax fix" vs CRITICAL) |
| **Expected verdict** | ❌ DESTRUCTIVE [CRITICAL] |
| **Consistency target** | 3/3 identical |
| **Notes** | The canonical case. All 5 layers should fire. Deceptive description makes L5b flag DECEPTIVE_PAYLOAD. |

---

### T05 — `boundary/structural-threshold`

| Field | Value |
|---|---|
| **Purpose** | Test exactly at the 20% structural deletion threshold |
| **Change** | In `auth.py` (10 structural nodes total): delete exactly 2 methods (20%) |
| **PR description** | "Remove deprecated session methods" |
| **Layers expected to fire** | L4 (just at threshold) |
| **Expected verdict** | ⚠️ CAUTION or → REVIEW [depends on other signals] |
| **Consistency target** | 3/3 identical verdict AND identical score |
| **Notes** | Critical boundary test. Run this 5x not 3x. Any variance in score is a consistency bug. |

---

### T06 — `boundary/temporal-warning`

| Field | Value |
|---|---|
| **Purpose** | Test at exactly the temporal WARNING threshold (drift score 250) |
| **Change** | Trivial change (+1 line comment) on a branch created to simulate 50 days old on a repo at 5 commits/day |
| **PR description** | "Add inline comment to utils" |
| **Layers expected to fire** | L5a (drift score = 250, STALE/WARNING) |
| **Expected verdict** | → REVIEW [MEDIUM] |
| **Consistency target** | 3/3 identical |
| **Notes** | Isolates temporal layer. Other layers should be silent. |

---

### T07 — `boundary/temporal-critical`

| Field | Value |
|---|---|
| **Purpose** | Test at exactly the temporal CRITICAL threshold (drift score 1000) |
| **Change** | Trivial change (+1 line comment) simulating 100 days old at 10 commits/day |
| **PR description** | "Add inline comment to utils" |
| **Layers expected to fire** | L5a (drift score = 1000, DANGEROUS/CRITICAL) |
| **Expected verdict** | ⚠️ CAUTION [HIGH] |
| **Consistency target** | 3/3 identical |
| **Notes** | Temporal layer alone at critical. Change is genuinely harmless — tests whether temporal signal alone escalates correctly. |

---

### T08 — `mixed/stale-branch-tiny-change`

| Field | Value |
|---|---|
| **Purpose** | Old branch, harmless change — should flag temporal but not structural |
| **Change** | Fix a typo in a docstring. Branch is 200 days old. |
| **PR description** | "Fix typo in docstring" |
| **Layers expected to fire** | L5a (temporal — STALE) |
| **Expected verdict** | → REVIEW [MEDIUM] |
| **Consistency target** | 3/3 identical |
| **Notes** | Tests that a stale branch with minimal change doesn't over-escalate. Verdict should be proportionate. |

---

### T09 — `semantic/no-description`

| Field | Value |
|---|---|
| **Purpose** | Empty PR description — UNVERIFIED path |
| **Change** | Delete `database.py` (significant change) |
| **PR description** | *(empty)* |
| **Layers expected to fire** | L1, L2, L3, L4, L5b (UNVERIFIED — no description to analyse) |
| **Expected verdict** | ❌ DESTRUCTIVE [CRITICAL] |
| **Consistency target** | 3/3 identical |
| **Notes** | Confirms empty description returns UNVERIFIED not a crash. Destructive verdict should still fire from other layers. |

---

### T10 — `semantic/honest-critical`

| Field | Value |
|---|---|
| **Purpose** | Honest description of a genuinely destructive change |
| **Change** | Delete `auth.py` entirely |
| **PR description** | "BREAKING CHANGE: Remove Auth module — replaced by external OAuth provider" |
| **Layers expected to fire** | L1, L2, L3, L4 — L5b should return TRANSPARENT |
| **Expected verdict** | ❌ DESTRUCTIVE [CRITICAL] |
| **Consistency target** | 3/3 identical |
| **Notes** | Confirms L5b doesn't reduce severity for honest PRs — TRANSPARENT means the description matches, not that the change is safe. |

---

### T11 — `multilang/structural-js-ts-go`

| Field | Value |
|---|---|
| **Purpose** | Stress test structural parser across all non-Python languages |
| **Change** | Delete `fetchUser`, `createUser` from `api.js`; delete `UserService` from `services.ts`; delete `NewServer`, `HandleRequest` from `utils.go` |
| **PR description** | "Remove unused API and server utilities" |
| **Layers expected to fire** | L4 (structural — JS, TS, Go nodes all deleted) |
| **Expected verdict** | ⚠️ CAUTION or ❌ DESTRUCTIVE |
| **Consistency target** | 3/3 identical |
| **Notes** | First real test of multi-language structural parser in a live CI context. Watch for silent failures where nodes aren't detected. |

---

### T12 — `safe/large-rename`

| Field | Value |
|---|---|
| **Purpose** | Detect false positives caused by class renaming — the rename gap |
| **Change** | In `auth.py`: rename `Auth` → `Identity`, `SessionManager` → `SessionStore`, `PasswordValidator` → `CredentialValidator` (no logic changes) |
| **PR description** | "Rename auth classes for consistency with identity domain terminology" |
| **Layers expected to fire** | None (safe rename — no logic deleted) |
| **Expected verdict** | ✅ SAFE [LOW] |
| **Consistency target** | 3/3 identical |
| **Notes** | **If this returns anything other than SAFE, it is a confirmed false positive.** L4 sees three classes disappear and cannot match them to the renamed versions — this is the known rename gap. Fix requires treating `change_type == 'R'` as modify and cross-referencing deleted/added node names across the full diff. |

---

## Track 2 — Adversarial Branches

*These are designed to probe limitations. Results are documented as known boundaries — not bugs — unless PayloadGuard catches them unexpectedly.*

---

### A01 — `adversarial/keyword-evasion`

| Field | Value |
|---|---|
| **Purpose** | Deceptive description that avoids all benign keywords |
| **Change** | Delete `auth.py` entirely (~120 lines) |
| **PR description** | "Architectural consolidation: centralising identity management into the new OAuth gateway layer" |
| **Layers expected to fire** | L1, L2, L3, L4 — L5b should return TRANSPARENT (no keyword match) |
| **Expected verdict** | ❌ DESTRUCTIVE [CRITICAL] |
| **Known limitation** | L5b misses this — keyword matching only, no NLP. Documented as known gap. |
| **Notes** | The description is deceptive but uses no trigger words. Tests whether other layers compensate. |

---

### A02 — `adversarial/rename-smuggling`

| Field | Value |
|---|---|
| **Purpose** | Destructive changes hidden in renamed files (change_type = R) |
| **Change** | Rename `auth.py` → `identity.py` with contents gutted (all classes removed) |
| **PR description** | "Rename auth module to identity for consistency" |
| **Layers expected to fire** | L1 (rename count), L5b (description seems benign) |
| **Expected verdict** | → REVIEW or ⚠️ CAUTION |
| **Known limitation** | L4 does not analyse renamed files — structural gutting is invisible to structural drift detection. |
| **Notes** | Documents the renamed-file blind spot from the whitepaper. |

---

### A03 — `adversarial/slow-deletion`

| Field | Value |
|---|---|
| **Purpose** | Mass deletion spread thinly to stay under per-file thresholds |
| **Change** | Delete 1 function each from `auth.py`, `database.py`, `api.js`, `services.ts`, `utils.go` — no single file crosses 20% structural threshold |
| **PR description** | "Remove deprecated utility functions across modules" |
| **Layers expected to fire** | Possibly none at high severity |
| **Expected verdict** | ✅ SAFE or → REVIEW |
| **Known limitation** | Per-file structural scoring doesn't accumulate cross-file. Distributed deletion evades detection. |
| **Notes** | One of the most realistic attack vectors. Documents cross-file accumulation gap. |

---

### A04 — `adversarial/addition-camouflage`

| Field | Value |
|---|---|
| **Purpose** | Large addition masks large deletion — ratio looks safe |
| **Change** | Add 200 lines of new boilerplate to `api.js`, simultaneously delete `auth.py` (120 lines) |
| **PR description** | "Expand API module with new endpoints" |
| **Layers expected to fire** | L1 (deleted files), L2 (critical path), L3, L4 |
| **Expected verdict** | ⚠️ CAUTION or ❌ DESTRUCTIVE |
| **Notes** | Deletion ratio will be low (~37%) because of the large addition. Tests whether file-level signals compensate for ratio camouflage. |

---

### A05 — `adversarial/nested-gutting`

| Field | Value |
|---|---|
| **Purpose** | Top-level class preserved, all methods inside deleted |
| **Change** | In `auth.py`: keep `class Auth` but delete all methods inside it (`login`, `logout`, `register`, `authenticate`, `deactivate`) |
| **PR description** | "Refactor Auth class interface" |
| **Layers expected to fire** | L4 (methods are tracked as structural nodes) |
| **Expected verdict** | ⚠️ CAUTION or ❌ DESTRUCTIVE |
| **Notes** | Tests whether method-level deletion inside a class is caught. PayloadGuard tracks methods — this should fire. Documents behaviour clearly either way. |

---

### A06 — `adversarial/threshold-gaming`

| Field | Value |
|---|---|
| **Purpose** | Every metric tuned to sit just below every threshold |
| **Change** | Branch 89 days old. Delete 9 files. Deletion ratio 49%. Structural deletion 19%. Drift score 249. |
| **PR description** | "General codebase maintenance" |
| **Layers expected to fire** | None — every metric is sub-threshold |
| **Expected verdict** | ✅ SAFE [LOW] — severity score 0 |
| **Known limitation** | A sophisticated attacker who knows the thresholds can game every metric simultaneously. |
| **Notes** | The most important adversarial case. Documents that threshold-based systems have a known gaming vector. Mitigation path: composite scoring or ML-based thresholds. |

---

### A07 — `adversarial/new-file-replacement`

| Field | Value |
|---|---|
| **Purpose** | Nothing deleted — old files replaced by new files with destructive content |
| **Change** | Delete `auth.py`, add `auth_v2.py` with 5 lines replacing 120. Net: additions > deletions. |
| **PR description** | "Upgrade auth module to v2" |
| **Layers expected to fire** | L1 (deleted file), L2 (critical path), L3 |
| **Expected verdict** | ⚠️ CAUTION or ❌ DESTRUCTIVE |
| **Notes** | Tests whether delete+add pattern (rather than modify) is caught. L4 won't compare old→new across different filenames. |

---

### A08 — `adversarial/empty-diff`

| Field | Value |
|---|---|
| **Purpose** | PR opened with no actual changes — empty diff |
| **Change** | Branch created from HEAD with no commits beyond it |
| **PR description** | "Preparing for upcoming changes" |
| **Layers expected to fire** | None |
| **Expected verdict** | ✅ SAFE [LOW] |
| **Notes** | Tests graceful handling of zero-diff PRs. Should not crash or produce misleading output. |

---

### A09 — `adversarial/config-only-deletion`

| Field | Value |
|---|---|
| **Purpose** | Delete only config and CI files — no source code touched |
| **Change** | Delete `settings.yml`, `.github/workflows/` (if present) |
| **PR description** | "Remove unused configuration files" |
| **Layers expected to fire** | L2 (critical path patterns: config, .yml) |
| **Expected verdict** | → REVIEW or ⚠️ CAUTION |
| **Notes** | Tests whether config-only deletions are treated as critical. No structural nodes affected — pure L2 signal. |

---

### A10 — `adversarial/unicode-payload`

| Field | Value |
|---|---|
| **Purpose** | Malformed or unusual encoding in file content |
| **Change** | Modify `auth.py` to include null bytes, non-UTF8 sequences, or right-to-left override characters in comments |
| **PR description** | "Update auth module comments" |
| **Layers expected to fire** | Potentially none — or a graceful error |
| **Expected verdict** | ✅ SAFE or graceful error — no crash |
| **Notes** | Tests robustness of blob reading and AST parsing against hostile encoding. The `errors='ignore'` in blob reading should handle this — confirms it does. |

---

## Consistency Protocol

Each branch is scanned a minimum of **3 times**. For boundary cases (T05, T06, T07) scan **5 times**.

A branch passes consistency if:
- Verdict status is identical across all runs
- Severity score is identical across all runs
- Layers fired are identical across all runs

Any variance is logged as a **consistency failure** in the run report.

---

## Report Naming Convention

```
{track}-{id}-{branch-slug}-run{n}-{YYYYMMDD}.json
```

Examples:
```
t01-safe-small-additive-run1-20260423.json
a06-threshold-gaming-run1-20260423.json
```

---

## Track 3 — Layer 2c: GitHub Actions Poisoning (Validation)

*These confirm the seven Layer 2c signal types behave as specified. WS07 is the only safe case — any flag there is a false positive bug.*

---

### WS01 — `workflow-security/base64-payload`

| Field | Value |
|---|---|
| **Purpose** | Confirm base64 payload delivery is caught (CRITICAL signal) |
| **Change** | Add `.github/workflows/base64-delivery.yml` containing `echo "..." \| base64 -d \| bash` |
| **PR description** | "Add CI pipeline for dependency management" |
| **Layers expected to fire** | L2c (`base64_payload`, CRITICAL, score +5) |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Notes** | Cleanest CRITICAL signal. Any other layers silent — change is addition-only. Confirm `actions_poisoning.flagged_workflows` has 1 entry with `severity: CRITICAL`. |

---

### WS02 — `workflow-security/credential-harvest`

| Field | Value |
|---|---|
| **Purpose** | Confirm AWS metadata endpoint + env grep is caught (CRITICAL signal) |
| **Change** | Add `.github/workflows/deployment.yml` with `curl http://169.254.169.254/...` and `env \| grep -E 'AWS_\|SECRET'` |
| **PR description** | "Add deployment workflow" |
| **Layers expected to fire** | L2c (`credential_harvest`, CRITICAL, score +5) |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Notes** | Two separate patterns in `_ACTIONS_CREDENTIAL_HARVEST` should both match. Confirm signal list has two entries. |

---

### WS03 — `workflow-security/dormant-trigger`

| Field | Value |
|---|---|
| **Purpose** | Confirm dormant trigger + shell exec composite signal fires (HIGH) |
| **Change** | Add `.github/workflows/maintenance.yml` with `on: workflow_dispatch` and `curl -s ... \| bash` |
| **PR description** | "Add maintenance workflow" |
| **Layers expected to fire** | L2c (`dormant_trigger_with_payload`, HIGH, score +3) |
| **Expected verdict** | ⚠️ CAUTION |
| **Notes** | Both conditions must be true: dormant trigger AND shell exec. Trigger alone is not flagged (see AW02 for prt-only baseline). |

---

### WS04 — `workflow-security/forged-bot-author`

| Field | Value |
|---|---|
| **Purpose** | Confirm forged bot identity in git config is caught (HIGH signal) |
| **Change** | Add `.github/workflows/auto-release.yml` with `git config user.name "github-actions[bot]"` |
| **PR description** | "Automate release tagging" |
| **Layers expected to fire** | L2c (`forged_bot_author`, HIGH, score +3) |
| **Expected verdict** | ⚠️ CAUTION |
| **Notes** | Tests `_ACTIONS_FORGED_AUTHOR` regex with the canonical impersonation string `github-actions[bot]`. |

---

### WS05 — `workflow-security/oidc-elevation`

| Field | Value |
|---|---|
| **Purpose** | Confirm `id-token: write` without a legitimate consumer is flagged (HIGH) |
| **Change** | Add `.github/workflows/deploy-cloud.yml` with `permissions: id-token: write` and no `aws-actions/`, `google-github-actions/`, or `azure/login` |
| **PR description** | "Add cloud deployment workflow" |
| **Layers expected to fire** | L2c (`oidc_elevation_no_consumer`, HIGH, score +3) |
| **Expected verdict** | ⚠️ CAUTION |
| **Notes** | Exact-match allowlist must reject prefix variations. See AW03 for typosquat test, AW04 for the safe counterpart. |

---

### WS06 — `workflow-security/prt-write-permissions`

| Field | Value |
|---|---|
| **Purpose** | Confirm `pull_request_target` + write permissions escalates to CRITICAL |
| **Change** | Add `.github/workflows/pr-automation.yml` with `on: pull_request_target` and `permissions: contents: write, pull-requests: write` |
| **PR description** | "Add PR automation workflow" |
| **Layers expected to fire** | L2c (`pull_request_target_with_write_permissions`, CRITICAL, score +5) |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Notes** | Two-tier prt scoring: prt alone = HIGH (+3); prt + any write permission = CRITICAL (+5). This tests the CRITICAL path. |

---

### WS07 — `workflow-security/safe-clean-workflow`

| Field | Value |
|---|---|
| **Purpose** | Confirm clean legitimate workflow raises no L2c flags |
| **Change** | Add `.github/workflows/ci-standard.yml` — standard `push`/`pull_request` triggers, `actions/checkout`, `pytest`, no shell injection, `permissions: contents: read` |
| **PR description** | "Add standard CI workflow" |
| **Layers expected to fire** | None |
| **Expected verdict** | ✅ SAFE |
| **Consistency target** | 3/3 identical |
| **Notes** | **If this returns anything other than SAFE, it is a confirmed false positive.** Zero-noise baseline for Layer 2c. |

---

## Track 4 — Layer 2c: GitHub Actions Poisoning (Adversarial)

*These probe the hardened detection paths. Failures document known bypass vectors or regression bugs.*

---

### AW01 — `adversarial/workflow-yaml-folded-block`

| Field | Value |
|---|---|
| **Purpose** | Base64 payload split across YAML folded block lines to break naive line-by-line regex |
| **Change** | Add `.github/workflows/build-pipeline.yml` using YAML `>` folded block to spread `base64 -d \| bash` across multiple lines |
| **PR description** | "Add build pipeline" |
| **Layers expected to fire** | L2c (`base64_payload`, CRITICAL) after `_normalize_yaml_content()` |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Known bypass if missed** | YAML content normalisation not applied — raw line-by-line match misses folded blocks |
| **Notes** | This is the primary hardening test. `_normalize_yaml_content()` joins all lines with spaces before applying base64 patterns. If this returns SAFE, normalisation is broken. |

---

### AW02 — `adversarial/workflow-prt-only`

| Field | Value |
|---|---|
| **Purpose** | `pull_request_target` without write permissions — should score HIGH not CRITICAL |
| **Change** | Add `.github/workflows/pr-labeler.yml` with `on: pull_request_target` and `permissions: pull-requests: read, contents: read` |
| **PR description** | "Add PR labeler" |
| **Layers expected to fire** | L2c (`dangerous_trigger_pull_request_target`, HIGH, score +3) |
| **Expected verdict** | ⚠️ CAUTION |
| **Notes** | Tests the two-tier prt distinction. If this returns DESTRUCTIVE, the escalation logic is wrong. |

---

### AW03 — `adversarial/workflow-typosquatted-oidc`

| Field | Value |
|---|---|
| **Purpose** | Typosquatted OIDC consumer action to bypass prefix matching |
| **Change** | Add `.github/workflows/aws-deploy.yml` with `id-token: write` and `uses: aws-actions-unofficial/configure-aws-credentials@v2` |
| **PR description** | "Deploy to AWS" |
| **Layers expected to fire** | L2c (`oidc_elevation_no_consumer`, CRITICAL — typosquat fails exact-match check) |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Known bypass if missed** | Prefix matching (`aws-actions/`) instead of exact-match — typosquat `aws-actions-unofficial/` would pass a prefix check |
| **Notes** | Tests that `_SAFE_OIDC_CONSUMERS_DEFAULT` uses exact action-name prefix matching, not loose substring. |

---

### AW04 — `adversarial/workflow-legitimate-oidc`

| Field | Value |
|---|---|
| **Purpose** | Legitimate OIDC consumer must not be flagged — false positive regression test |
| **Change** | Add `.github/workflows/aws-deploy-legit.yml` with `id-token: write` and `uses: aws-actions/configure-aws-credentials@v4` |
| **PR description** | "Deploy to AWS using OIDC" |
| **Layers expected to fire** | None |
| **Expected verdict** | ✅ SAFE |
| **Known false positive if flagged** | Exact-match check incorrectly rejecting canonical consumer |
| **Notes** | **If this returns CAUTION or DESTRUCTIVE, the OIDC allowlist is broken.** Pair with AW03 — one must pass, one must fail. |

---

### AW05 — `adversarial/workflow-modified-poison`

| Field | Value |
|---|---|
| **Purpose** | Poison injected into an existing workflow via modification (change_type = M, not A) |
| **Change** | Modify existing `.github/workflows/payloadguard.yml` to append `env \| grep -E 'GITHUB_TOKEN\|SECRET'` and `printenv \| awk '/KEY\|TOKEN/{print}'` steps |
| **PR description** | "Add diagnostic step to CI" |
| **Layers expected to fire** | L2c (`credential_harvest`, CRITICAL, score +5) |
| **Expected verdict** | ❌ DESTRUCTIVE |
| **Known bypass if missed** | Scanner only processes `change_type == 'A'` — existing workflows modified post-merge are invisible |
| **Notes** | This is the second hardening test. `_scan_github_actions_poisoning()` processes both A and M types. If this returns SAFE, the M-type guard is broken. |

---

## Summary Table

| ID | Branch | Track | Expected Verdict | Layers |
|---|---|---|---|---|
| T01 | `safe/small-additive` | Validation | SAFE | None |
| T02 | `safe/docs-only` | Validation | SAFE | None |
| T03 | `destructive/mass-deletion` | Validation | DESTRUCTIVE | L1 L2 L3 L4 |
| T04 | `destructive/april-2026-replica` | Validation | DESTRUCTIVE | L1 L2 L3 L4 L5a L5b |
| T05 | `boundary/structural-threshold` | Validation | CAUTION/REVIEW | L4 |
| T06 | `boundary/temporal-warning` | Validation | REVIEW | L5a |
| T07 | `boundary/temporal-critical` | Validation | CAUTION | L5a |
| T08 | `mixed/stale-branch-tiny-change` | Validation | REVIEW | L5a |
| T09 | `semantic/no-description` | Validation | DESTRUCTIVE | L1 L2 L3 L4 L5b(UNVERIFIED) |
| T10 | `semantic/honest-critical` | Validation | DESTRUCTIVE | L1 L2 L3 L4 |
| T11 | `multilang/structural-js-ts-go` | Validation | CAUTION/DESTRUCTIVE | L4 |
| T12 | `safe/large-rename` | Validation | SAFE | None |
| A01 | `adversarial/keyword-evasion` | Adversarial | DESTRUCTIVE | L1 L2 L3 L4 |
| A02 | `adversarial/rename-smuggling` | Adversarial | REVIEW/CAUTION | L1 |
| A03 | `adversarial/slow-deletion` | Adversarial | SAFE/REVIEW | None/L4 |
| A04 | `adversarial/addition-camouflage` | Adversarial | CAUTION/DESTRUCTIVE | L1 L2 L3 |
| A05 | `adversarial/nested-gutting` | Adversarial | CAUTION/DESTRUCTIVE | L4 |
| A06 | `adversarial/threshold-gaming` | Adversarial | SAFE | None |
| A07 | `adversarial/new-file-replacement` | Adversarial | CAUTION/DESTRUCTIVE | L1 L2 L3 |
| A08 | `adversarial/empty-diff` | Adversarial | SAFE | None |
| A09 | `adversarial/config-only-deletion` | Adversarial | REVIEW/CAUTION | L2 |
| A10 | `adversarial/unicode-payload` | Adversarial | SAFE/graceful error | None |
| WS01 | `workflow-security/base64-payload` | L2c Validation | DESTRUCTIVE | L2c |
| WS02 | `workflow-security/credential-harvest` | L2c Validation | DESTRUCTIVE | L2c |
| WS03 | `workflow-security/dormant-trigger` | L2c Validation | CAUTION | L2c |
| WS04 | `workflow-security/forged-bot-author` | L2c Validation | CAUTION | L2c |
| WS05 | `workflow-security/oidc-elevation` | L2c Validation | CAUTION | L2c |
| WS06 | `workflow-security/prt-write-permissions` | L2c Validation | DESTRUCTIVE | L2c |
| WS07 | `workflow-security/safe-clean-workflow` | L2c Validation | SAFE | None |
| AW01 | `adversarial/workflow-yaml-folded-block` | L2c Adversarial | DESTRUCTIVE | L2c |
| AW02 | `adversarial/workflow-prt-only` | L2c Adversarial | CAUTION | L2c |
| AW03 | `adversarial/workflow-typosquatted-oidc` | L2c Adversarial | DESTRUCTIVE | L2c |
| AW04 | `adversarial/workflow-legitimate-oidc` | L2c Adversarial | SAFE | None |
| AW05 | `adversarial/workflow-modified-poison` | L2c Adversarial | DESTRUCTIVE | L2c |

---

*PayloadGuard Test Harness v1.2 — 34 branches, 4 tracks*  
*Built to find the limits before production does.*
