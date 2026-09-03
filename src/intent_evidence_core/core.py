from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable


HIGH_RISK_FACTORS = {
    "ARCHITECTURE",
    "BUSINESS_LOGIC",
    "PRODUCTION_WRITE",
    "SECRETS",
    "DIFFICULT_ROLLBACK",
}


class CoreError(RuntimeError):
    pass


class ProjectMismatch(CoreError):
    pass


class ContextBudgetExceeded(CoreError):
    pass


class MissingEvidence(CoreError):
    pass


class ApprovalRequired(CoreError):
    pass


@dataclass(frozen=True)
class ContextItem:
    project_id: str
    kind: str
    content: Any
    source_ref: str
    required: bool = False

    @property
    def estimated_tokens(self) -> int:
        encoded = json.dumps(self.content, ensure_ascii=False, sort_keys=True)
        return max(1, (len(encoded) + 3) // 4)


def _as_item(raw: dict[str, Any]) -> ContextItem:
    return ContextItem(
        project_id=str(raw["project_id"]),
        kind=str(raw.get("kind", "CONTEXT")),
        content=raw.get("content"),
        source_ref=str(raw.get("source_ref", "unknown")),
        required=bool(raw.get("required", False)),
    )


def select_context(
    project_id: str,
    context_items: Iterable[dict[str, Any]],
    *,
    budget: int = 4000,
) -> dict[str, Any]:
    """Select global + project context, never another project's context."""
    eligible: list[ContextItem] = []
    for raw in context_items:
        item = _as_item(raw)
        if item.project_id not in {"GLOBAL", project_id}:
            continue
        eligible.append(item)

    required = [item for item in eligible if item.required]
    optional = [item for item in eligible if not item.required]
    required_tokens = sum(item.estimated_tokens for item in required)
    if required_tokens > budget:
        raise ContextBudgetExceeded(
            f"required context needs {required_tokens} tokens, budget is {budget}"
        )

    selected = list(required)
    used = required_tokens
    for item in sorted(optional, key=lambda x: (x.kind, x.source_ref)):
        if used + item.estimated_tokens <= budget:
            selected.append(item)
            used += item.estimated_tokens

    return {
        "project_id": project_id,
        "budget": budget,
        "selected_tokens": used,
        "selected": [
            {
                "project_id": item.project_id,
                "kind": item.kind,
                "source_ref": item.source_ref,
                "content": item.content,
            }
            for item in selected
        ],
        "dropped_count": len(eligible) - len(selected),
    }


def grill(intent: dict[str, Any], evidence_refs: list[str]) -> dict[str, Any]:
    """Ask at most one blocking question. No evidence means no specification."""
    if not intent.get("project_id"):
        return {
            "status": "BLOCKED",
            "question": "Which project does this request belong to?",
            "reason": "Project isolation cannot be enforced without a project id.",
        }
    if not str(intent.get("goal", "")).strip():
        return {
            "status": "BLOCKED",
            "question": "What verifiable outcome should this change produce?",
            "reason": "A change cannot be validated without a stated goal.",
        }
    if not evidence_refs:
        return {
            "status": "BLOCKED",
            "question": "What evidence establishes the current state or requirement?",
            "reason": "The framework does not promote unsupported assumptions into a change specification.",
        }
    return {"status": "READY", "question": None, "reason": None}


def infer_risk_factors(scope_paths: Iterable[str], requested_writes: Iterable[str]) -> list[str]:
    factors: set[str] = set()
    for path in scope_paths:
        normalized = path.lower()
        if "architecture" in normalized or "/adr/" in normalized:
            factors.add("ARCHITECTURE")
        if "business" in normalized or "policy" in normalized:
            factors.add("BUSINESS_LOGIC")
        if "secret" in normalized or ".env" in normalized:
            factors.add("SECRETS")
    if any(str(target).lower() not in {"", "none", "dry_run"} for target in requested_writes):
        factors.add("PRODUCTION_WRITE")
    return sorted(factors)


def compile_change_spec(
    *,
    intent: dict[str, Any],
    evidence_refs: list[str],
    scope_paths: list[str],
    requested_writes: list[str] | None = None,
    declared_risk_factors: list[str] | None = None,
) -> dict[str, Any]:
    requested_writes = requested_writes or []
    declared = set(declared_risk_factors or [])
    inferred = set(infer_risk_factors(scope_paths, requested_writes))
    risk_factors = sorted(declared | inferred)
    risk_class = "HIGH_RISK" if HIGH_RISK_FACTORS.intersection(risk_factors) else "STANDARD"
    payload = {
        "project_id": intent["project_id"],
        "goal": intent["goal"],
        "evidence_refs": sorted(evidence_refs),
        "scope_paths": sorted(scope_paths),
        "requested_writes": sorted(requested_writes),
        "risk_factors": risk_factors,
        "risk_class": risk_class,
    }
    payload["spec_id"] = "chg-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:12]
    return payload


def _validate(spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "project_preserved": result.get("project_id") == spec.get("project_id"),
        "goal_preserved": result.get("goal") == spec.get("goal"),
        "spec_id_preserved": result.get("spec_id") == spec.get("spec_id"),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def run_pipeline(
    *,
    intent: dict[str, Any],
    context_items: list[dict[str, Any]],
    evidence_refs: list[str],
    scope_paths: list[str],
    requested_writes: list[str] | None = None,
    approval: bool = False,
    context_budget: int = 4000,
) -> dict[str, Any]:
    """Run the deterministic public reference pipeline.

    This simulator never performs a model call or an external write.
    """
    grill_result = grill(intent, evidence_refs)
    if grill_result["status"] != "READY":
        raise MissingEvidence(grill_result["reason"])

    context = select_context(intent["project_id"], context_items, budget=context_budget)
    spec = compile_change_spec(
        intent=intent,
        evidence_refs=evidence_refs,
        scope_paths=scope_paths,
        requested_writes=requested_writes,
    )
    if spec["risk_class"] == "HIGH_RISK" and not approval:
        raise ApprovalRequired(
            "high-risk change requires explicit approval before execution"
        )

    # Deterministic local executor. It mirrors intent/spec but performs no I/O.
    execution = {
        "project_id": spec["project_id"],
        "goal": spec["goal"],
        "spec_id": spec["spec_id"],
        "mode": "OFFLINE_SIMULATION",
    }
    validation = _validate(spec, execution)
    if validation["status"] != "PASS":
        raise CoreError("validation failed")

    evidence_payload = {
        "spec_id": spec["spec_id"],
        "validation": validation,
        "context_sources": [item["source_ref"] for item in context["selected"]],
        "model_calls": 0,
        "external_writes": 0,
    }
    evidence_id = "ev-" + hashlib.sha256(
        json.dumps(evidence_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]

    return {
        "status": "DONE",
        "project_id": spec["project_id"],
        "specification": spec,
        "context": context,
        "execution": execution,
        "validation": validation,
        "evidence": {"evidence_id": evidence_id, **evidence_payload},
        "memory_proposal": {
            "status": "PROPOSED",
            "statement": f"Verified change {spec['spec_id']} completed in offline simulation.",
            "evidence_ref": evidence_id,
        },
        "model_calls": 0,
        "external_writes": 0,
    }
