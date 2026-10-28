# Repository instructions

- Use portable `Containerfile` builds; retain Podman, Docker and WSLc compatibility.
- Keep each container's metadata, scripts, tests and ignore rules in its own folder.
  Shared tooling under `.github/` must stay container-agnostic.
- New containers need `updates/manifest.json`, its referenced scripts/tests, and a
  smoke test. Use the existing container layout as the example.
- Read a container's `AGENTS.md` before changing its version pins or update scripts.
- Preserve the always-reported **Container CI** gate and read-only PR permissions.
- For shared update tooling changes, run `python .github/scripts/test_containers.py`,
  `python .github/scripts/containers.py validate` and
  `node .github/scripts/test-renovate.cjs` from the repository root.
- Reuse `.github/workflows/build-container.yml` for native amd64/arm64 builds,
  smoke tests and GHCR publishing; publishing uses `GITHUB_TOKEN`.
- Keep major versions and Alpine release changes out of automatic merge groups.
- Keep GitHub setup docs concise. Never commit App private keys or tokens.
