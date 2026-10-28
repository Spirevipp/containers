# Containers

Personal OCI container images for Linux amd64 and arm64.

- [aria2](aria2/README.md): resumable direct downloads with the AriaNg web UI;
  BitTorrent and Metalink are disabled.

Images are published to GHCR. Pull requests build and test affected containers
on both architectures before merging.

Monthly dependency checks group updates per container. Minor/patch and image-digest
updates can auto-merge after checks pass; major versions and Alpine release changes
require manual review. Optional monthly rebuilds pick up package fixes.

Scheduled updates and rebuilds are disabled until configured:
[GitHub update setup](.github/UPDATES.md).
