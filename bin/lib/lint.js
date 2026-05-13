'use strict';

const fs = require('node:fs');

const EXIT = require('./exit_codes');
const { resolveAgentsTxt, toPosix } = require('./paths');

const { parse, validate } = require('@agent_press/core');

function runLint(argv) {
  let jsonOut = false;
  let strict = false;
  let pathArg = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--json') jsonOut = true;
    else if (argv[i] === '--strict') strict = true;
    else if (argv[i] === '-h' || argv[i] === '--help') {
      printHelp();
      return EXIT.OK;
    } else if (!argv[i].startsWith('-')) pathArg = argv[i];
  }

  const target = resolveAgentsTxt(pathArg);

  if (!fs.existsSync(target)) {
    const msg = `agents.txt not found at ${toPosix(target)}. Run \`agentpress init\` to create one.`;
    if (jsonOut) {
      process.stdout.write(JSON.stringify({ ok: false, file_not_found: true, path: toPosix(target), message: msg }) + '\n');
    } else {
      process.stderr.write(`✗ ${msg}\n`);
    }
    return EXIT.FILE_NOT_FOUND;
  }

  const text = fs.readFileSync(target, 'utf-8');
  const data = parse(text);
  const result = validate(data);

  const errors = result.issues.filter((i) => i.severity === 'error').length;
  const warnings = result.issues.filter((i) => i.severity === 'warning').length;
  const ok = errors === 0 && (!strict || warnings === 0);

  if (jsonOut) {
    process.stdout.write(JSON.stringify({
      ok,
      path: toPosix(target),
      spec_version: data.meta.specVersion || null,
      project: data.meta.project || null,
      errors,
      warnings,
      issues: result.issues,
    }) + '\n');
  } else {
    process.stdout.write(`AgentPress lint: ${toPosix(target)} (spec v${data.meta.specVersion || '?'})\n`);
    if (errors === 0 && warnings === 0) {
      process.stdout.write(`  ✓ valid\n`);
    } else {
      for (const issue of result.issues) {
        const icon = issue.severity === 'error' ? '✗' : '⚠';
        const loc = [issue.section, issue.key].filter(Boolean).join('.');
        process.stdout.write(`  ${icon} ${issue.severity.padEnd(7)} ${loc ? `[${loc}] ` : ''}${issue.message}\n`);
      }
    }
    process.stdout.write(`  ${errors} error(s), ${warnings} warning(s)\n`);
  }

  if (errors > 0) return EXIT.ERRORS_FOUND;
  if (strict && warnings > 0) return EXIT.STRICT_OR_INTERNAL;
  return EXIT.OK;
}

function printHelp() {
  process.stdout.write(`Usage: agentpress lint [path] [options]

Validate an agents.txt against the v1.0 spec.

Arguments:
  path                Path to agents.txt or to a directory containing one.
                      Default: ./agents.txt

Options:
  --json              Emit machine-readable JSON output. Default: human.
  --strict            Treat warnings as errors (exit 2 on warnings).
  -h, --help          Show this help.

Exit codes:
  0  valid
  1  errors found
  2  strict-mode warnings escalated, or internal error
  3  agents.txt not found
`);
}

module.exports = { runLint, printHelp };
