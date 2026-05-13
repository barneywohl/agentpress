'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execSync } = require('node:child_process');

const EXIT = require('./exit_codes');
const { resolveAgentsTxt, rootOrCwd, toPosix } = require('./paths');

const { parse, validate } = require('@agent_press/core');
const pkg = require('../../package.json');

function checkNodeVersion() {
  const ver = process.versions.node;
  const major = parseInt(ver.split('.')[0], 10);
  return {
    name: 'Node.js >= 18',
    status: major >= 18 ? 'pass' : 'fail',
    detail: `node ${ver}`,
  };
}

function checkPythonAvailable() {
  try {
    const out = execSync('python3 --version', { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    return { name: 'python3 available (optional, for legacy commands)', status: 'pass', detail: out };
  } catch (_) {
    return { name: 'python3 available (optional, for legacy commands)', status: 'warn', detail: 'not found' };
  }
}

function checkCoreParserLoadable() {
  try {
    const v = require('@agent_press/core');
    return { name: '@agent_press/core parser loadable', status: 'pass', detail: `spec v${v.SPEC_VERSION}` };
  } catch (e) {
    return { name: '@agent_press/core parser loadable', status: 'fail', detail: e.message };
  }
}

function checkAgentsTxtExists(target) {
  if (fs.existsSync(target)) return { name: `agents.txt exists`, status: 'pass', detail: toPosix(target) };
  return { name: `agents.txt exists`, status: 'fail', detail: `missing at ${toPosix(target)} — run \`agentpress init\`` };
}

function checkAgentsTxtParses(target) {
  if (!fs.existsSync(target)) return { name: 'agents.txt parses', status: 'skip', detail: 'no file' };
  try {
    parse(fs.readFileSync(target, 'utf-8'));
    return { name: 'agents.txt parses', status: 'pass' };
  } catch (e) {
    return { name: 'agents.txt parses', status: 'fail', detail: e.message };
  }
}

function checkAgentsTxtValidates(target) {
  if (!fs.existsSync(target)) return { name: 'agents.txt validates', status: 'skip', detail: 'no file' };
  try {
    const data = parse(fs.readFileSync(target, 'utf-8'));
    const r = validate(data);
    const errs = r.issues.filter((i) => i.severity === 'error').length;
    const warns = r.issues.filter((i) => i.severity === 'warning').length;
    if (errs > 0) return { name: 'agents.txt validates', status: 'fail', detail: `${errs} error(s)` };
    if (warns > 0) return { name: 'agents.txt validates', status: 'warn', detail: `${warns} warning(s)` };
    return { name: 'agents.txt validates', status: 'pass' };
  } catch (e) {
    return { name: 'agents.txt validates', status: 'fail', detail: e.message };
  }
}

function checkGithubWorkflowPresent(root) {
  const wfPath = path.join(root, '.github', 'workflows', 'agentstxt.yml');
  const workflowsDir = path.join(root, '.github', 'workflows');
  if (fs.existsSync(wfPath)) return { name: '.github/workflows/agentstxt.yml present', status: 'pass' };
  if (fs.existsSync(workflowsDir)) return { name: '.github/workflows/agentstxt.yml present', status: 'warn', detail: 'GitHub Actions configured but agents.txt workflow missing' };
  return { name: '.github/workflows/agentstxt.yml present', status: 'skip', detail: 'no .github/workflows dir' };
}

function checkReadmeBadge(root) {
  const readmePath = path.join(root, 'README.md');
  if (!fs.existsSync(readmePath)) return { name: 'README badge present', status: 'skip', detail: 'no README.md' };
  const content = fs.readFileSync(readmePath, 'utf-8');
  if (/agents\.txt-v1\.0/.test(content) || /img\.shields\.io.*agents\.txt/.test(content)) {
    return { name: 'README badge present', status: 'pass' };
  }
  return { name: 'README badge present', status: 'warn', detail: 'no agents.txt badge detected' };
}

function checkOnPath() {
  try {
    const which = execSync(process.platform === 'win32' ? 'where agentpress' : 'command -v agentpress', { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    return { name: 'agentpress on PATH', status: 'pass', detail: which.split(/\r?\n/)[0] };
  } catch (_) {
    return { name: 'agentpress on PATH', status: 'warn', detail: 'not found (you may be running via npx)' };
  }
}

function runDoctor(argv) {
  let jsonOut = false;
  let pathArg = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--json') jsonOut = true;
    else if (argv[i] === '-h' || argv[i] === '--help') {
      printHelp();
      return EXIT.OK;
    } else if (!argv[i].startsWith('-')) pathArg = argv[i];
  }

  const root = pathArg ? path.resolve(process.cwd(), pathArg) : rootOrCwd();
  const target = resolveAgentsTxt(pathArg);

  const checks = [
    checkNodeVersion(),
    checkPythonAvailable(),
    checkCoreParserLoadable(),
    checkAgentsTxtExists(target),
    checkAgentsTxtParses(target),
    checkAgentsTxtValidates(target),
    checkGithubWorkflowPresent(root),
    checkReadmeBadge(root),
    checkOnPath(),
  ];

  const counts = { pass: 0, warn: 0, fail: 0, skip: 0 };
  for (const c of checks) counts[c.status] = (counts[c.status] || 0) + 1;
  const ok = counts.fail === 0;

  if (jsonOut) {
    process.stdout.write(JSON.stringify({
      ok,
      version: pkg.version,
      root: toPosix(root),
      checks,
      summary: counts,
    }) + '\n');
  } else {
    process.stdout.write(`AgentPress doctor (v${pkg.version})\n`);
    process.stdout.write(`  root: ${toPosix(root)}\n`);
    process.stdout.write('\n');
    for (const c of checks) {
      const icon = c.status === 'pass' ? '✓' : c.status === 'warn' ? '⚠' : c.status === 'fail' ? '✗' : '·';
      const detail = c.detail ? `  (${c.detail})` : '';
      process.stdout.write(`  ${icon} ${c.name}${detail}\n`);
    }
    process.stdout.write('\n');
    process.stdout.write(`Summary: ${counts.pass} OK, ${counts.warn} warning(s), ${counts.fail} error(s)${counts.skip ? `, ${counts.skip} skipped` : ''}.\n`);
    process.stdout.write(ok ? 'System healthy.\n' : 'See errors above.\n');
  }

  return ok ? EXIT.OK : EXIT.ERRORS_FOUND;
}

function printHelp() {
  process.stdout.write(`Usage: agentpress doctor [path] [options]

Run a comprehensive health check on the v1.0 surface for a repo.

Options:
  --json        Emit JSON output instead of the human-readable checklist.
  -h, --help    Show this help.

Exit codes:
  0  all checks pass (warnings allowed)
  1  one or more errors
`);
}

module.exports = { runDoctor, printHelp };
