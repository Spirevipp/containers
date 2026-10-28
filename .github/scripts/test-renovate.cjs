const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const config = require('../renovate.cjs');
const policy = config.repositories[0];
const root = path.resolve(__dirname, '../..');
const files = fs.readdirSync(root, {withFileTypes: true})
  .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(root, entry.name, 'Containerfile')))
  .map((entry) => `${entry.name}/Containerfile`);
files.push('.github/workflows/updates.yml');

assert.equal(policy.platformAutomerge, true);
assert.equal(policy.dependencyDashboard, false);
assert(policy.packageRules.some((rule) => rule.matchUpdateTypes.includes('major') && rule.automerge === false));
for (const manager of policy.customManagers) {
  const matchedFiles = [];
  for (const file of files) {
    if (!fs.existsSync(path.join(root, file))) continue;
    const matchesFile = manager.managerFilePatterns.some((pattern) => new RegExp(pattern.slice(1, -1)).test(file));
    if (!matchesFile) continue;
    const text = fs.readFileSync(path.join(root, file), 'utf8');
    assert(manager.matchStrings.some((pattern) => new RegExp(pattern).test(text)), `No version extracted from ${file}`);
    matchedFiles.push(file);
  }
  assert(matchedFiles.length > 0, `Manager does not match a tracked file: ${manager.depNameTemplate}`);
}
for (const rule of policy.packageRules.filter((rule) => rule.postUpgradeTasks)) {
  for (const command of rule.postUpgradeTasks.commands) {
    assert(config.allowedCommands.some((pattern) => new RegExp(pattern).test(command)));
    assert(!config.allowedCommands.some((pattern) => new RegExp(pattern).test(command + '; echo unsafe')));
  }
}
console.log('PASS: update policy, dependency extraction, and post-upgrade command allowlist.');
