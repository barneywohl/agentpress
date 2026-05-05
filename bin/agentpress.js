#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');
const py = process.env.PYTHON || 'python3';

// Require Python >= 3.10 (scripts use match statements and tomllib)
const vcheck = spawnSync(py, ['--version'], { encoding: 'utf8' });
if (vcheck.error) {
  console.error(`agentpress: Python not found (tried '${py}'). The npm package is currently a Node shim over the Python CLI; install Python >= 3.10 or set PYTHON=/path/to/python3.10+.`);
  process.exit(1);
}
const vstr = (vcheck.stdout || vcheck.stderr || '').trim(); // "Python 3.x.y"
const vm = vstr.match(/Python (\d+)\.(\d+)/);
if (!vm || parseInt(vm[1], 10) < 3 || (parseInt(vm[1], 10) === 3 && parseInt(vm[2], 10) < 10)) {
  console.error(`agentpress: Python >= 3.10 required, found: ${vstr}. Install a newer Python or set PYTHON=/path/to/python3.10+.`);
  process.exit(1);
}

const script = path.resolve(__dirname, '..', 'scripts', 'agentpress.py');
const result = spawnSync(py, [script, ...process.argv.slice(2)], { stdio: 'inherit' });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
