# Tester guide

## Baseline

Run from a clean checkout:

```bash
python scripts/project.py setup
python scripts/project.py verify
python scripts/project.py smoke
python scripts/project.py demo
```

## Adversarial checks

Try changing the demo or writing a small Python script to test these claims:

- Add context for a different project and confirm it is not selected.
- Reduce the context budget below required context and confirm the run blocks.
- Remove all evidence refs and confirm the run blocks.
- Request a production write without approval and confirm the run blocks.
- Grant approval and confirm the simulator still performs zero external writes.
- Modify the executor result so validation fails and confirm `DONE` is impossible.

## Useful feedback

The best feedback is a reproducible counterexample: a case where the stated invariant is violated, or where the framework blocks legitimate work for no good reason.
