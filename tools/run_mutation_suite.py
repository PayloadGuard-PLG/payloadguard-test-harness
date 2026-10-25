#!/usr/bin/env python3
"""
PayloadGuard Adversarial Harness Mutation Testing Runner
========================================================
Generates mutated adversarial and benign-refactoring git branches in an isolated
temporary clone of the test harness, runs PayloadGuard in both `shadow` (Legacy L3)
and `enforce` (SCG Consequence Engine v1) modes, records structured telemetry to
`mutation-reports/mutation_runs.jsonl`, and writes a human-readable analysis report
to `mutation-reports/latest_mutation_summary.md`.
"""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List


HARNESS_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ANALYSER = HARNESS_ROOT.parent.parent / "PLG" / "payload-consequence-analyser"
REPORTS_DIR = HARNESS_ROOT / "mutation-reports"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def _read_norm(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _write_norm(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _build_mutations() -> List[Dict[str, Any]]:
    """Return catalog of adversarial and benign-refactoring mutations against the harness."""
    mutations: List[Dict[str, Any]] = []

    # 1. Guard inversion (Adversarial edge case: condition replaced with `if False:`)
    def mut_adv_01(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        text = text.replace(
            'if not self.validator.verify(password, user["hashed"], user["salt"]):',
            "if False:",
        )
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-ADV-01",
        "branch": "mut/adv-guard-constant-false",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Replace password verification guard predicate with `if False:` in Auth.login while keeping return statements",
        "apply": mut_adv_01,
    })

    # 2. Try/except pass hollowing (Adversarial edge case: hollowing disguised inside try/except block)
    def mut_adv_02(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        target = (
            "    def login(self, username: str, password: str) -> Optional[str]:\n"
            "        user = self._users.get(username)\n"
            "        if not user or not user[\"active\"]:\n"
            "            return None\n"
            "        if not self.validator.verify(password, user[\"hashed\"], user[\"salt\"]):\n"
            "            return None\n"
            "        return self.sessions.create(username)"
        )
        replacement = (
            "    def login(self, username: str, password: str) -> Optional[str]:\n"
            "        try:\n"
            "            pass\n"
            "        except Exception:\n"
            "            return None\n"
            "        return self.sessions.create(username)"
        )
        _write_norm(p, text.replace(target, replacement))

    mutations.append({
        "id": "MUT-ADV-02",
        "branch": "mut/adv-try-except-hollow",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Strip all auth guards in Auth.login inside a try/except pass block",
        "apply": mut_adv_02,
    })

    # 3. Cross-language distributed deletion (Python + JS + Go, 1 symbol each)
    def mut_adv_03(repo: Path) -> None:
        db = _read_norm(repo / "database.py")
        db = db.replace(
            "    def table(self, name: str) -> QueryBuilder:\n        return QueryBuilder(name)\n\n",
            "",
        )
        _write_norm(repo / "database.py", db)

        api = _read_norm(repo / "api.js")
        api = api.replace(
            "async function deleteUser(userId, token) {\n"
            "  const response = await fetch(`${BASE_URL}/users/${userId}`, {\n"
            "    method: \"DELETE\",\n"
            "    headers: {\n"
            "      Authorization: `Bearer ${token}`,\n"
            "    },\n"
            "  });\n"
            "  return response.ok;\n"
            "}\n",
            "",
        )
        _write_norm(repo / "api.js", api)

        go = _read_norm(repo / "utils.go")
        go = go.replace(
            "// Stop gracefully shuts down the server.\n"
            "func (s *Server) Stop() {\n"
            "\ts.started = false\n"
            "\tlog.Println(\"Server stopped\")\n"
            "}\n\n",
            "",
        )
        _write_norm(repo / "utils.go", go)

    mutations.append({
        "id": "MUT-ADV-03",
        "branch": "mut/adv-polyglot-distributed-delete",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Delete 1 symbol each across Python (database.py), JS (api.js), and Go (utils.go)",
        "apply": mut_adv_03,
    })

    # 4. Comment-padded hollowing of security function
    def mut_adv_04(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        padding = "\n".join(f"        # Security audit compliance note line {i}" for i in range(1, 35))
        target = (
            "    def validate(self, token: str) -> Optional[str]:\n"
            "        session = self._sessions.get(token)\n"
            "        if not session:\n"
            "            return None\n"
            "        if datetime.utcnow() > session[\"expires_at\"]:\n"
            "            self.revoke(token)\n"
            "            return None\n"
            "        return session[\"user_id\"]"
        )
        replacement = (
            "    def validate(self, token: str) -> Optional[str]:\n"
            f"{padding}\n"
            "        return \"admin\""
        )
        _write_norm(p, text.replace(target, replacement))

    mutations.append({
        "id": "MUT-ADV-04",
        "branch": "mut/adv-comment-padded-hollow",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Gut SessionManager.validate to return constant '\"admin\"' while adding 34 comment lines to inflate addition ratio",
        "apply": mut_adv_04,
    })

    # 5. JS guard strip in api.js
    def mut_adv_05(repo: Path) -> None:
        p = repo / "api.js"
        text = _read_norm(p)
        text = text.replace(
            "  if (!response.ok) {\n    throw new Error(`fetchUser failed: ${response.status}`);\n  }\n",
            "",
        )
        text = text.replace(
            "  if (!response.ok) {\n    throw new Error(`createUser failed: ${response.status}`);\n  }\n",
            "",
        )
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-ADV-05",
        "branch": "mut/adv-js-guard-removal",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Strip `if (!response.ok)` HTTP status guards in api.js fetchUser and createUser",
        "apply": mut_adv_05,
    })

    # 6. Go state-guard removal in utils.go
    def mut_adv_06(repo: Path) -> None:
        p = repo / "utils.go"
        text = _read_norm(p)
        text = text.replace(
            "\tif s.started {\n\t\treturn fmt.Errorf(\"server already started\")\n\t}\n",
            "",
        )
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-ADV-06",
        "branch": "mut/adv-go-state-guard-removal",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Strip `if s.started` duplicate-start guard in Go Server.Start",
        "apply": mut_adv_06,
    })

    # 7. Exported API signature arity break with aliased caller
    def mut_adv_07(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        text = text.replace(
            "    def verify(self, password: str, hashed: str, salt: str) -> bool:",
            "    def verify(self, password: str, hashed: str, salt: str, iterations: int, pepper: str) -> bool:",
        )
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-ADV-07",
        "branch": "mut/adv-signature-arity-break",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Break exported `PasswordValidator.verify` required parameter arity (3 -> 5 required args) while `Auth.login` calls 3-arg form",
        "apply": mut_adv_07,
    })

    # 8. Benign Refactor 1: Extract helper method in same file (potential FP edge case for D06)
    def mut_ben_01(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        old_block = (
            "    def login(self, username: str, password: str) -> Optional[str]:\n"
            "        user = self._users.get(username)\n"
            "        if not user or not user[\"active\"]:\n"
            "            return None\n"
            "        if not self.validator.verify(password, user[\"hashed\"], user[\"salt\"]):\n"
            "            return None\n"
            "        return self.sessions.create(username)"
        )
        new_block = (
            "    def _is_active_user(self, user: Optional[dict]) -> bool:\n"
            "        if not user or not user[\"active\"]:\n"
            "            return False\n"
            "        return True\n\n"
            "    def login(self, username: str, password: str) -> Optional[str]:\n"
            "        user = self._users.get(username)\n"
            "        if not self._is_active_user(user):\n"
            "            return None\n"
            "        if not self.validator.verify(password, user[\"hashed\"], user[\"salt\"]):\n"
            "            return None\n"
            "        return self.sessions.create(username)"
        )
        _write_norm(p, text.replace(old_block, new_block))

    mutations.append({
        "id": "MUT-BEN-01",
        "branch": "mut/ben-extract-guard-helper",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Extract active-user guard into `Auth._is_active_user` helper while retaining `if not self._is_active_user(user):` guard in `Auth.login`",
        "apply": mut_ben_01,
    })

    # 9. Benign Refactor 2: Cross-file move of QueryBuilder from database.py to query_builder.py
    def mut_ben_02(repo: Path) -> None:
        p = repo / "database.py"
        text = _read_norm(p)
        qb_block = (
            "class QueryBuilder:\n"
            "    \"\"\"Builds parameterised SQL queries.\"\"\"\n\n"
            "    def __init__(self, table: str):\n"
            "        self.table = table\n"
            "        self._conditions: list[str] = []\n"
            "        self._params: list[Any] = []\n\n"
            "    def where(self, condition: str, *params) -> \"QueryBuilder\":\n"
            "        self._conditions.append(condition)\n"
            "        self._params.extend(params)\n"
            "        return self\n\n"
            "    def build_select(self, columns: str = \"*\") -> tuple[str, list]:\n"
            "        query = f\"SELECT {columns} FROM {self.table}\"\n"
            "        if self._conditions:\n"
            "            query += \" WHERE \" + \" AND \".join(self._conditions)\n"
            "        return query, self._params\n\n"
            "    def build_delete(self) -> tuple[str, list]:\n"
            "        query = f\"DELETE FROM {self.table}\"\n"
            "        if self._conditions:\n"
            "            query += \" WHERE \" + \" AND \".join(self._conditions)\n"
            "        return query, self._params\n"
        )
        text = text.replace(qb_block, "from query_builder import QueryBuilder\n")
        _write_norm(p, text)
        _write_norm(repo / "query_builder.py", "from typing import Any\n\n\n" + qb_block)

    mutations.append({
        "id": "MUT-BEN-02",
        "branch": "mut/ben-cross-file-class-move",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Move `QueryBuilder` class from database.py to query_builder.py and import it back",
        "apply": mut_ben_02,
    })

    # 10. Benign Refactor 3: Combine two sequential guards into single compound guard (Edge case for D06 guard count)
    def mut_ben_03(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        old_block = (
            "        if not user or not user[\"active\"]:\n"
            "            return None\n"
            "        if not self.validator.verify(password, user[\"hashed\"], user[\"salt\"]):\n"
            "            return None"
        )
        new_block = (
            "        if not user or not user[\"active\"] or not self.validator.verify(password, user[\"hashed\"], user[\"salt\"]):\n"
            "            return None"
        )
        _write_norm(p, text.replace(old_block, new_block))

    mutations.append({
        "id": "MUT-BEN-03",
        "branch": "mut/ben-combine-guards",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Combine two sequential `if` guards in Auth.login into a single compound boolean `if` guard",
        "apply": mut_ben_03,
    })

    # 11. Benign Refactor 4: Rename methods across TypeScript service with identical bodies
    def mut_ben_04(repo: Path) -> None:
        p = repo / "services.ts"
        text = _read_norm(p)
        text = text.replace("async getUser(", "async findUserById(").replace("async createUser(", "async registerUser(")
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-BEN-04",
        "branch": "mut/ben-ts-method-rename",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Rename TypeScript UserService methods `getUser` -> `findUserById` and `createUser` -> `registerUser` with identical bodies",
        "apply": mut_ben_04,
    })

    # 12. Benign Refactor 5: Add new test cases
    def mut_ben_05(repo: Path) -> None:
        p = repo / "test_database.py"
        text = _read_norm(p)
        text += (
            "\ndef test_connection_retry_defaults():\n"
            "    db = Database('localhost', 5432)\n"
            "    assert db.host == 'localhost'\n"
        )
        _write_norm(p, text)

    mutations.append({
        "id": "MUT-BEN-05",
        "branch": "mut/ben-additive-tests",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Pure additive test case in test_database.py",
        "apply": mut_ben_05,
    })

    # 13. Adversarial 8: Boolean short-circuit guard bypass (`and False`) in Auth.login
    def mut_adv_08(repo: Path) -> None:
        p = repo / "auth.py"
        text = _read_norm(p)
        old = 'if not self.validator.verify(password, user["hashed"], user["salt"]):'
        new = 'if not self.validator.verify(password, user["hashed"], user["salt"]) and False:'
        _write_norm(p, text.replace(old, new))

    mutations.append({
        "id": "MUT-ADV-08",
        "branch": "mut/adv-guard-short-circuit",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Neutralize password verification in Auth.login via boolean short-circuit (`and False`)",
        "apply": mut_adv_08,
    })

    # 14. Adversarial 9: Workflow expression injection in `.github/workflows/ci.yml`
    def mut_adv_09(repo: Path) -> None:
        wf_dir = repo / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        wf_file = wf_dir / "ci.yml"
        _write_norm(
            wf_file,
            "name: CI\n"
            "on: [pull_request]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Log PR title\n"
            "        run: echo \"Checking ${{ github.event.pull_request.title }}\"\n",
        )

    mutations.append({
        "id": "MUT-ADV-09",
        "branch": "mut/adv-workflow-expr-injection",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Introduce untrusted GitHub expression interpolation inside workflow `run:` block",
        "apply": mut_adv_09,
    })

    # 15. Adversarial 10: Test assertion erosion (`assert True`) in `test_database.py`
    def mut_adv_10(repo: Path) -> None:
        p = repo / "test_database.py"
        text = _read_norm(p)
        old = (
            "    def test_acquire_returns_connection(self):\n"
            "        pool = ConnectionPool()\n"
            "        conn = pool.acquire()\n"
            "        assert conn is not None\n"
            "        assert conn[\"alive\"] is True"
        )
        new = (
            "    def test_acquire_returns_connection(self):\n"
            "        pool = ConnectionPool()\n"
            "        conn = pool.acquire()\n"
            "        assert True"
        )
        _write_norm(p, text.replace(old, new))

    mutations.append({
        "id": "MUT-ADV-10",
        "branch": "mut/adv-test-assertion-erosion",
        "kind": "adversarial",
        "expected_verdict": "DESTRUCTIVE",
        "description": "Replace real assertions in `TestConnectionPool.test_acquire_returns_connection` with `assert True`",
        "apply": mut_adv_10,
    })

    # 16. Benign 6: Safe workflow `env:` binding for untrusted PR title
    def mut_ben_06(repo: Path) -> None:
        wf_dir = repo / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        wf_file = wf_dir / "ci.yml"
        _write_norm(
            wf_file,
            "name: CI\n"
            "on: [pull_request]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11\n"
            "      - name: Log PR title safely\n"
            "        env:\n"
            "          PR_TITLE: ${{ github.event.pull_request.title }}\n"
            "        run: echo \"Checking $PR_TITLE\"\n",
        )

    mutations.append({
        "id": "MUT-BEN-06",
        "branch": "mut/ben-workflow-safe-env",
        "kind": "benign",
        "expected_verdict": "SAFE",
        "description": "Bind `github.event.pull_request.title` via step `env:` variable in workflow",
        "apply": mut_ben_06,
    })

    return mutations


