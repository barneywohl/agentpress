'use strict';

const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const EXIT = require('./exit_codes');

let bannerShown = false;

function showBannerOnce() {
  if (bannerShown) return;
  if (process.env.AGENTPRESS_LEGACY_QUIET === '1') return;
  process.stderr.write(`\n[deprecation] You're using the legacy v0.x command surface via \`agentpress legacy ...\`.\n`);
  process.stderr.write(`              Legacy commands stay supported through v1.x and will be removed in v2.0.\n`);
  process.stderr.write(`              Set AGENTPRESS_LEGACY_QUIET=1 to silence this message.\n\n`);
  bannerShown = true;
}

function runLegacy(argv) {
  if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') {
    showBannerOnce();
    const result = spawnSync(getPython(), [getLegacyScript(), '--help'], {
      stdio: 'inherit',
      cwd: process.cwd(),
    });
    return result.status ?? EXIT.STRICT_OR_INTERNAL;
  }
  showBannerOnce();
  const result = spawnSync(getPython(), [getLegacyScript(), ...argv], {
    stdio: 'inherit',
    cwd: process.cwd(),
  });
  if (result.error && result.error.code === 'ENOENT') {
    process.stderr.write(`✗ python3 not found. Legacy commands require Python 3.10+ on PATH.\n`);
    return EXIT.STRICT_OR_INTERNAL;
  }
  return result.status ?? EXIT.STRICT_OR_INTERNAL;
}

function getPython() {
  return process.env.PYTHON || 'python3';
}

function getLegacyScript() {
  // bin/lib/legacy.js → ../../scripts/agentpress.py
  return path.resolve(__dirname, '..', '..', 'scripts', 'agentpress.py');
}

function legacyAvailable() {
  return fs.existsSync(getLegacyScript());
}

function printHelp() {
  process.stdout.write(`Usage: agentpress legacy <subcommand> [args...]

Forward a command to the legacy v0.x CLI surface. Useful while we
migrate functionality into native v1.0 verbs.

Run \`agentpress legacy --help\` for the full list of legacy subcommands.

This forwarding stays supported through the v1.x series and will be
removed in v2.0.

Environment:
  AGENTPRESS_LEGACY_QUIET=1   Silence the deprecation banner.
`);
}

module.exports = { runLegacy, legacyAvailable, printHelp };
