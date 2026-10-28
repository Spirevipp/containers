# aria2 updates

- `manifest.json`: release sources, version/hash ARGs and test paths.
- `refresh.py`: updates asset hashes alongside version bumps; rejects changed
  assets without a version change.
- `test_refresh.py`: offline checksum-update regression tests.

Maintenance steps: [AGENTS.md](../AGENTS.md).
GitHub configuration: [UPDATES.md](../../.github/UPDATES.md).
