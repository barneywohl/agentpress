#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);

function wantsJson(argv) {
  return argv.includes('--json');
}

function printStart(json = false) {
  const payload = {
    schema_version: '2026-05-05.agentpress-node-fast-start.v1',
    status: 'ok',
    purpose: 'No-Python fast path for fresh users; install Python >=3.10 for the full CLI.',
    commands: [
      { step: 1, name: 'doctor', command: 'agentpress doctor --json', why: 'Check local/remote AgentPress health and get next_steps.' },
      { step: 2, name: 'llms-init', command: 'agentpress llms-init . --json', why: 'Create minimal llms.txt + .well-known/agentpress.json when missing.' },
      { step: 3, name: 'first-run-wizard', command: 'agentpress first-run-wizard . --json', why: 'Get exact_next_command, proof command, blockers, and safety notes.' },
    ],
    safety: { external_writes: false, secrets_required: false, destructive_actions: false },
    full_cli_requires: 'Python >=3.10',
  };
  if (json) {
    console.log(JSON.stringify(payload, null, 2));
    return;
  }
  console.log('AgentPress start: run these first');
  for (const item of payload.commands) console.log(`${item.step}. ${item.command}  # ${item.why}`);
  console.log('Safety: local-only guidance; no external writes or secrets. Full CLI requires Python >=3.10.');
}

function printHelp() {
  console.log(`AgentPress — agent-readable repo surfaces\n\nStart here (concise first-user path):\n  agentpress start\n  agentpress doctor --json\n  agentpress llms-init . --json\n  agentpress first-run-wizard . --json\n\nCommon commands:\n  agentpress verify <dir> --json\n  agentpress self-test --agent-id local-agent --out /tmp/agentpress-self-test.jsonl\n  agentpress agent-onboard --agent-id local-agent --runtime codex --json\n\nRun with Python available for the full command catalog.`);
}

function printNoPythonDoctor(json = false, py = 'python3', err = '') {
  const payload = {
    schema_version: '2026-05-05.agentpress-node-fast-doctor.v1',
    status: 'fail',
    mode: 'node-fast-path',
    errors: [`Python not found or not runnable (tried '${py}'). ${err}`.trim()],
    next_steps: [
      { id: 'install_python', command: 'python3 --version', why: 'Install/verify Python >=3.10, or set PYTHON=/path/to/python3.10+' },
      { id: 'start_guidance', command: 'agentpress start --json', why: 'Show no-Python first-run guidance.' },
    ],
    recommendations: [
      { priority: 'P0', summary: 'Install Python >=3.10 for full AgentPress CLI execution.', command: 'python3 --version' },
    ],
  };
  if (json) console.log(JSON.stringify(payload, null, 2));
  else {
    console.error(payload.errors[0]);
    console.error('Next: agentpress start');
  }
}

if (args.length === 0 || args[0] === '--help' || args[0] === '-h' || args[0] === 'help') {
  printHelp();
  process.exit(0);
}

if (args[0] === 'start' || args[0] === 'help-start') {
  printStart(wantsJson(args));
  process.exit(0);
}

const py = process.env.PYTHON || 'python3';

// Require Python >= 3.10 for the full CLI. Keep doctor/help-start useful even before Python exists.
const vcheck = spawnSync(py, ['--version'], { encoding: 'utf8' });
if (vcheck.error) {
  if (args[0] === 'doctor') {
    printNoPythonDoctor(wantsJson(args), py, vcheck.error.message);
    process.exit(1);
  }
  console.error(`agentpress: Python not found (tried '${py}'). Install Python >= 3.10 or set PYTHON=/path/to/python3.10+.`);
  console.error(`Try 'agentpress start' for no-Python first-run guidance.`);
  process.exit(1);
}
const vstr = (vcheck.stdout || vcheck.stderr || '').trim(); // "Python 3.x.y"
const vm = vstr.match(/Python (\d+)\.(\d+)/);
if (!vm || parseInt(vm[1], 10) < 3 || (parseInt(vm[1], 10) === 3 && parseInt(vm[2], 10) < 10)) {
  if (args[0] === 'doctor') {
    printNoPythonDoctor(wantsJson(args), py, `Found ${vstr}; need Python >=3.10.`);
    process.exit(1);
  }
  console.error(`agentpress: Python >= 3.10 required, found: ${vstr}. Install a newer Python or set PYTHON=/path/to/python3.10+.`);
  console.error(`Try 'agentpress start' for no-Python first-run guidance.`);
  process.exit(1);
}

const script = path.resolve(__dirname, '..', 'scripts', 'agentpress.py');
const result = spawnSync(py, [script, ...args], { stdio: 'inherit' });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
