# Intent Evidence Core

A small, dependency-free reference implementation of a governed execution kernel for AI-assisted work.

It is built around one idea: **an AI result is not a durable fact or an authorized change just because a model produced it**.

The pipeline is:

`Intent → Context Bootstrap → Minimum-Sufficient Context → Grill → Change Specification → Risk / Approval Gate → Execution → Validation → Evidence → Memory Proposal`

This public v0.1 is intentionally synthetic. It contains **no private project data, chat exports, credentials, production connectors, or user-specific Google data**.

## What this v0.1 demonstrates

- deterministic project isolation;
- bounded context selection;
- fail-closed behavior when required context is missing;
- a minimum-sufficient grill gate;
- explicit risk classification;
- approval required for high-risk changes;
- offline deterministic execution;
- validation before `DONE`;
- evidence records for every completed run;
- zero model calls and zero external writes in the default smoke path.

## Quick start

Requirements: Git and Python 3.11+.

```bash
git clone https://github.com/galiakberowwww-byte/intent-evidence-core.git
cd intent-evidence-core
python scripts/project.py setup
python scripts/project.py verify
python scripts/project.py smoke
python scripts/project.py demo
```

On Windows, use `py` instead of `python` if that is how Python is installed.

Expected smoke result includes:

```json
{
  "status": "PASS",
  "model_calls": 0,
  "external_writes": 0
}
```

## What to send back after testing

Please include:

1. OS and Python version.
2. Exact command you ran.
3. Full output for any failing command.
4. What you expected to happen.
5. Whether the architecture is understandable without explanation.
6. One place where the framework feels too complicated.
7. One failure mode you think is not covered.

Open a GitHub issue for reproducible defects or design criticism.

## Synthetic demo

`python scripts/project.py demo` runs three cases:

1. a low-risk deterministic change that completes;
2. a high-risk production-write change that is blocked without approval;
3. the same change with explicit approval, which is allowed to proceed only in the local simulator.

No real provider or external service is called.

## Non-goals of v0.1

This is not an autonomous agent platform, vector database, model router, or production connector framework. It is a compact executable reference for governance boundaries around those systems.

## License

MIT. See [LICENSE](LICENSE).
