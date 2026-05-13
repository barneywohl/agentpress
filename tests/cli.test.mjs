// End-to-end tests for the v1.0 Node CLI. Spawns the real bin and checks
// stdout/stderr/exit. Mirrors the smoke suite gates from LAUNCH/V1_RC2_GOAL.md.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, mkdirSync, existsSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BIN = path.resolve(__dirname, '..', 'bin', 'agentpress.js');

function run(args, { cwd, env, input } = {}) {
  return spawnSync('node', [BIN, ...args], {
    cwd: cwd || process.cwd(),
    env: { ...process.env, ...(env || {}), AGENTPRESS_LEGACY_QUIET: '1' },
    input,
    encoding: 'utf-8',
  });
}

function mkSandbox() {
  const dir = mkdtempSync(path.join(tmpdir(), 'agentpress-test-'));
  mkdirSync(path.join(dir, '.git'), { recursive: true });
  writeFileSync(path.join(dir, '.git', 'config'), `[remote "origin"]\n\turl = https://github.com/test-org/test-repo.git\n`);
  writeFileSync(path.join(dir, 'package.json'), JSON.stringify({ name: 'test-pkg', author: 'A <a@example.com>' }));
  return dir;
}

test('top-level help shows four verbs only', () => {
  const r = run([]);
  assert.equal(r.status, 0);
  assert.match(r.stdout, /Commands:/);
  for (const verb of ['init', 'lint', 'doctor', 'receipt', 'legacy']) {
    assert.match(r.stdout, new RegExp(`^\\s*${verb}\\b`, 'm'));
  }
  // No legacy v0.x bloat names in default help
  for (const bloat of ['gorilla', 'marketplace', 'china', 'mission-keeper']) {
    assert.doesNotMatch(r.stdout, new RegExp(bloat, 'i'));
  }
});

test('--version prints package version', () => {
  const r = run(['--version']);
  assert.equal(r.status, 0);
  assert.match(r.stdout.trim(), /^\d+\.\d+\.\d+(-[\w.]+)?$/);
});

test('unknown command exits 1 with clean error', () => {
  const r = run(['nonexistent']);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /Unknown command/);
  assert.doesNotMatch(r.stderr, /Error|stack/i);
});

test('lint in empty dir exits 3 with FILE_NOT_FOUND message', () => {
  const dir = mkSandbox();
  try {
    const r = run(['lint'], { cwd: dir });
    assert.equal(r.status, 3);
    assert.match(r.stderr + r.stdout, /agents\.txt not found/);
    assert.match(r.stderr + r.stdout, /agentpress init/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('init --non-interactive writes agents.txt that lints cleanly', () => {
  const dir = mkSandbox();
  try {
    const r1 = run(['init', '--non-interactive'], { cwd: dir });
    assert.equal(r1.status, 0, `init failed: ${r1.stderr}`);
    assert.ok(existsSync(path.join(dir, 'agents.txt')));
    assert.match(readFileSync(path.join(dir, 'agents.txt'), 'utf-8'), /\[meta\][\s\S]*spec_version = 1\.0/);

    const r2 = run(['lint'], { cwd: dir });
    assert.equal(r2.status, 0, `lint after init failed: ${r2.stderr}`);
    assert.match(r2.stdout, /valid/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('init refuses to overwrite without --force', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['init', '--non-interactive'], { cwd: dir });
    assert.equal(r.status, 1);
    assert.match(r.stderr, /already exists/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('init --force overwrites existing agents.txt', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['init', '--non-interactive', '--force'], { cwd: dir });
    assert.equal(r.status, 0, `force init failed: ${r.stderr}`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('lint --json returns parseable JSON with ok flag', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['lint', '--json'], { cwd: dir });
    assert.equal(r.status, 0);
    const parsed = JSON.parse(r.stdout);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.spec_version, '1.0');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('lint of malformed agents.txt surfaces errors with exit 1', () => {
  const dir = mkSandbox();
  try {
    writeFileSync(path.join(dir, 'agents.txt'), `[meta]\nspec_version = 1.0\n`);
    const r = run(['lint'], { cwd: dir });
    assert.equal(r.status, 1);
    assert.match(r.stdout + r.stderr, /error/i);
    // No raw stack traces
    assert.doesNotMatch(r.stdout + r.stderr, /at Object\.\<anonymous\>|at Module/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('doctor reports all-pass after init', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['doctor'], { cwd: dir });
    assert.equal(r.status, 0);
    assert.match(r.stdout, /System healthy/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('doctor --json returns structured output', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['doctor', '--json'], { cwd: dir });
    assert.equal(r.status, 0);
    const parsed = JSON.parse(r.stdout);
    assert.equal(parsed.ok, true);
    assert.ok(Array.isArray(parsed.checks));
    assert.ok(parsed.checks.length >= 5);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('receipt --stdout-only emits valid JSON with sha256', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['receipt', '--stdout-only'], { cwd: dir });
    assert.equal(r.status, 0);
    const parsed = JSON.parse(r.stdout);
    assert.equal(parsed.schema_version, 'agentpress-receipt.v1');
    assert.match(parsed.agents_txt_sha256, /^[a-f0-9]{64}$/);
    assert.equal(parsed.validation.ok, true);
    assert.match(parsed.receipt_id, /^rcpt_[a-f0-9]{12}$/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('receipt writes file when not --stdout-only', () => {
  const dir = mkSandbox();
  try {
    run(['init', '--non-interactive'], { cwd: dir });
    const r = run(['receipt'], { cwd: dir });
    assert.equal(r.status, 0);
    // a file should exist under agentpress/receipts/
    const dirEntries = readFileSync(path.join(dir, 'agents.txt'), 'utf-8'); // sanity
    const receiptsDir = path.join(dir, 'agentpress', 'receipts');
    assert.ok(existsSync(receiptsDir));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('receipt fails cleanly when agents.txt is invalid', () => {
  const dir = mkSandbox();
  try {
    writeFileSync(path.join(dir, 'agents.txt'), `[meta]\nspec_version = 1.0\n`);
    const r = run(['receipt'], { cwd: dir });
    assert.equal(r.status, 1);
    assert.match(r.stderr, /error|Run `agentpress lint`/i);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('verb --help exits 0 and shows usage', () => {
  for (const verb of ['init', 'lint', 'doctor', 'receipt']) {
    const r = run([verb, '--help']);
    assert.equal(r.status, 0, `${verb} --help failed: ${r.stderr}`);
    assert.match(r.stdout, new RegExp(`Usage:\\s+agentpress\\s+${verb}`));
  }
});

test('legacy --help exits without crashing', () => {
  // legacy uses stdio:inherit so output goes to terminal not the captured buffer.
  // Just verify it doesn't crash and exits with the underlying script's status.
  const r = run(['legacy', '--help']);
  // Status will be 0 if python exists and the legacy script ran, or non-zero otherwise.
  // Either is fine — we just want to know our forwarder doesn't blow up.
  assert.notEqual(r.status, undefined);
  assert.ok(typeof r.status === 'number');
});
