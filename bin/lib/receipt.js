'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const EXIT = require('./exit_codes');
const { resolveAgentsTxt, writeFileAtomic, toPosix, rootOrCwd } = require('./paths');

const { parse, validate } = require('@agent_press/core');
const pkg = require('../../package.json');

function uuid12() {
  return crypto.randomBytes(6).toString('hex');
}

function runReceipt(argv) {
  let jsonOut = true;            // receipt output is always JSON; flag controls only stdout vs file behavior
  let stdoutOnly = false;
  let pathArg = null;
  let out = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--stdout-only') stdoutOnly = true;
    else if (argv[i] === '--out' || argv[i] === '-o') out = argv[++i];
    else if (argv[i] === '--json') jsonOut = true;
    else if (argv[i] === '-h' || argv[i] === '--help') {
      printHelp();
      return EXIT.OK;
    } else if (!argv[i].startsWith('-')) pathArg = argv[i];
  }

  const target = resolveAgentsTxt(pathArg);
  if (!fs.existsSync(target)) {
    process.stderr.write(`agents.txt not found at ${toPosix(target)}. Run \`agentpress init\` to create one.\n`);
    return EXIT.FILE_NOT_FOUND;
  }

  const body = fs.readFileSync(target);    // bytes for hash
  const text = body.toString('utf-8');
  const data = parse(text);
  const result = validate(data);
  const errors = result.issues.filter((i) => i.severity === 'error').length;
  const warnings = result.issues.filter((i) => i.severity === 'warning').length;

  if (errors > 0) {
    process.stderr.write(`agents.txt has ${errors} error(s). Receipt requires a valid file. Run \`agentpress lint\` to see details.\n`);
    return EXIT.ERRORS_FOUND;
  }

  const root = rootOrCwd();
  const receiptId = `rcpt_${uuid12()}`;
  const sha256 = crypto.createHash('sha256').update(body).digest('hex');
  const receipt = {
    schema_version: 'agentpress-receipt.v1',
    ts: new Date().toISOString(),
    kind: 'lint',
    agents_txt_path: toPosix(path.relative(root, target)),
    agents_txt_sha256: sha256,
    spec_version: data.meta.specVersion,
    project: data.meta.project,
    validation: { ok: errors === 0, errors, warnings },
    agentpress_version: pkg.version,
    receipt_id: receiptId,
  };

  const json = JSON.stringify(receipt, null, 2);

  if (stdoutOnly) {
    process.stdout.write(json + '\n');
    return EXIT.OK;
  }

  const outPath = out
    ? path.resolve(process.cwd(), out)
    : path.join(root, 'agentpress', 'receipts', `${receiptId}.json`);
  writeFileAtomic(outPath, json + '\n');

  if (jsonOut) {
    // Also print to stdout for consumption by CI
    process.stdout.write(json + '\n');
  }
  process.stderr.write(`✓ receipt written to ${toPosix(path.relative(root, outPath))}\n`);
  return EXIT.OK;
}

function printHelp() {
  process.stdout.write(`Usage: agentpress receipt [path] [options]

Generate a content-addressed JSON receipt proving an agents.txt was
validated. Future v1.1 will add ed25519 signing; v1.0 receipts are
unsigned but include a sha256 of the file body so the receipt can be
verified later by re-hashing.

Options:
  --stdout-only         Print receipt to stdout; do not write to disk.
  --out PATH            Write receipt to PATH (default: agentpress/receipts/<id>.json).
  --json                Also print the receipt to stdout (default when writing).
  -h, --help            Show this help.

Exit codes:
  0  receipt generated
  1  agents.txt has errors
  3  agents.txt not found
`);
}

module.exports = { runReceipt, printHelp };
