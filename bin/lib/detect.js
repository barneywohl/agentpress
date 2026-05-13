'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execSync } = require('node:child_process');

/** Detect the project type. Pure file-existence probes; no shell calls except git config. */
function detectRepoType(root) {
  const hits = [];
  if (fs.existsSync(path.join(root, 'package.json'))) hits.push('node');
  if (fs.existsSync(path.join(root, 'pyproject.toml')) || fs.existsSync(path.join(root, 'setup.py'))) hits.push('python');
  if (fs.existsSync(path.join(root, 'go.mod'))) hits.push('go');
  if (fs.existsSync(path.join(root, 'Cargo.toml'))) hits.push('rust');
  if (fs.existsSync(path.join(root, 'Gemfile'))) hits.push('ruby');
  if (fs.existsSync(path.join(root, 'composer.json'))) hits.push('php');
  if (hits.length === 0) return 'generic';
  if (hits.length === 1) return hits[0];
  return 'monorepo:' + hits.join('+');
}

function detectCI(root) {
  if (fs.existsSync(path.join(root, '.github', 'workflows'))) return 'github_actions';
  if (fs.existsSync(path.join(root, '.gitlab-ci.yml'))) return 'gitlab';
  if (fs.existsSync(path.join(root, '.circleci', 'config.yml'))) return 'circleci';
  if (fs.existsSync(path.join(root, 'azure-pipelines.yml'))) return 'azure';
  return null;
}

function detectGitHubOrigin(root) {
  try {
    const cfg = fs.readFileSync(path.join(root, '.git', 'config'), 'utf-8');
    // Match a github.com origin in any [remote "*"] block; tolerate ssh + https variants
    const m = cfg.match(/url\s*=\s*(?:https?:\/\/github\.com\/|git@github\.com:)([^/\s]+)\/([^.\s]+?)(?:\.git)?\s*$/m);
    if (m) return { owner: m[1], repo: m[2] };
  } catch (_) {}
  return null;
}

function safeReadJSON(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch (_) { return null; }
}

function detectMaintainerEmail(root) {
  // package.json author
  const pkg = safeReadJSON(path.join(root, 'package.json'));
  if (pkg && pkg.author) {
    if (typeof pkg.author === 'string') {
      const m = pkg.author.match(/<([^>]+)>/);
      if (m) return m[1];
      if (pkg.author.includes('@')) return pkg.author.trim();
    } else if (pkg.author.email) return pkg.author.email;
  }
  // pyproject.toml authors — simple text extraction
  try {
    const py = fs.readFileSync(path.join(root, 'pyproject.toml'), 'utf-8');
    const m = py.match(/email\s*=\s*"([^"]+)"/);
    if (m) return m[1];
  } catch (_) {}
  // git config user.email
  try {
    const email = execSync('git config user.email', { cwd: root, encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (email) return email;
  } catch (_) {}
  return null;
}

function detectProjectName(root) {
  const pkg = safeReadJSON(path.join(root, 'package.json'));
  if (pkg && pkg.name) return pkg.name;
  try {
    const py = fs.readFileSync(path.join(root, 'pyproject.toml'), 'utf-8');
    const m = py.match(/^\s*name\s*=\s*"([^"]+)"/m);
    if (m) return m[1];
  } catch (_) {}
  const origin = detectGitHubOrigin(root);
  if (origin) return origin.repo;
  return path.basename(root);
}

function detectAll(root) {
  return {
    root,
    project: detectProjectName(root),
    repoType: detectRepoType(root),
    ci: detectCI(root),
    githubOrigin: detectGitHubOrigin(root),
    maintainerEmail: detectMaintainerEmail(root),
  };
}

module.exports = {
  detectRepoType,
  detectCI,
  detectGitHubOrigin,
  detectMaintainerEmail,
  detectProjectName,
  detectAll,
};
