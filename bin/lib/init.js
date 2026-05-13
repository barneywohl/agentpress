'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const EXIT = require('./exit_codes');
const { rootOrCwd, writeFileAtomic, toPosix } = require('./paths');
const { detectAll } = require('./detect');
const { ask, askYesNo } = require('./prompts');
const { buildAgentsTxt, buildGithubWorkflow, buildBadgeSnippet } = require('./template');

const { parse, validate } = require('@agent_press/core');

function uuid12() {
  return crypto.randomBytes(6).toString('hex');
}

async function runInit(argv) {
  // Flags
  let nonInteractive = false;
  let force = false;
  let out = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--non-interactive' || argv[i] === '-y') nonInteractive = true;
    else if (argv[i] === '--force' || argv[i] === '-f') force = true;
    else if (argv[i] === '--out' || argv[i] === '-o') out = argv[++i];
    else if (argv[i] === '-h' || argv[i] === '--help') {
      printHelp();
      return EXIT.OK;
    } else if (!argv[i].startsWith('-')) {
      // positional path argument (the repo root)
      out = argv[i];
    }
  }

  const root = out ? path.resolve(process.cwd(), out) : rootOrCwd();
  const facts = detectAll(root);

  const agentsTxtPath = path.join(root, 'agents.txt');
  if (fs.existsSync(agentsTxtPath) && !force) {
    process.stderr.write(`agents.txt already exists at ${toPosix(agentsTxtPath)}\n`);
    process.stderr.write(`  Run \`agentpress doctor\` to check it, or pass --force to overwrite.\n`);
    return EXIT.ERRORS_FOUND;
  }

  // Print detection results
  process.stderr.write(`AgentPress init\n`);
  process.stderr.write(`  root: ${toPosix(root)}\n`);
  if (facts.githubOrigin) process.stderr.write(`  detected: GitHub repo ${facts.githubOrigin.owner}/${facts.githubOrigin.repo}\n`);
  process.stderr.write(`  detected: ${facts.repoType} project\n`);
  if (facts.ci) process.stderr.write(`  detected: CI = ${facts.ci}\n`);
  process.stderr.write('\n');

  // Gather answers
  let maintainer;
  let disclose;
  let allowPRs;
  let protectSensitive;
  let writeWorkflow;

  if (nonInteractive) {
    maintainer = facts.maintainerEmail || 'maintainer@example.com';
    disclose = true;
    allowPRs = true;
    protectSensitive = true;
    writeWorkflow = facts.ci === 'github_actions';
  } else {
    maintainer = await ask('Maintainer email', facts.maintainerEmail || '');
    disclose = await askYesNo('AI disclosure required for agent-authored PRs?', true);
    allowPRs = await askYesNo('Allow agents to file PRs without per-PR approval?', true);
    protectSensitive = await askYesNo('Require human approval for changes to billing/, payments/, auth/, security/?', true);
    writeWorkflow = facts.ci === 'github_actions'
      ? await askYesNo('Add a GitHub Action that lints agents.txt on every PR?', true)
      : false;
  }

  const body = buildAgentsTxt({
    project: facts.project,
    maintainer,
    contactForAgents: maintainer,
    aiDisclosureRequired: disclose,
    allowPrsWithoutApproval: allowPRs,
    protectSensitivePaths: protectSensitive,
    repoType: facts.repoType,
  });

  // Validate inline before write so we never produce invalid output
  const parsed = parse(body);
  const valResult = validate(parsed);
  if (!valResult.ok) {
    process.stderr.write(`\nInternal error: generated agents.txt did not validate.\n`);
    for (const issue of valResult.issues) {
      if (issue.severity === 'error') {
        process.stderr.write(`  - ${issue.severity}: ${issue.message}\n`);
      }
    }
    return EXIT.STRICT_OR_INTERNAL;
  }

  writeFileAtomic(agentsTxtPath, body);
  const wrote = [agentsTxtPath];

  if (writeWorkflow) {
    const wfPath = path.join(root, '.github', 'workflows', 'agentstxt.yml');
    if (!fs.existsSync(wfPath) || force) {
      writeFileAtomic(wfPath, buildGithubWorkflow());
      wrote.push(wfPath);
    }
  }

  // Write init receipt
  const receiptId = `rcpt_${uuid12()}`;
  const receiptPath = path.join(root, 'agentpress', 'receipts', `init_${receiptId}.json`);
  const sha256 = crypto.createHash('sha256').update(body).digest('hex');
  const receipt = {
    schema_version: 'agentpress-receipt.v1',
    ts: new Date().toISOString(),
    kind: 'init',
    agents_txt_path: toPosix(path.relative(root, agentsTxtPath)),
    agents_txt_sha256: sha256,
    spec_version: parsed.meta.specVersion,
    project: parsed.meta.project,
    validation: { ok: true, errors: 0, warnings: valResult.issues.filter((i) => i.severity === 'warning').length },
    agentpress_version: require('../../package.json').version,
    receipt_id: receiptId,
  };
  writeFileAtomic(receiptPath, JSON.stringify(receipt, null, 2) + '\n');
  wrote.push(receiptPath);

  // Output
  process.stderr.write('\n');
  for (const w of wrote) process.stderr.write(`  ✓ wrote ${toPosix(path.relative(root, w))}\n`);
  process.stderr.write('\n');
  process.stderr.write(`README badge snippet:\n\n`);
  process.stderr.write(`  ${buildBadgeSnippet(facts.githubOrigin)}\n`);
  process.stderr.write('\n');
  process.stderr.write(`Next: review agents.txt, commit, push. Tools that respect the standard will start respecting your contract.\n`);

  return EXIT.OK;
}

function printHelp() {
  process.stdout.write(`Usage: agentpress init [path] [options]

Drop an agents.txt at the repo root, plus a GitHub Actions workflow that
validates it on every PR, plus a README badge snippet.

Options:
  -y, --non-interactive    Use sensible defaults; no prompts.
  -f, --force              Overwrite an existing agents.txt.
  -o, --out PATH           Write into PATH instead of the current repo root.
  -h, --help               Show this help.

Example:
  agentpress init
  agentpress init --non-interactive
  agentpress init ./my-project
`);
}

module.exports = { runInit, printHelp };
