#!/usr/bin/env node
'use strict';

const EXIT = require('./lib/exit_codes');
const pkg = require('../package.json');

const VERBS = {
  init:    require('./lib/init'),
  lint:    require('./lib/lint'),
  doctor:  require('./lib/doctor'),
  receipt: require('./lib/receipt'),
  legacy:  require('./lib/legacy'),
};

function topHelp() {
  process.stdout.write(`AgentPress v${pkg.version} — agents.txt for any repo

Usage: agentpress <command> [options]

Commands:
  init        Drop an agents.txt at your repo root in under a minute.
  lint        Validate an agents.txt against the v1.0 spec.
  doctor      Run a health check on your repo's v1.0 surface.
  receipt     Generate a content-addressed proof receipt.
  legacy      Forward to the v0.x command surface (deprecation banner).

Options:
  -h, --help          Show this help.
  -v, --version       Print version (${pkg.version}).

Docs: https://github.com/barneywohl/agentpress
Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
`);
}

async function main() {
  const argv = process.argv.slice(2);

  if (argv.length === 0 || argv[0] === '-h' || argv[0] === '--help') {
    topHelp();
    return EXIT.OK;
  }
  if (argv[0] === '-v' || argv[0] === '--version') {
    process.stdout.write(`${pkg.version}\n`);
    return EXIT.OK;
  }

  const cmd = argv[0];
  const rest = argv.slice(1);

  if (!VERBS[cmd]) {
    process.stderr.write(`Unknown command '${cmd}'. See \`agentpress --help\`.\n`);
    return EXIT.ERRORS_FOUND;
  }

  const fn = cmd === 'init' ? VERBS[cmd].runInit
           : cmd === 'lint' ? VERBS[cmd].runLint
           : cmd === 'doctor' ? VERBS[cmd].runDoctor
           : cmd === 'receipt' ? VERBS[cmd].runReceipt
           : cmd === 'legacy' ? VERBS[cmd].runLegacy
           : null;

  return await fn(rest);
}

main()
  .then((code) => process.exit(code ?? EXIT.OK))
  .catch((err) => {
    process.stderr.write(`Internal error: ${err && err.message ? err.message : err}\n`);
    if (process.env.AGENTPRESS_DEBUG === '1') {
      process.stderr.write((err && err.stack ? err.stack : String(err)) + '\n');
    } else {
      process.stderr.write(`(set AGENTPRESS_DEBUG=1 for stack trace)\n`);
    }
    process.exit(EXIT.STRICT_OR_INTERNAL);
  });
