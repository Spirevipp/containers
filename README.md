# Containers

Personal container images. Each image has its own build context and documentation.

- [aria2](aria2/README.md): aria2 and AriaNg, with BitTorrent and Metalink compiled out.

The aria2 GitHub Actions workflow builds and tests pull requests, then publishes
`ghcr.io/<owner>/<repository>/aria2` on pushes to `main`. No Docker Hub account or
personal access token is needed.
