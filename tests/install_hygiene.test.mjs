// Phase D verification: no install-time side effects in any package.
// These tests parse package.json files and assert that nothing in the
// scripts block runs on `npm install` for end users.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const INSTALL_TIME_HOOKS = new Set([
  'preinstall',
  'install',
  'postinstall',
  'prepare',     // runs on `npm install` for git deps + `npm publish`
  // 'prepublishOnly' is publish-time only; safe.
]);

function load(rel) {
  return JSON.parse(readFileSync(path.join(ROOT, rel), 'utf-8'));
}

const PACKAGES = [
  'package.json',
  'packages/core/package.json',
  'packages/mcp-server/package.json',
];

for (const pkgPath of PACKAGES) {
  test(`${pkgPath} declares no install-time hooks`, () => {
    const pkg = load(pkgPath);
    const scripts = pkg.scripts || {};
    const hooks = Object.keys(scripts).filter((k) => INSTALL_TIME_HOOKS.has(k));
    assert.deepEqual(hooks, [], `${pkgPath} should not declare ${[...INSTALL_TIME_HOOKS].join('/')} scripts`);
  });
}

test('no package declares a "files" entry that ships unwanted content', () => {
  const main = load('package.json');
  const files = main.files || [];
  // Sanity: must include at least bin/ and key docs
  assert.ok(files.includes('bin/'));
  assert.ok(files.includes('README.md'));
  // Must NOT include the v0.x mass-bloat dirs we explicitly removed
  for (const banned of ['agentpress/material-kits/', 'agentpress/evidence/', 'agentpress/gorilla/']) {
    assert.ok(!files.includes(banned), `files should not include ${banned}`);
  }
});

test('main package.json scripts do not shell out to network commands', () => {
  const main = load('package.json');
  for (const [name, cmd] of Object.entries(main.scripts || {})) {
    for (const bad of ['curl http', 'wget http', 'npm publish', 'pip install', 'sudo ']) {
      assert.ok(!cmd.includes(bad), `script "${name}" must not run "${bad}": ${cmd}`);
    }
  }
});
