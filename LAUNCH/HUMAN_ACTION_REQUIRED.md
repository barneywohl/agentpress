# 🔐 Human action required

I built every artifact for the v1.0 launch. The remaining steps require your hands on a keyboard because they need authentication / payment / human review I can't do for you.

Items ordered by recommended sequence. Each item lists the **exact commands** + estimated time.

---

## 1. Buy `agentpress.dev` domain (15 min, $15)

Go to your registrar of choice (Namecheap, Cloudflare, Porkbun). Search for `agentpress.dev`. Buy.

If `.dev` unavailable:
- `agentpress.tools` — fine fallback
- `agentpress.so` — fine fallback
- `getagentpress.com` — slightly less clean

After buying, in **Cloudflare Pages**:
- Project: `agentpress` (already exists, serving `agentpress.pages.dev`)
- Settings → Custom domains → Add custom domain → enter `agentpress.dev`
- Add www CNAME if desired
- Cloudflare auto-provisions SSL within ~15 min

---

## 2. Review the v1.0 PR on GitHub (15 min)

Open https://github.com/barneywohl/agentpress/pull/new/v1.0

Review the changes. Edit anything that doesn't match your taste. Particular things to check:
- README pitch matches your voice
- `agents.txt` at the root reflects the contract you actually want for AgentPress itself
- Disabled CI workflows (`.disabled-in-v1`) are OK to leave or remove

When ready: **Merge the PR to main**.

---

## 3. Bump versions to 1.0.0 final (5 min)

```bash
cd /Volumes/X10/clawd/agentpress-v1-source
git checkout main
git pull

# Bump 5 versions in 5 files (one find-replace per file)
sed -i '' 's/"version": "1.0.0-rc.1"/"version": "1.0.0"/' package.json
sed -i '' 's/version = "1.0.0rc1"/version = "1.0.0"/' pyproject.toml
sed -i '' 's/"version": "1.0.0-rc.1"/"version": "1.0.0"/' packages/core/package.json
sed -i '' 's/"version": "1.0.0-rc.1"/"version": "1.0.0"/' packages/mcp-server/package.json
sed -i '' 's/version = "1.0.0rc1"/version = "1.0.0"/' python-core/pyproject.toml

git add -A
git commit -m "release: v1.0.0"
git tag v1.0.0
git push && git push --tags
```

---

## 4. Publish to npm (5 min, requires 2FA)

```bash
# Make sure you're logged in
npm whoami    # should show your npm username

# Main CLI
cd /Volumes/X10/clawd/agentpress-v1-source
npm publish --access public

# Core parser (build first)
cd packages/core
npm install --no-fund --no-audit
npx tsc -p tsconfig.json
[ -f dist/index.js ] && mv dist/index.js dist/index.mjs
[ -f dist/index.js.map ] && mv dist/index.js.map dist/index.mjs.map
npx tsc -p tsconfig.cjs.json
[ -f dist-cjs/index.js ] && cp dist-cjs/index.js dist/index.cjs
npm publish --access public

# MCP server
cd ../mcp-server
npm install --no-fund --no-audit
npm run build
npm publish --access public
```

Each publish prompts for 2FA. Have your authenticator app ready.

**Verify:**
```bash
npm view @agent_press/agentpress version
npm view @agentpress/core version
npm view @agentpress/mcp-server version
```

---

## 5. Publish to PyPI (5 min, requires API token)

```bash
# Main CLI
cd /Volumes/X10/clawd/agentpress-v1-source
python3 -m build
python3 -m twine upload dist/agentpress_static-1.0.0*

# Parser library
cd python-core
python3 -m build
python3 -m twine upload dist/agentpress_core-1.0.0*
```

