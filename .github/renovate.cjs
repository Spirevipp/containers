// Shared policy only. Dependency names, assets and scripts live with containers.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const customManagers = [];
const packageRules = [
  {matchUpdateTypes: ['minor', 'patch', 'digest', 'pinDigest'], automerge: true},
  {matchUpdateTypes: ['major'], automerge: false},
  {
    matchManagers: ['github-actions'],
    matchUpdateTypes: ['minor', 'patch', 'digest', 'pinDigest'],
    groupName: 'GitHub Actions non-major updates',
  },
];
const allowedCommands = [];

for (const entry of fs.readdirSync(root, {withFileTypes: true})) {
  if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
  const directory = path.join(root, entry.name);
  const manifestPath = path.join(directory, 'updates', 'manifest.json');
  if (!fs.existsSync(manifestPath)) continue;
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const file = `${entry.name}/${manifest.containerfile}`;
  for (const dependency of manifest.dependencies) {
    customManagers.push({
      customType: 'regex',
      managerFilePatterns: [`/^${escapeRegex(file)}$/`],
      matchStrings: [`(?:^|\\r?\\n)ARG ${escapeRegex(dependency.arg)}=(?<currentValue>[0-9.]+)(?:\\r?\\n|$)`],
      depNameTemplate: dependency.repository,
      datasourceTemplate: 'github-releases',
      extractVersionTemplate: dependency.extractVersion,
      versioningTemplate: dependency.versioning,
    });
  }
  const script = path.join(directory, manifest.refreshScript).split(path.sep).join('/');
  const command = `python3 ${script}`;
  allowedCommands.push(`^${escapeRegex(command)}$`);
  packageRules.push({
    matchFileNames: [file],
    matchDatasources: ['github-releases'],
    postUpgradeTasks: {
      commands: [command],
      workingDirTemplate: entry.name,
      fileFilters: [file],
      executionMode: 'branch',
    },
  });
  packageRules.push({
    matchFileNames: [file],
    matchUpdateTypes: ['minor', 'patch', 'digest', 'pinDigest'],
    groupName: `${entry.name} non-major updates`,
  });
  for (const base of manifest.baseImages || []) {
    if (base.manualReleaseUpdates) packageRules.push({
      matchFileNames: [file],
      matchDatasources: ['docker'],
      matchPackageNames: [base.name],
      matchUpdateTypes: ['minor', 'major'],
      automerge: false,
      groupName: null,
    });
  }
}

// Keep the updater itself maintained as well as pinned action SHAs.
customManagers.push({
  customType: 'regex',
  managerFilePatterns: ['/^\\.github/workflows/updates\\.yml$/'],
  matchStrings: ['RENOVATE_VERSION: "(?<currentValue>[0-9.]+)"'],
  depNameTemplate: 'renovate', datasourceTemplate: 'npm', versioningTemplate: 'semver',
});

module.exports = {
  platform: 'github',
  onboarding: false,
  requireConfig: 'ignored',
  binarySource: 'global',
  allowedCommands,
  repositories: [{
    repository: process.env.GITHUB_REPOSITORY || 'Spirevipp/containers',
    extends: ['config:recommended'],
    dependencyDashboard: false,
    enabledManagers: ['dockerfile', 'custom.regex', 'github-actions'],
    pinDigests: true,
    ignoreUnstable: true,
    minimumReleaseAge: '3 days',
    minimumReleaseAgeBehaviour: 'timestamp-optional',
    internalChecksFilter: 'strict',
    separateMajorMinor: true,
    automergeType: 'pr',
    platformAutomerge: true,
    automergeStrategy: 'squash',
    rebaseWhen: 'behind-base-branch',
    prConcurrentLimit: 5,
    customManagers,
    packageRules,
  }],
};
