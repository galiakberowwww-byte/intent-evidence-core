# Architecture

Intent Evidence Core separates **what a user wants**, **what is known**, **what may be changed**, and **what is proven afterward**.

```text
Human intent
    ↓
Project resolution / Context Bootstrap
    ↓
Project-isolated minimum-sufficient context
    ↓
Grill: enough evidence and a verifiable goal?
    ↓
Change Specification
    ↓
Risk inference + declared risk
    ↓
Approval Gate for HIGH_RISK
    ↓
Deterministic local executor in v0.1
    ↓
Validator
    ↓
Evidence record
    ↓
Memory proposal (never auto-promoted to fact)
```

## Core invariants

1. Context from another project is not selected.
2. Required context that does not fit the budget blocks execution.
3. Missing evidence blocks specification/execution.
4. High-risk changes require explicit approval.
5. `DONE` requires validator PASS and evidence.
6. Model output is never automatically canonical memory.
7. Default public smoke performs zero model calls and zero external writes.

## Risk factors

`ARCHITECTURE`, `BUSINESS_LOGIC`, `PRODUCTION_WRITE`, `SECRETS`, and `DIFFICULT_ROLLBACK` are high-risk factors.

The public implementation infers a small subset from scope paths and requested writes. A production system should expand this with repository-specific protected surfaces and diff/evidence checks.

## Why no model call in v0.1?

The governance kernel should be testable independently from model quality, provider availability, credentials, price, and nondeterminism. Provider adapters belong outside the deterministic acceptance path and must be explicitly opted into.