Twine asks for your PyPI API token (or username/password if you've configured `.pypirc`).

**Verify:**
```bash
pip index versions agentpress-static
pip index versions agentpress-core
```

---

## 6. Publish GitHub Action to Marketplace (10 min)

1. Go to https://github.com/barneywohl/agentpress/releases/new
2. Tag: `v1.0.0`
3. Title: `AgentPress v1.0.0 — agents.txt for any repo`
4. Description: paste the **CHANGELOG.md** entry for 1.0.0
5. Check ☑ **Publish this Action to the GitHub Marketplace**
6. Pick **Primary Category**: "Utilities" → **Secondary**: "Code review"
7. Create release

The Action becomes installable via `barneywohl/agentpress/actions/setup-action@v1.0.0` (and `@v1` once you set up the `v1` tag pointing at this release).

---

## 7. Publish VS Code extension (15 min)

If you don't have an Azure DevOps publisher account:
- Go to https://marketplace.visualstudio.com/manage
- Create publisher (use `barneywohl` as ID)
- Generate a Personal Access Token (PAT) with `Marketplace > Manage` scope

Then:

```bash
cd /Volumes/X10/clawd/agentpress-v1-source/extensions/vscode
npm install -g vsce
vsce login barneywohl       # paste PAT when prompted
vsce package                # creates agents-txt-1.0.0.vsix
vsce publish                # uploads to Marketplace
```

Marketplace listing live at: https://marketplace.visualstudio.com/items?itemName=barneywohl.agents-txt

---

## 8. Submit Browser extension to Chrome Web Store (30 min, $5 one-time)

If you don't have a Chrome Web Store developer account:
- Go to https://chrome.google.com/webstore/devconsole/
- Pay $5 one-time developer registration fee

Then:
1. Create real icons (16, 32, 48, 128 px) — replace the placeholder in `extensions/browser/icons/`. Hire on Fiverr ($30) or use Figma → SVG → PNG.
2. Build the .zip:
   ```bash
   cd extensions/browser
   zip -r ../agentpress-inspector-v1.0.0.zip . -x "*.zip"
   ```
3. Upload to Chrome Web Store dev console:
   - Title: `AgentPress Inspector`
   - Summary: `See agents.txt for any GitHub repo or website`
   - Description: paste from `extensions/browser/README.md`
   - Screenshots: 5 required (use the popup on different sites)
   - Promo tile (440×280): brand asset
4. Submit for review (typically 2-7 days)

For Firefox AMO: similar flow at https://addons.mozilla.org/developers/

---

## 9. Launch day execution (~4 hours of your time)

Open `LAUNCH/LAUNCH_DAY_RUNBOOK.md` and follow the hour-by-hour playbook. All copy is pre-written in the LAUNCH/ directory.

---

## 10. File the 20 PRs (over 14 days, ~30 min each)

Open `LAUNCH/TARGET_REPOS.md` for the list and `LAUNCH/PR_TEMPLATE.md` for the body template. File one or two per day, **starting day +1 after launch** to let the launch wave amplify the maintainer's awareness.

For each repo:
```bash
gh repo fork {owner}/{repo} --clone --remote
cd {repo}
git checkout -b agents-txt-v1
# Customize the agents.txt for THIS repo (don't copy-paste — tailor)
npx @agent_press/agentpress init
git add agents.txt
git commit -m "Add agents.txt v1.0"
git push origin agents-txt-v1
gh pr create --title "Add agents.txt v1.0 — declare what AI agents may do on this repo" --body-file ~/Volumes/X10/clawd/agentpress-v1-source/LAUNCH/PR_TEMPLATE.md
```

Update `LAUNCH/PR_TRACKER.md` after each filing.

---

## What you DON'T need to do

- Set up new infrastructure (everything runs on existing Cloudflare Pages + npm + PyPI + GitHub)
- Hire anyone (the parser, action, extensions, MCP server are all single-file or single-package; maintenance is light)
- Pay for advertising (organic launch only — the lineage analogy does the work)
- Schedule a launch event (asynchronous launch via HN/PH/X is the right mode)

---

## Total time-to-launch estimate

| Step | Time |
|---|---|
| Domain purchase | 15 min |
| PR review + merge | 15 min |
| Version bumps | 5 min |
| npm publish (3 packages) | 10 min |
| PyPI publish (2 packages) | 5 min |
| GitHub Action Marketplace | 10 min |
| VS Code extension publish | 15 min |
| Browser extension submit | 30 min (+ wait for review) |
| Launch day execution | ~4 hours |
| 20 PRs filed (over 2 weeks) | ~10 hours total |

**Total to "everything live": ~6 hours of focused work, spread over ~3 weeks.**
