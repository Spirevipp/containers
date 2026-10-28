#!/usr/bin/env python3
"""Refresh release-asset hashes after a version change; never execute downloads."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


def argument(text, name):
    matches = re.findall(rf"^ARG {re.escape(name)}=([^\r\n]+)$", text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one ARG {name}")
    return matches[0]


def asset_hashes(dependency, version):
    if not re.fullmatch(r"\d+(?:\.\d+){1,3}", version):
        raise ValueError(f"Unsupported release version: {version}")
    tag = urllib.parse.quote(dependency["tag"].format(version=version), safe="")
    url = f'https://api.github.com/repos/{dependency["repository"]}/releases/tags/{tag}'
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "containers-release-updater"}
    token = os.environ.get("GITHUB_COM_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        release = json.load(response)
    if release.get("draft") or release.get("prerelease"):
        raise ValueError(f"Refusing draft/prerelease: {tag}")
    assets = {asset["name"]: asset for asset in release["assets"]}
    result = {}
    for definition in dependency["assets"]:
        name = definition["file"].format(version=version)
        asset = assets.get(name)
        if not asset:
            raise ValueError(f'Missing release asset: {dependency["repository"]}/{tag}/{name}')
        download = asset["browser_download_url"]
        if not download.startswith("https://github.com/"):
            raise ValueError(f"Unexpected release download URL: {download}")
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(download, timeout=60) as response:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 256 * 1024 * 1024:
                    raise ValueError(f"Release asset exceeds 256 MiB: {name}")
                digest.update(chunk)
        actual = digest.hexdigest()
        published = asset.get("digest")
        if published and published != f"sha256:{actual}":
            raise ValueError(f"GitHub's published digest does not match: {name}")
        result[definition["arg"]] = actual
    return result


def refresh(text, original, manifest, fetch=asset_hashes, check=False):
    updated = text
    for dependency in manifest["dependencies"]:
        version = argument(text, dependency["arg"])
        old_version = argument(original, dependency["arg"])
        hashes = fetch(dependency, version)
        for asset in dependency["assets"]:
            name = asset["arg"]
            current = argument(text, name)
            expected = hashes[name]
            if current == expected:
                continue
            if check:
                raise ValueError(f"Checksum mismatch: {name} at version {version}")
            if version == old_version:
                raise ValueError(f"Asset changed without a version change: {name}. Review it manually.")
            updated = re.sub(rf"^ARG {re.escape(name)}=[^\r\n]+$",
                             f"ARG {name}={expected}", updated, flags=re.MULTILINE)
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify all hashes without modifying files")
    parser.add_argument("--container-dir", type=Path, default=None)
    args = parser.parse_args()
    # Renovate invokes this trusted script with the updated container as cwd.
    directory = args.container_dir or Path.cwd()
    if not (directory / "updates/manifest.json").is_file():
        directory /= "aria2"
    directory = directory.resolve()
    manifest = json.loads((directory / "updates/manifest.json").read_text())
    containerfile = directory / manifest["containerfile"]
    text = containerfile.read_text()
    if args.check:
        original = text
    else:
        repository = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=directory, text=True).strip()).resolve()
        relative = containerfile.relative_to(repository).as_posix()
        original = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=repository, text=True)
    updated = refresh(text, original, manifest, check=args.check)
    if updated != text:
        containerfile.write_text(updated, newline="\n")
        print("Updated release checksums in", containerfile.name)
    else:
        print("Release checksums verified; no changes needed.")


if __name__ == "__main__":
    main()
