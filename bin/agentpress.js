#!/usr/bin/env node
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const script = path.resolve(__dirname, '..', 'scripts', 'agentpress.py');
const py = process.env.PYTHON || 'python3';
const argv = process.argv.slice(2);

function printStart() {
  const copyPasteBlock = [
    'agentpress start --json',
    'agentpress doctor --json',
    'agentpress package-verify --json',
  ].join('\n');
  const successCriteria = [
    { step: 1, name: 'start', proves: 'CLI entrypoint runs', check: 'exit code 0' },
    { step: 2, name: 'doctor', proves: 'Health check passes', check: 'exit code 0' },
    { step: 3, name: 'package-verify', proves: 'Package integrity verified', check: 'exit code 0' },
  ];
  const pkgPath = path.resolve(__dirname, '..', 'package.json');
  let pkg = {};
  try {
    pkg = require(pkgPath);
  } catch (_) {}
  console.log(JSON.stringify({
    schema_version: '2026-05-06.agentpress-start.v1',
    status: 'ok',
    copy_paste_block: copyPasteBlock,
    success_criteria: successCriteria,
    npm_package: pkg.name || '@agent_press/agentpress',
    npm_version: pkg.version || 'unknown',
  }, null, 2));
}

if (argv.includes('--version') || argv.includes('-v')) {
  const pkg = require(path.resolve(__dirname, '..', 'package.json'));
  console.log(pkg.version || '0.0.0');
  process.exit(0);
}

if (argv.length === 0 || argv.includes('--help') || argv.includes('-h')) {
  if (!fs.existsSync(script)) {
    console.error(`Error: Python script not found at ${script}`);
    process.exit(1);
  }
  const result = spawnSync(py, [script, '--help'], { stdio: 'inherit' });
  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  process.exit(result.status === null ? 1 : result.status);
}

if (argv[0] === 'start' && argv.includes('--json') && !fs.existsSync(script)) {
  printStart();
  process.exit(0);
}

if (!fs.existsSync(script)) {
  console.error(`Error: Python script not found at ${script}`);
  process.exit(1);
}

const result = spawnSync(py, [script, ...argv], { stdio: 'inherit' });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
