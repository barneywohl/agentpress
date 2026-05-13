'use strict';

const fs = require('node:fs');
const path = require('node:path');

/**
 * Resolve the agents.txt path from a user-supplied argument.
 * Rules:
 *   - if arg is undefined → CWD/agents.txt
 *   - if arg points to a directory → <arg>/agents.txt
 *   - else → arg as-is (treated as a file)
 * Always returns an absolute path.
 */
function resolveAgentsTxt(arg) {
  const cwd = process.cwd();
  if (!arg) return path.resolve(cwd, 'agents.txt');
  const candidate = path.resolve(cwd, arg);
  try {
    const st = fs.statSync(candidate);
    if (st.isDirectory()) return path.join(candidate, 'agents.txt');
  } catch (_) {
    // path may not exist — fall through to treat as file
  }
  return candidate;
}

/** Find the nearest ancestor directory containing a `.git` entry. Returns null if none. */
function findRepoRoot(start) {
  let dir = path.resolve(start || process.cwd());
  const root = path.parse(dir).root;
  while (dir !== root) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    dir = path.dirname(dir);
  }
  return null;
}

/** Best-effort root: repo root via .git, falling back to CWD. */
function rootOrCwd(start) {
  return findRepoRoot(start) || path.resolve(start || process.cwd());
}

/** Atomic-write: write to a temp file in the same dir then rename. Cross-platform safe. */
function writeFileAtomic(target, content, opts) {
  const dir = path.dirname(target);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.${path.basename(target)}.tmp-${process.pid}-${Date.now()}`);
  fs.writeFileSync(tmp, content, opts || { encoding: 'utf-8' });
  fs.renameSync(tmp, target);
}

/** Normalise a path for cross-platform JSON output: always forward slashes. */
function toPosix(p) {
  return p.split(path.sep).join('/');
}

module.exports = {
  resolveAgentsTxt,
  findRepoRoot,
  rootOrCwd,
  writeFileAtomic,
  toPosix,
};
