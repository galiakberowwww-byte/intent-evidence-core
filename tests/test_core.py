from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from intent_evidence_core.core import (  # noqa: E402
    ApprovalRequired,
    ContextBudgetExceeded,
    MissingEvidence,
    compile_change_spec,
    grill,
    infer_risk_factors,
    run_pipeline,
    select_context,
)


class CoreTests(unittest.TestCase):
    def test_project_isolation(self):
        selected = select_context("A", [
            {"project_id": "A", "source_ref": "a", "content": "keep"},
            {"project_id": "B", "source_ref": "b", "content": "drop"},
            {"project_id": "GLOBAL", "source_ref": "g", "content": "keep"},
        ])
        self.assertEqual({x["project_id"] for x in selected["selected"]}, {"A", "GLOBAL"})

    def test_required_context_over_budget_fails_closed(self):
        with self.assertRaises(ContextBudgetExceeded):
            select_context("A", [{"project_id": "A", "source_ref": "a", "required": True, "content": "x" * 100}], budget=1)

    def test_optional_context_can_be_dropped(self):
        selected = select_context("A", [
            {"project_id": "A", "source_ref": "required", "required": True, "content": "ok"},
            {"project_id": "A", "source_ref": "optional", "content": "x" * 1000},
        ], budget=5)
        self.assertEqual(selected["dropped_count"], 1)

    def test_grill_requires_project(self):
        self.assertEqual(grill({"goal": "x"}, ["e"])["status"], "BLOCKED")

    def test_grill_requires_goal(self):
        self.assertEqual(grill({"project_id": "A"}, ["e"])["status"], "BLOCKED")

    def test_grill_requires_evidence(self):
        self.assertEqual(grill({"project_id": "A", "goal": "x"}, [])["status"], "BLOCKED")

    def test_missing_evidence_stops_pipeline(self):
        with self.assertRaises(MissingEvidence):
            run_pipeline(intent={"project_id": "A", "goal": "x"}, context_items=[], evidence_refs=[], scope_paths=[])

    def test_production_write_is_high_risk(self):
        spec = compile_change_spec(intent={"project_id": "A", "goal": "x"}, evidence_refs=["e"], scope_paths=[], requested_writes=["prod"])
        self.assertEqual(spec["risk_class"], "HIGH_RISK")
        self.assertIn("PRODUCTION_WRITE", spec["risk_factors"])

    def test_business_path_is_high_risk(self):
        self.assertIn("BUSINESS_LOGIC", infer_risk_factors(["src/business/policy.py"], []))

    def test_high_risk_requires_approval(self):
        with self.assertRaises(ApprovalRequired):
            run_pipeline(
                intent={"project_id": "A", "goal": "x"},
                context_items=[], evidence_refs=["e"], scope_paths=[], requested_writes=["prod"],
            )

    def test_high_risk_with_approval_remains_offline(self):
        result = run_pipeline(
            intent={"project_id": "A", "goal": "x"},
            context_items=[], evidence_refs=["e"], scope_paths=[], requested_writes=["prod"], approval=True,
        )
        self.assertEqual(result["external_writes"], 0)
        self.assertEqual(result["model_calls"], 0)

    def test_done_has_validation_and_evidence(self):
        result = run_pipeline(
            intent={"project_id": "A", "goal": "x"},
            context_items=[], evidence_refs=["e"], scope_paths=["examples/x.json"],
        )
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["validation"]["status"], "PASS")
        self.assertTrue(result["evidence"]["evidence_id"].startswith("ev-"))
        self.assertEqual(result["memory_proposal"]["status"], "PROPOSED")


if __name__ == "__main__":
    unittest.main()
