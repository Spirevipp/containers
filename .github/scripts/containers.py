#!/usr/bin/env python3
"""Discover containers, select changed folders, and dispatch their own tests."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def discover(root=ROOT):
    containers = {}
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith('.') or not (folder / 'Containerfile').is_file():
            continue
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', folder.name):
            raise ValueError(f'Unsupported container folder name: {folder.name}')
        manifest = json.loads((folder / 'updates/manifest.json').read_text())
        if manifest['schemaVersion'] != 1:
            raise ValueError(f'Unsupported manifest version in {folder}')
        for key in ('containerfile', 'smokeTest', 'validationTests', 'refreshScript'):
            target = (folder / manifest[key]).resolve()
            if not target.is_relative_to(folder.resolve()) or not target.is_file():
                raise ValueError(f'Invalid {key} in {folder.name}')
        names = set()
        for dep in manifest['dependencies']:
            for name in [dep['arg'], *(asset['arg'] for asset in dep['assets'])]:
                if not re.fullmatch(r'[A-Z][A-Z0-9_]*', name) or name in names:
                    raise ValueError(f'Invalid or repeated ARG in {folder.name}: {name}')
                names.add(name)
                text = (folder / manifest['containerfile']).read_text()
                if len(re.findall(rf'^ARG {name}=.+$', text, re.MULTILINE)) != 1:
                    raise ValueError(f'Missing/ambiguous ARG in {folder.name}: {name}')
        containers[folder.name] = manifest
    if not containers:
        raise ValueError('No containers were discovered')
    return containers


def select(containers, changed):
    if any(name.startswith('.github/') or name == '.gitattributes' for name in changed):
        return list(containers)
    return [name for name in containers if any(file.startswith(name + '/') for file in changed)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['discover', 'validate', 'smoke'])
    parser.add_argument('--base')
    parser.add_argument('--container')
    parser.add_argument('--image')
    args = parser.parse_args()
    containers = discover()
    if args.container and args.container not in containers:
        parser.error('Unknown container: ' + args.container)
    if args.operation == 'discover':
        if args.base:
            changed = subprocess.check_output(
                ['git', 'diff', '--name-only', args.base, 'HEAD', '--'], cwd=ROOT, text=True).splitlines()
            selected = select(containers, changed)
        else:
            selected = list(containers)
        print(json.dumps({'container': selected}))
    elif args.operation == 'validate':
        for name, manifest in containers.items():
            if args.container and name != args.container:
                continue
            subprocess.run([sys.executable, str(ROOT / name / manifest['validationTests'])], check=True)
    else:
        if args.container not in containers or not args.image:
            parser.error('smoke requires a known --container and --image')
        subprocess.run([sys.executable, str(ROOT / args.container / containers[args.container]['smokeTest']),
                        args.image], check=True)


if __name__ == '__main__':
    main()
