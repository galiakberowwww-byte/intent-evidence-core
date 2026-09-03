# Contributing

Contributions are welcome, especially reproducible failure cases.

Before opening a pull request:

1. State the invariant or behavior you want to change.
2. Add or update a test that demonstrates it.
3. Run `python scripts/project.py verify`.
4. Keep the default path dependency-free, offline, and deterministic.
5. Do not add credentials, private datasets, raw chat logs, or production endpoints.

For architectural changes, open an issue first and explain the failure mode the change is intended to address.
