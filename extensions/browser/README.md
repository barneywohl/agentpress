# AgentPress Inspector — browser extension

> See `agents.txt` for any GitHub repo or website. Badge in your URL bar when a site declares an agents.txt v1.0 contract.

A daily-use extension that turns `agents.txt` adoption into something you can *see* while browsing.

## What it does

- On every tab you navigate to, looks for an `agents.txt`:
  - **GitHub repos** (`github.com/owner/repo`) → fetches `raw.githubusercontent.com/owner/repo/HEAD/agents.txt`
  - **Any other website** (`https://example.com`) → fetches `https://example.com/agents.txt`
- Sets a 📜 badge on the toolbar icon when one is found.
- Clicking the icon opens a popup showing:
  - The repo's `[meta]`: project, spec version, maintainer
  - **Allowed actions** (green)
  - **Requires-approval actions** (orange)
  - **Prohibited actions** (red)
  - Direct link to the raw `agents.txt`

## Privacy

- All inspection happens client-side. Nothing leaves your browser.
- Results cached in `chrome.storage.local` for 24 hours per URL to avoid re-fetching.
- No analytics. No accounts. No telemetry.

## Install

### Chrome / Edge / Brave / Arc
1. Download the latest `.zip` from [Releases](https://github.com/barneywohl/agentpress/releases).
2. Unzip.
3. Go to `chrome://extensions`, toggle **Developer mode**, click **Load unpacked**, pick the `extensions/browser/` folder.

(Marketplace listing for one-click install: coming with v1.0.0 final.)

### Firefox
1. Download the same `.zip`.
2. Go to `about:debugging` → **This Firefox** → **Load Temporary Add-on…** → pick `manifest.json`.

(AMO listing for permanent install: coming with v1.0.0 final.)

## Permissions

| Permission | Why |
|---|---|
| `storage` | Cache lookup results for 24h to avoid hammering servers. |
| `tabs` | Detect when you navigate to a new tab so we can inspect. |
| `host_permissions: <all_urls>` | Fetch `/agents.txt` from arbitrary hosts. |

## Development

```bash
cd extensions/browser
# Make changes to background.js / popup.* / manifest.json
# Reload the extension in chrome://extensions
```

## Building a release zip

```bash
cd extensions/browser
zip -r ../../agentpress-inspector-v1.0.0.zip . -x "node_modules/*" "*.zip"
```

Then upload to the [Releases](https://github.com/barneywohl/agentpress/releases) page.

## Links

- Spec: <https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md>
- Repo: <https://github.com/barneywohl/agentpress>
- Registry: <https://agentpress.pages.dev/registry/>

## License

MIT.
