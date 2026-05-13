// AgentPress Inspector — background service worker.
//
// On every tab navigation, look for an agents.txt at:
//   - GitHub repo pages: https://raw.githubusercontent.com/{owner}/{repo}/HEAD/agents.txt
//   - Other URLs:        https://{hostname}/agents.txt
//
// Cache results in chrome.storage for 24h to avoid hammering servers.
// Set the toolbar badge text + tooltip based on result.

const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

const SUPPORTED_VERSIONS = new Set(["1.0"]);
const TRUE = new Set(["true", "yes", "1", "on"]);
const FALSE = new Set(["false", "no", "0", "off"]);

function asBool(v) {
  if (v == null) return undefined;
  const s = String(v).trim().toLowerCase();
  if (TRUE.has(s)) return true;
  if (FALSE.has(s)) return false;
  return undefined;
}

function tokenize(text) {
  const sections = [];
  let current = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("[") && line.endsWith("]")) {
      current = { name: line.slice(1, -1).trim().toLowerCase(), kv: [], bare: [] };
      sections.push(current);
      continue;
    }
    if (!current) continue;
    const eq = line.indexOf("=");
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
  const m = kv("meta");
  return {
    meta: {
      specVersion: m.spec_version || "",
      project: m.project,
      maintainer: m.maintainer,
      aiDisclosureRequired: asBool(m.ai_disclosure_required),
    },
    allowedActions: bare("allowed_actions"),
    prohibitedActions: bare("prohibited_actions"),
    requiresHumanApproval: bare("requires_human_approval"),
    entryPoints: kv("entry_points"),
  };
}

function candidateUrls(tabUrl) {
  try {
    const u = new URL(tabUrl);
    if (!/^https?:$/.test(u.protocol)) return [];
    if (u.hostname === "github.com") {
      const m = u.pathname.match(/^\/([^/]+)\/([^/]+)/);
      if (m) {
        return [
          `https://raw.githubusercontent.com/${m[1]}/${m[2]}/HEAD/agents.txt`,
        ];
      }
      return [];
    }
    return [`${u.protocol}//${u.hostname}/agents.txt`];
  } catch {
    return [];
  }
}

async function loadCached(key) {
  const obj = await chrome.storage.local.get(key);
  const v = obj[key];
  if (!v) return null;
  if (Date.now() - v.fetchedAt > CACHE_TTL_MS) return null;
  return v;
}
async function saveCached(key, value) {
  await chrome.storage.local.set({ [key]: { ...value, fetchedAt: Date.now() } });
}

async function tryFetch(url) {
  try {
    const res = await fetch(url, { redirect: "follow" });
    if (!res.ok) return null;
    const text = await res.text();
    if (text.length > 32000) return null; // sanity cap
    if (!/\[meta\]/i.test(text) || !/spec_version/i.test(text)) return null;
    return text;
  } catch {
    return null;
  }
}

async function inspectTab(tabId, tabUrl) {
  const urls = candidateUrls(tabUrl);
  if (urls.length === 0) {
    setBadge(tabId, "", "AgentPress: no inspection for this URL");
    return;
  }
  const cacheKey = `inspect:${urls[0]}`;
  let result = await loadCached(cacheKey);
  if (!result) {
    let text = null;
    let foundUrl = null;
    for (const url of urls) {
      text = await tryFetch(url);
      if (text) { foundUrl = url; break; }
    }
    if (!text) {
      result = { found: false, fetchedAt: Date.now(), tabUrl };
    } else {
      const data = parse(text);
      result = { found: true, agentsTxtUrl: foundUrl, data, fetchedAt: Date.now(), tabUrl };
    }
    await saveCached(cacheKey, result);
  }

  if (result.found) {
    const v = result.data?.meta?.specVersion || "?";
    setBadge(tabId, "📜", `AgentPress: agents.txt v${v} declared`);
  } else {
    setBadge(tabId, "", "AgentPress: no agents.txt found");
  }

  // Stash the latest result for the popup
  await chrome.storage.local.set({ [`tab:${tabId}`]: result });
}

function setBadge(tabId, text, title) {
  try {
    chrome.action.setBadgeText({ tabId, text });
    chrome.action.setBadgeBackgroundColor({ tabId, color: text ? "#2563eb" : "#9ca3af" });
    chrome.action.setTitle({ tabId, title });
  } catch {}
}

chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.status === "complete" && tab.url) inspectTab(tabId, tab.url);
});
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId);
  if (tab?.url) inspectTab(tabId, tab.url);
});
