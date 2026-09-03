#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REQUIRED = [ROOT / "README.md", ROOT / "LICENSE", ROOT / "src", ROOT / "tests", ROOT / "docs"]


def setup() -> dict:
    checks = {
        "python_3_11_plus": sys.version_info >= (3, 11),
        "required_paths": all(path.exists() for path in REQUIRED),
    }
    try:
        import intent_evidence_core  # noqa: F401
    except Exception:
        checks["core_import"] = False
    else:
        checks["core_import"] = True
    return {"command": "setup", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def smoke() -> dict:
    from intent_evidence_core import run_pipeline

    result = run_pipeline(
        intent={"project_id": "DEMO", "goal": "Verify the deterministic public smoke path."},
        context_items=[
            {"project_id": "GLOBAL", "kind": "RULE", "source_ref": "repo:README.md", "required": True, "content": {"fail_closed": True}},
            {"project_id": "DEMO", "kind": "CURRENT_STATE", "source_ref": "example:demo", "content": {"state": "synthetic"}},
            {"project_id": "OTHER", "kind": "CURRENT_STATE", "source_ref": "example:must-not-leak", "content": {"secret": "not selected"}},
        ],
        evidence_refs=["repo:README.md"],
        scope_paths=["examples/demo.json"],
    )
    checks = {
        "done": result["status"] == "DONE",
        "validation_pass": result["validation"]["status"] == "PASS",
        "model_calls_zero": result["model_calls"] == 0,
        "external_writes_zero": result["external_writes"] == 0,
        "other_project_excluded": all(
            item["project_id"] != "OTHER" for item in result["context"]["selected"]
        ),
    }
    return {
        "command": "smoke",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "model_calls": result["model_calls"],
        "external_writes": result["external_writes"],
        "evidence_id": result["evidence"]["evidence_id"],
    }


def demo() -> int:
    from intent_evidence_core import ApprovalRequired, run_pipeline

    base = dict(
        intent={"project_id": "SYNTHETIC-SHOP", "goal": "Add a validation rule for synthetic orders."},
        context_items=[
            {"project_id": "GLOBAL", "kind": "RULE", "source_ref": "demo:global", "required": True, "content": {"verified_done_only": True}},
            {"project_id": "SYNTHETIC-SHOP", "kind": "CURRENT_STATE", "source_ref": "demo:order-contract", "required": True, "content": {"amount": "positive integer"}},
        ],
        evidence_refs=["demo:order-contract"],
    )

    low = run_pipeline(**base, scope_paths=["examples/order_validation.json"])
    print("CASE 1 — low risk: PASS")
    print(json.dumps({"status": low["status"], "spec_id": low["specification"]["spec_id"]}, indent=2))

    high_kwargs = dict(base, scope_paths=["src/business/policy.py"], requested_writes=["production-orders"])
    try:
        run_pipeline(**high_kwargs)
    except ApprovalRequired as exc:
        print("CASE 2 — high risk without approval: BLOCKED")
        print(str(exc))
    else:
        print("CASE 2 — unexpected PASS")
        return 1

    high = run_pipeline(**high_kwargs, approval=True)
    print("CASE 3 — high risk with approval: PASS (offline simulator only)")
    print(json.dumps({"status": high["status"], "risk_class": high["specification"]["risk_class"], "external_writes": high["external_writes"]}, indent=2))
    return 0


def delegate(args: list[str]) -> int:
    return subprocess.run(args, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["setup", "test", "verify", "smoke", "demo"])
    command = parser.parse_args().command
    if command == "setup":
        result = setup(); print(json.dumps(result, indent=2)); return 0 if result["status"] == "PASS" else 1
    if command == "smoke":
        result = smoke(); print(json.dumps(result, indent=2)); return 0 if result["status"] == "PASS" else 1
    if command == "demo":
        return demo()
    if command == "test":
        return delegate([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    # verify intentionally delegates to the same test suite plus smoke.
    rc = delegate([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    if rc != 0:
        return rc
    result = smoke(); print(json.dumps(result, indent=2)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
