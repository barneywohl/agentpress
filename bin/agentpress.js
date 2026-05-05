#!/usr/bin/env node
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const py = process.env.PYTHON || 'python3';
const FLAG_VALUE_OPTIONS = new Set(['--base-url', '--mode', '--timeout', '--title', '--out']);
const SENSITIVE_PATH_MARKERS = [
  '.env',
  '.ssh',
  '.aws',
  '.config/gcloud',
  '.netrc',
  '.pypirc',
  '.npmrc',
  'id_rsa',
  'id_ed25519',
  'clawd_secrets',
];

function wantsJson(argv) {
  return argv.includes('--json');
}

function flagValue(argv, name, fallback = '') {
  const inline = argv.find((item) => item.startsWith(`${name}=`));
  if (inline) return inline.slice(name.length + 1) || fallback;
  const idx = argv.indexOf(name);
  if (idx === -1 || idx + 1 >= argv.length) return fallback;
  const value = argv[idx + 1];
  return value && !value.startsWith('--') ? value : fallback;
}

function shellQuote(value) {
  const s = String(value || '.');
  if (/^[A-Za-z0-9_./:-]+$/.test(s)) return s;
  return `'${s.replace(/'/g, `'\\''`)}'`;
}

function localPackageVersion() {
  const pkgPath = path.resolve(__dirname, '..', 'package.json');
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    return { npm_package: pkg.name || '@agent_press/agentpress', npm_version: pkg.version || 'unknown' };
  } catch (e) {
    return { npm_package: '@agent_press/agentpress', npm_version: 'unknown' };
  }
}

function versionChannelInfo() {
  const local = localPackageVersion();
  const isRc = String(local.npm_version || '').toLowerCase().includes('rc');
  return {
    channel: isRc ? 'release_candidate' : 'stable_or_local',
    local,
    stable_latest: {
      status: 'not_asserted_without_registry_check',
      rule: 'Do not call a release candidate the stable latest. Verify npm/PyPI live registry state before using stable labels.',
    },
    rc_lane: {
      status: isRc ? 'active' : 'not_detected',
      npm_install_hint: `npm package metadata in this checkout is ${local.npm_version}`,
    },
    safe_publish_policy: 'No npm/PyPI publish is implied by this CLI output; dry-run/pack checks are local evidence only.',
  };
}

function rankedFirstActions(root = '.') {
  const rootArg = shellQuote(root);
  return [
    {
      rank: 1,
      id: 'doctor',
      command: `agentpress doctor ${rootArg} --json`,
      targets_painpoints: ['first_run_onboarding_friction', 'secret_path_guardrails', 'stable_vs_rc_confusion'],
      why: 'Start with a bounded health check and machine-readable next_steps.',
    },
    {
      rank: 2,
      id: 'llms_init_if_missing',
      command: `agentpress llms-init ${rootArg} --json`,
      targets_painpoints: ['first_run_onboarding_friction', 'compact_task_cards_source_maps'],
      why: 'Create the minimal agent-readable entrypoints when doctor reports missing surfaces.',
    },
    {
      rank: 3,
      id: 'first_run_wizard',
      command: `agentpress first-run-wizard ${rootArg} --json`,
      targets_painpoints: ['first_run_onboarding_friction', 'python_runtime_dependency_friction', 'proof_handoff_evidence'],
      why: 'Emit the exact next command, host/provider blockers, and proof command once Python is available.',
    },
    {
      rank: 4,
      id: 'proof_capture',
      command: "agentpress proof-capture --task-id first-run --evidence-dir /tmp/agentpress-proof --commands 'agentpress doctor --json' --json",
      targets_painpoints: ['proof_handoff_evidence'],
      why: 'Turn the run into a local proof bundle instead of a prose claim.',
    },
  ];
}

function firstPositional(argv, start = 1) {
  for (let i = start; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === '--') return argv[i + 1];
    if (item.startsWith('--')) {
      if (FLAG_VALUE_OPTIONS.has(item) && i + 1 < argv.length && !argv[i + 1].startsWith('--')) i += 1;
      continue;
    }
    return item;
  }
  return undefined;
}

function isSensitivePath(targetPath) {
  const resolved = path.resolve(targetPath || '.').replace(/\\/g, '/').toLowerCase();
  const name = path.basename(resolved);
  if (name.endsWith('.key') || name.endsWith('.pem')) return true;
  return SENSITIVE_PATH_MARKERS.some((marker) => resolved.includes(marker));
}

function sensitivePathPayload(command, dir) {
  return {
    schema_version: '2026-05-05.agentpress-node-sensitive-path-guard.v1',
    status: 'fail',
    mode: 'node-fast-path',
    command,
    root: dir,
    checked: ['secret_path_guard'],
    errors: ['Refusing to read or write a secret-bearing path. Choose the public project root instead.'],
    security_guard: {
      code: 'sensitive_root_refused',
      path: dir,
      default_deny_secrets: true,
    },
    version_channel: versionChannelInfo(),
    next_steps: [
      { command: 'cd /path/to/public/repo && agentpress doctor --json', why: 'Run AgentPress from the public project root.' },
    ],
  };
}

function printPayload(payload, json, textLine) {
  if (json) console.log(JSON.stringify(payload, null, 2));
  else console.log(textLine || payload.status);
}

function printStart(json = false) {
  const payload = {
    schema_version: '2026-05-05.agentpress-node-fast-start.v2',
    status: 'ok',
    purpose: 'No-Python fast path for fresh users; install Python >=3.10 for the full CLI.',
    commands: [
      { step: 1, name: 'doctor', command: 'agentpress doctor --json', why: 'Check local/remote AgentPress health and get next_steps.' },
      { step: 2, name: 'llms-init', command: 'agentpress llms-init . --json', why: 'Create minimal llms.txt + .well-known/agentpress.json when missing.' },
      { step: 3, name: 'first-run-wizard', command: 'agentpress first-run-wizard . --json', why: 'Get exact_next_command, proof command, blockers, and safety notes.' },
    ],
    ranked_first_actions: rankedFirstActions('.'),
    version_channel: versionChannelInfo(),
    painpoint_map_command: 'agentpress painpoint-map --json',
    safety: { external_writes: false, secrets_required: false, destructive_actions: false },
    full_cli_requires: 'Python >=3.10',
  };
  if (json) {
    console.log(JSON.stringify(payload, null, 2));
    return;
  }
  console.log('AgentPress start: run these first');
  for (const item of payload.commands) console.log(`${item.step}. ${item.command}  # ${item.why}`);
  console.log(`Version channel: ${payload.version_channel.channel} (registry stable latest not asserted)`);
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
    version_channel: versionChannelInfo(),
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

function nodeDoctor(targetDir, opts = {}) {
  const json = opts.json || false;
  const requestedMode = opts.mode || 'auto';
  const dir = path.resolve(targetDir || '.');
  if (isSensitivePath(dir)) {
    printPayload(sensitivePathPayload('doctor', dir), json, 'AgentPress doctor: refused sensitive path');
    return 1;
  }

  if (requestedMode === 'online') {
    const payload = {
      schema_version: '2026-05-05.agentpress-node-fast-doctor.v2',
      status: 'fail',
      mode: 'node-fast-path',
      requested_mode: requestedMode,
      root: dir,
      errors: ['Online URL health checks require the full Python CLI; the Node fast path only performs local first-run checks.'],
      checked_urls: [],
      ranked_first_actions: rankedFirstActions(dir),
      version_channel: versionChannelInfo(),
      next_steps: [
        { command: 'python3 --version', why: 'Install or verify Python >=3.10.' },
        { command: 'agentpress doctor --json', why: 'Rerun after Python is available for full online checks.' },
      ],
      safety: { external_writes: false, secrets_required: false, destructive_actions: false },
      full_cli_requires: 'Python >=3.10',
    };
    printPayload(payload, json, 'AgentPress doctor: online mode requires Python >=3.10');
    return 1;
  }

  if (requestedMode === 'self-check') {
    const payload = {
      schema_version: '2026-05-05.agentpress-node-fast-doctor.v2',
      status: 'ok',
      mode: 'node-fast-path',
      requested_mode: requestedMode,
      root: dir,
      checks: {
        node_version: process.version,
        json_output_supported: true,
        local_file_reads: false,
      },
      errors: [],
      ranked_first_actions: rankedFirstActions(dir),
      version_channel: versionChannelInfo(),
      next_steps: [
        { command: 'agentpress doctor . --json', why: 'Check local AgentPress entrypoints.' },
        { command: 'agentpress llms-init . --json', why: 'Create minimal entrypoints if they are missing.' },
      ],
      safety: { external_writes: false, secrets_required: false, destructive_actions: false },
      full_cli_requires: 'Python >=3.10',
    };
    printPayload(payload, json, 'AgentPress doctor self-check: ok');
    return 0;
  }

  const entrypoints = [];
  const errors = [];
  const llmsTxt = path.join(dir, 'llms.txt');
  const manifestFile = path.join(dir, '.well-known', 'agentpress.json');

  if (fs.existsSync(llmsTxt)) {
    try {
      const text = fs.readFileSync(llmsTxt, 'utf8');
      entrypoints.push({ path: 'llms.txt', status: text.trim() ? 'present' : 'empty', bytes: Buffer.byteLength(text, 'utf8') });
      if (!text.trim()) errors.push('llms.txt is empty');
    } catch (e) {
      entrypoints.push({ path: 'llms.txt', status: 'error', error: e.message });
      errors.push(`llms.txt read failed: ${e.message}`);
    }
  } else {
    entrypoints.push({ path: 'llms.txt', status: 'missing' });
    errors.push('missing llms.txt');
  }

  if (fs.existsSync(manifestFile)) {
    try {
      const manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
      entrypoints.push({
        path: '.well-known/agentpress.json',
        status: 'present',
        schema_version: manifest.schema_version || manifest.schema || '',
      });
    } catch (e) {
      entrypoints.push({ path: '.well-known/agentpress.json', status: 'invalid_json', error: e.message });
      errors.push(`.well-known/agentpress.json invalid JSON: ${e.message}`);
    }
  } else {
    entrypoints.push({ path: '.well-known/agentpress.json', status: 'missing' });
    errors.push('missing .well-known/agentpress.json');
  }

  const payload = {
    schema_version: '2026-05-05.agentpress-node-fast-doctor.v2',
    status: errors.length ? 'fail' : 'ok',
    mode: 'node-fast-path',
    requested_mode: requestedMode,
    root: dir,
    entrypoints,
    errors,
    ranked_first_actions: rankedFirstActions(dir),
    version_channel: versionChannelInfo(),
    next_steps: errors.length ? [
      { command: `agentpress llms-init ${shellQuote(dir)} --json`, why: 'Create minimal llms.txt and .well-known/agentpress.json.' },
      { command: `agentpress doctor ${shellQuote(dir)} --json`, why: 'Re-check the generated first-run surface.' },
      { command: 'python3 --version', why: 'Install Python >=3.10 for the full AgentPress CLI.' },
    ] : [
      { command: `agentpress first-run-wizard ${shellQuote(dir)} --json`, why: 'Generate a fuller first-run plan once Python >=3.10 is available.' },
      { command: `agentpress external-proof-run --agent-id <agent-id> --runtime codex --out /tmp/agentpress-proof-<agent-id> --json`, why: 'Produce a local proof bundle for human-reviewed submission.' },
    ],
    safety: { external_writes: false, secrets_required: false, destructive_actions: false },
    full_cli_requires: 'Python >=3.10',
  };
  printPayload(payload, json, `AgentPress doctor: ${payload.status}`);
  return errors.length ? 1 : 0;
}

function llmsInit(targetDir, opts) {
  const json = (opts && opts.json) || false;
  const force = (opts && opts.force) || false;
  const noWrite = (opts && opts.noWrite) || false;
  const dir = path.resolve(targetDir || '.');
  const title = (opts && opts.title) || path.basename(dir) || 'AgentPress project';
  const baseUrl = ((opts && opts.baseUrl) || '').replace(/\/+$/, '');
  const created = [];
  const skipped = [];
  const wouldWrite = [];
  const errors = [];

  if (isSensitivePath(dir)) {
    printPayload(sensitivePathPayload('llms-init', dir), json, 'AgentPress llms-init: refused sensitive path');
    return 1;
  }

  if (!noWrite) {
    try {
      fs.mkdirSync(dir, { recursive: true });
    } catch (e) {
      errors.push(`target dir: ${e.message}`);
    }
  }

  try {
    const llmsTxt = path.join(dir, 'llms.txt');
    if (force || !fs.existsSync(llmsTxt)) {
      const template = [
        `# ${title}`,
        '# llms.txt - agent-readable repo surface',
        '',
        '## AgentPress quick start',
        '',
        'This repository exposes a minimal agent-readable surface. Start with:',
        '',
        '```bash',
        'agentpress doctor . --json',
        'agentpress first-run-wizard . --json',
        '```',
        '',
        '## Safe operating boundary',
        '',
        '- Read and summarize public repository files.',
        '- Do not access secrets, credentials, private data, payments, or external posting flows without explicit human approval.',
        '- Prefer machine-readable JSON outputs and attach command evidence when reporting blockers.',
        '',
        '# Generated by: agentpress llms-init (minimal Node fast-path template)',
        '',
      ].join('\n');
      if (noWrite) wouldWrite.push('llms.txt');
      else fs.writeFileSync(llmsTxt, template, 'utf8');
      created.push('llms.txt');
    } else {
      skipped.push('llms.txt');
    }
  } catch (e) {
    errors.push(`llms.txt: ${e.message}`);
  }

  try {
    const wkDir = path.join(dir, '.well-known');
    const wkFile = path.join(wkDir, 'agentpress.json');
    if (force || !fs.existsSync(wkFile)) {
      if (!noWrite && !fs.existsSync(wkDir)) fs.mkdirSync(wkDir, { recursive: true });
      const manifest = {
        schema_version: '2026-05-05.agentpress-minimal-entrypoint.v1',
        name: title,
        status: 'minimal',
        canonical_url: baseUrl,
        entrypoints: ['llms.txt', '.well-known/agentpress.json'],
        commands: {
          doctor: 'agentpress doctor . --json',
          start: 'agentpress start --json',
          first_run_wizard: 'agentpress first-run-wizard . --json',
        },
        safety: {
          external_writes: false,
          secrets_required: false,
          human_approval_required_for_mutations: true,
        },
        generated_by: 'agentpress-llms-init-node-fast-path',
        note: 'Minimal template. Run: agentpress doctor . --json for a fast local check; full CLI commands require Python >=3.10.',
      };
      if (noWrite) wouldWrite.push('.well-known/agentpress.json');
      else fs.writeFileSync(wkFile, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
      created.push('.well-known/agentpress.json');
    } else {
      skipped.push('.well-known/agentpress.json');
    }
  } catch (e) {
    errors.push(`.well-known/agentpress.json: ${e.message}`);
  }

  const status = errors.length > 0 ? 'error' : (created.length > 0 ? 'ok' : 'already_exists');
  const payload = {
    schema_version: '2026-05-05.agentpress-llms-init-node.v1',
    status,
    mode: 'node-fast-path',
    target_dir: dir,
    created,
    written: noWrite ? [] : created,
    would_write: wouldWrite,
    skipped,
    errors,
    version_channel: versionChannelInfo(),
    next_steps: [
      { command: `agentpress doctor ${shellQuote(dir)} --json`, why: 'Fast local check without Python.' },
      { command: `agentpress first-run-wizard ${shellQuote(dir)} --json`, why: 'Full first-run plan (requires Python >=3.10).' },
    ],
    note: created.length ? 'Minimal templates written. Edit llms.txt to describe your repo.' : 'Files already exist; no changes made.',
  };
  if (json) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    if (created.length) console.log('Created:', created.join(', '));
    if (skipped.length) console.log('Already exists (skipped):', skipped.join(', '));
    if (errors.length) console.error('Errors:', errors.join('; '));
    console.log('Next: agentpress validate (requires Python >=3.10) or agentpress doctor --json');
  }
  return status === 'error' ? 1 : 0;
}

if (args.length === 0 || args[0] === '--help' || args[0] === '-h' || args[0] === 'help') {
  printHelp();
  process.exit(0);
}

if ((args[0] === 'llms-init' || args[0] === 'doctor') && (args.includes('--help') || args.includes('-h'))) {
  printHelp();
  process.exit(0);
}

if (args[0] === 'start' || args[0] === 'help-start') {
  printStart(wantsJson(args));
  process.exit(0);
}

if (args[0] === 'llms-init') {
  const targetDir = firstPositional(args, 1);
  const exitCode = llmsInit(targetDir, {
    json: wantsJson(args),
    force: args.includes('--force'),
    noWrite: args.includes('--no-write'),
    title: flagValue(args, '--title', ''),
    baseUrl: flagValue(args, '--base-url', ''),
  });
  process.exit(exitCode);
}

// Require Python >= 3.10 for the full CLI. Keep doctor/help-start useful even before Python exists.
const vcheck = spawnSync(py, ['--version'], { encoding: 'utf8' });
if (vcheck.error) {
  if (args[0] === 'doctor') {
    if (wantsJson(args)) {
      const exitCode = nodeDoctor(firstPositional(args, 1), { json: true, mode: flagValue(args, '--mode', 'auto') });
      process.exit(exitCode);
    }
    printNoPythonDoctor(false, py, vcheck.error.message);
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
    if (wantsJson(args)) {
      const exitCode = nodeDoctor(firstPositional(args, 1), { json: true, mode: flagValue(args, '--mode', 'auto') });
      process.exit(exitCode);
    }
    printNoPythonDoctor(false, py, `Found ${vstr}; need Python >=3.10.`);
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
