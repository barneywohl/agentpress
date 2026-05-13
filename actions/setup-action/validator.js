#!/usr/bin/env node
/**
 * agentpress/setup-action validator (v1.0)
 *
 * Self-contained Node script that validates an agents.txt file against
 * the v1.0 spec. Bundled inline so the action has zero external deps.
 *
 * Mirrors @agent_press/core; intentionally compact for audit.
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const SPEC_VERSION = '1.0';
const SUPPORTED = new Set(['1.0']);
const TRUE = new Set(['true', 'yes', '1', 'on']);
const FALSE = new Set(['false', 'no', '0', 'off']);

function asBool(v) {
  if (v == null) return undefined;
  const s = String(v).trim().toLowerCase();
  if (TRUE.has(s)) return true;
  if (FALSE.has(s)) return false;
  return undefined;
}
function asInt(v) {
  if (v == null) return undefined;
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : undefined;
}
function splitList(v) {
  return String(v).split(',').map((s) => s.trim()).filter(Boolean);
}

function tokenize(text) {
  const sections = [];
  let current = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    if (line.startsWith('[') && line.endsWith(']')) {
      current = { name: line.slice(1, -1).trim().toLowerCase(), kv: [], bare: [] };
      sections.push(current);
      continue;
    }
    if (!current) continue;
    const eq = line.indexOf('=');
    if (eq === -1) current.bare.push(line);
    else current.kv.push([line.slice(0, eq).trim().toLowerCase(), line.slice(eq + 1).trim()]);
  }
  return sections;
}

function parse(text) {
  const sections = tokenize(text);
  const by = new Map(sections.map((s) => [s.name, s]));
  const kv = (n) => Object.fromEntries((by.get(n) || { kv: [] }).kv);
  const bare = (n) => Array.from((by.get(n) || { bare: [] }).bare);

  const m = kv('meta');
  const meta = {
    specVersion: m.spec_version || '',
    project: m.project,
    maintainer: m.maintainer,
    contactForAgents: m.contact_for_agents,
    lastUpdated: m.last_updated,
    license: m.license,
    aiDisclosureRequired: asBool(m.ai_disclosure_required),
  };

  const allowed = bare('allowed_actions');
  const prohibited = bare('prohibited_actions');

  const rha = by.get('requires_human_approval');
  const requiresApproval = {};
  if (rha) {
    for (const item of rha.bare) requiresApproval[item] = true;
    for (const [k, v] of rha.kv) {
      const list = splitList(v);
      requiresApproval[k] = list.length ? list : true;
    }
  }

  const entryPoints = kv('entry_points');
  const d = kv('disclosure');
  const disclosure = {
    prLabel: d.pr_label,
    commitTrailer: d.commit_trailer,
    requireAttributionInPrBody: asBool(d.require_attribution_in_pr_body),
  };

  return { meta, allowedActions: allowed, prohibitedActions: prohibited, requiresHumanApproval: requiresApproval, entryPoints, disclosure };
}

function validate(data) {
  const issues = [];
  if (!data.meta.specVersion) issues.push({ severity: 'error', section: 'meta', key: 'spec_version', message: 'spec_version is required' });
  else if (!SUPPORTED.has(data.meta.specVersion)) issues.push({ severity: 'warning', section: 'meta', key: 'spec_version', message: `unknown spec_version "${data.meta.specVersion}"; this validator supports ${[...SUPPORTED].join(', ')}` });
  if (!data.meta.project) issues.push({ severity: 'error', section: 'meta', key: 'project', message: 'project name is required' });
  if (!data.meta.maintainer) issues.push({ severity: 'error', section: 'meta', key: 'maintainer', message: 'maintainer is required' });
  if (data.allowedActions.length === 0) issues.push({ severity: 'warning', section: 'allowed_actions', message: 'allowed_actions is empty; agents will treat all actions as unknown' });
  if (data.prohibitedActions.length === 0) issues.push({ severity: 'warning', section: 'prohibited_actions', message: 'prohibited_actions is empty; consider explicitly forbidding at least secret exfiltration and 2FA bypass' });
  if (Object.keys(data.entryPoints).length === 0) issues.push({ severity: 'warning', section: 'entry_points', message: 'entry_points is empty; agents will not know where to start' });
  if (!data.disclosure.prLabel && !data.disclosure.commitTrailer) issues.push({ severity: 'warning', section: 'disclosure', message: 'neither pr_label nor commit_trailer set; agent contributions cannot be identified' });
  return { ok: issues.every((i) => i.severity !== 'error'), issues };
}

function setOutput(name, value) {
  const out = process.env.GITHUB_OUTPUT;
  if (out) {
    fs.appendFileSync(out, `${name}=${value}\n`);
  }
}

function setSummary(md) {
  const path = process.env.GITHUB_STEP_SUMMARY;
  if (path) fs.appendFileSync(path, md);
}

function main() {
  const file = process.argv[2] || process.env.AGENTSTXT_FILE || 'agents.txt';
  const failOnWarnings = (process.env.AGENTSTXT_FAIL_ON_WARNINGS || 'false').toLowerCase() === 'true';
  const wantJson = (process.env.AGENTSTXT_JSON || 'false').toLowerCase() === 'true';

  const filePath = path.resolve(process.cwd(), file);
  if (!fs.existsSync(filePath)) {
    console.error(`✗ agents.txt not found at ${file}`);
    console.error(`  → run \`npx @agent_press/agentpress init\` to create one.`);
    setOutput('ok', 'false');
    setOutput('errors', '1');
    setOutput('warnings', '0');
    setOutput('spec_version', '');
    setSummary(`### ❌ AgentPress\n\n\`agents.txt\` not found at \`${file}\`.\n\nRun \`npx @agent_press/agentpress init\` to create one.\n`);
    process.exit(1);
  }

  const text = fs.readFileSync(filePath, 'utf-8');
  const data = parse(text);
  const result = validate(data);

  const errCount = result.issues.filter((i) => i.severity === 'error').length;
  const warnCount = result.issues.filter((i) => i.severity === 'warning').length;

  // Human-readable summary
  console.log(`AgentPress validating ${file} (spec v${data.meta.specVersion || 'unknown'})`);
  if (errCount === 0 && warnCount === 0) console.log('  ✓ valid');
  for (const issue of result.issues) {
    const icon = issue.severity === 'error' ? '✗' : '⚠';
    const loc = [issue.section, issue.key].filter(Boolean).join('.');
    console.log(`  ${icon} ${issue.severity.padEnd(7)} ${loc ? `[${loc}] ` : ''}${issue.message}`);
  }
  console.log(`Summary: ${errCount} error(s), ${warnCount} warning(s)`);

  if (wantJson) console.log(JSON.stringify({ ok: result.ok, issues: result.issues, meta: data.meta }, null, 2));

  // GH Actions outputs + step summary
  setOutput('ok', String(result.ok));
  setOutput('errors', String(errCount));
  setOutput('warnings', String(warnCount));
  setOutput('spec_version', data.meta.specVersion || '');

  let md = `### ${result.ok ? '✅' : '❌'} AgentPress — \`${file}\` (spec v${data.meta.specVersion || 'unknown'})\n\n`;
  if (errCount + warnCount === 0) {
    md += `\`agents.txt\` is valid.\n`;
  } else {
    md += `**${errCount} error(s), ${warnCount} warning(s)**\n\n| Severity | Section | Key | Message |\n|---|---|---|---|\n`;
    for (const i of result.issues) {
      md += `| ${i.severity} | ${i.section || ''} | ${i.key || ''} | ${i.message.replace(/\|/g, '\\|')} |\n`;
    }
  }
  md += `\nLearn more: <https://github.com/barneywohl/agentpress>\n`;
  setSummary(md);

  if (errCount > 0) process.exit(1);
  if (failOnWarnings && warnCount > 0) process.exit(2);
  process.exit(0);
}

main();
