// AgentPress Inspector — popup logic.
// Reads the cached inspection result for the active tab and renders it.

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  const obj = await chrome.storage.local.get(`tab:${tab.id}`);
  const result = obj[`tab:${tab.id}`];

  const statusSec = document.getElementById('status');
  const metaSec = document.getElementById('meta');
  const actionsSec = document.getElementById('actions');
  const emptySec = document.getElementById('empty');

  if (!result) {
    statusSec.querySelector('.status-line').textContent = 'No data yet — try refreshing the tab.';
    return;
  }

  if (!result.found) {
    statusSec.hidden = true;
    emptySec.hidden = false;
    return;
  }

  // Rendered: meta + actions
  statusSec.hidden = true;
  metaSec.hidden = false;
  actionsSec.hidden = false;

  document.getElementById('meta-project').textContent = result.data.meta.project || '—';
  document.getElementById('meta-spec').textContent = `v${result.data.meta.specVersion || '?'}`;
  document.getElementById('meta-maintainer').textContent = result.data.meta.maintainer || '—';
  document.getElementById('raw-link').href = result.agentsTxtUrl;

  const fill = (id, items) => {
    const ul = document.getElementById(id);
    ul.innerHTML = '';
    if (!items || items.length === 0) {
      const li = document.createElement('li');
      li.style.color = 'var(--fg-dim)';
      li.textContent = '(none)';
      ul.appendChild(li);
      return;
    }
    for (const item of items.slice(0, 30)) {
      const li = document.createElement('li');
      li.textContent = item;
      ul.appendChild(li);
    }
    if (items.length > 30) {
      const li = document.createElement('li');
      li.style.color = 'var(--fg-dim)';
      li.textContent = `… and ${items.length - 30} more`;
      ul.appendChild(li);
    }
  };

  fill('list-allowed', result.data.allowedActions);
  fill('list-approval', result.data.requiresHumanApproval);
  fill('list-prohibited', result.data.prohibitedActions);
}

init();