def run_suite(analyser_dir: Path) -> Dict[str, Any]:
    sys.path.insert(0, str(analyser_dir))
    import analyze  # type: ignore

    mutations = _build_mutations()
    results: List[Dict[str, Any]] = []
    false_positives: List[Dict[str, Any]] = []
    false_negatives: List[Dict[str, Any]] = []

    tmpdir = Path(tempfile.mkdtemp(prefix="pg_mutation_"))
    try:
        clone_dir = tmpdir / "harness"
        _git(HARNESS_ROOT, "clone", "--quiet", "--branch", "main", str(HARNESS_ROOT), str(clone_dir))
        _git(clone_dir, "config", "user.email", "mutation-runner@payloadguard.local")
        _git(clone_dir, "config", "user.name", "PayloadGuard Mutation Runner")

        for m in mutations:
            _git(clone_dir, "checkout", "-q", "main")
            _git(clone_dir, "checkout", "-q", "-B", m["branch"])
            m["apply"](clone_dir)
            _git(clone_dir, "add", "-A")
            _git(clone_dir, "commit", "-q", "-m", f"{m['id']}: {m['description']}")

            # Run shadow mode (legacy L3 verdict)
            shadow_pa = analyze.PayloadAnalyzer(str(clone_dir), m["branch"], "main")
            shadow_pa.config.consequence["mode"] = "shadow"
            shadow_rep = shadow_pa.analyze(pr_description=m["description"])
            shadow_verdict = shadow_rep["verdict"]["status"]

            # Run enforce mode (SCG Consequence Engine v1)
            enforce_pa = analyze.PayloadAnalyzer(str(clone_dir), m["branch"], "main")
            enforce_pa.config.consequence["mode"] = "enforce"
            enforce_rep = enforce_pa.analyze(pr_description=m["description"])
            enforce_verdict = enforce_rep["verdict"]["status"]
            conseq = enforce_rep.get("consequence_analysis", {})
            detectors = sorted({f["detector_id"] for f in conseq.get("findings", [])})

            expected = m["expected_verdict"]
            if m["kind"] == "adversarial":
                passed = enforce_verdict == "DESTRUCTIVE"
                if not passed:
                    false_negatives.append({
                        "id": m["id"],
                        "branch": m["branch"],
                        "description": m["description"],
                        "shadow_verdict": shadow_verdict,
                        "enforce_verdict": enforce_verdict,
                        "detectors": detectors,
                    })
            else:
                passed = enforce_verdict in ("SAFE", "REVIEW")
                if not passed:
                    false_positives.append({
                        "id": m["id"],
                        "branch": m["branch"],
                        "description": m["description"],
                        "shadow_verdict": shadow_verdict,
                        "enforce_verdict": enforce_verdict,
                        "detectors": detectors,
                    })

            results.append({
                "id": m["id"],
                "branch": m["branch"],
                "kind": m["kind"],
                "description": m["description"],
                "expected_verdict": expected,
                "shadow_verdict": shadow_verdict,
                "enforce_verdict": enforce_verdict,
                "detectors": detectors,
                "reconciled_symbols": conseq.get("reconciled_symbols", 0),
                "passed": passed,
            })
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    summary = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyser_version": getattr(analyze, "__version__", "unknown"),
        "total_mutations": len(results),
        "adversarial_total": sum(1 for r in results if r["kind"] == "adversarial"),
        "benign_total": sum(1 for r in results if r["kind"] == "benign"),
        "passed": sum(1 for r in results if r["passed"]),
        "false_positives_count": len(false_positives),
        "false_negatives_count": len(false_negatives),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "results": results,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = REPORTS_DIR / "mutation_runs.jsonl"
    with open(jsonl_path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(summary) + "\n")

    md_path = REPORTS_DIR / "latest_mutation_summary.md"
    lines = [
        "# PayloadGuard Adversarial Harness — Mutation Testing Report",
        "",
        f"- **Timestamp (UTC):** `{summary['timestamp']}`",
        f"- **Analyser Version:** `{summary['analyser_version']}`",
        f"- **Total Mutations Evaluated:** `{summary['total_mutations']}` (`{summary['adversarial_total']}` adversarial, `{summary['benign_total']}` benign refactors)",
        f"- **Pass Rate (Enforce Mode):** `{summary['passed']}/{summary['total_mutations']}`",
        f"- **False Positives Discovered:** `{summary['false_positives_count']}`",
        f"- **False Negatives / Evasions Discovered:** `{summary['false_negatives_count']}`",
        "",
        "## Mutation Results Matrix",
        "",
        "| ID | Kind | Branch | Legacy L3 (`shadow`) | Consequence (`enforce`) | Detectors Fired | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        dets = ", ".join(f"`{d}`" for d in r["detectors"]) if r["detectors"] else "*(none)*"
        status = "PASS" if r["passed"] else ("**FALSE POSITIVE**" if r["kind"] == "benign" else "**FALSE NEGATIVE (BYPASS)**")
        lines.append(
            f"| `{r['id']}` | `{r['kind']}` | `{r['branch']}` | `{r['shadow_verdict']}` | `{r['enforce_verdict']}` | {dets} | {status} |"
        )

    if false_positives or false_negatives:
        lines.extend(["", "## Edge Cases & Findings for Engineering Analysis", ""])
        for fp_item in false_positives:
            lines.append(
                f"- **False Positive (`{fp_item['id']}` — `{fp_item['branch']}`):** {fp_item['description']} "
                f"→ Fired `{fp_item['detectors']}` (`enforce={fp_item['enforce_verdict']}`)."
            )
        for fn_item in false_negatives:
            lines.append(
                f"- **False Negative / Evasion (`{fn_item['id']}` — `{fn_item['branch']}`):** {fn_item['description']} "
                f"→ Detectors: `{fn_item['detectors']}` (`enforce={fn_item['enforce_verdict']}`)."
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PayloadGuard adversarial harness mutation suite.")
    parser.add_argument("--analyser-dir", type=Path, default=DEFAULT_ANALYSER)
    args = parser.parse_args()
    summary = run_suite(args.analyser_dir.resolve())
    print(
        f"Mutation Run Complete: {summary['passed']}/{summary['total_mutations']} passed | "
        f"FPs: {summary['false_positives_count']} | FNs: {summary['false_negatives_count']}"
    )
    for fp_item in summary["false_positives"]:
        print(f"  [FP] {fp_item['id']} ({fp_item['branch']}): {fp_item['detectors']} -> {fp_item['enforce_verdict']}")
    for fn_item in summary["false_negatives"]:
        print(f"  [FN] {fn_item['id']} ({fn_item['branch']}): {fn_item['detectors']} -> {fn_item['enforce_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
