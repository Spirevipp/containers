# aria2 maintenance

- Build from the repository root:
  `podman build --format oci -f aria2/Containerfile -t localhost/aria2:dev aria2`.
  Buildah uses `buildah bud --format oci`; Docker/WSLc use
  `<engine> build -f aria2/Containerfile -t aria2:dev aria2`.
- Run `CONTAINER_ENGINE=podman python3 aria2/tests/smoke.py localhost/aria2:dev`.
  For PowerShell/WSLc, set `$env:CONTAINER_ENGINE = 'wslc'`, then run
  `python aria2/tests/smoke.py aria2:dev`. The test manages its own volumes/network.
- Keep release sources and asset mappings in `updates/manifest.json`.
- For version bumps, leave existing hashes, then run `python updates/refresh.py`
  from this folder **before committing**; it compares against `git show HEAD`.
- Check changes with `python updates/test_refresh.py`; verify upstream hashes with
  `python updates/refresh.py --check` when changing versions/assets.
- Preserve BitTorrent/Metalink compile exclusions and download/session persistence.
- Keep versions and archive checksums pinned, including the Alpine image digest.
  Alpine package patch versions float so rebuilds pick up fixes.
- `.github/workflows/aria2.yml` publishes `:latest` on relevant `main` pushes and
  manual default-branch runs. Tags `aria2-v<version>` publish `:<version>`;
  published images also receive `:sha-<12-character-commit>`.
