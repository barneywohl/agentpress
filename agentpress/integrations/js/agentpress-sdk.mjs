// AgentPress zero-dependency JavaScript SDK for browser, Node, Deno, and agent runtimes.
export class AgentPress {
  constructor(baseUrl = 'https://barneywohl.github.io/agentpress/') {
    this.baseUrl = baseUrl.endsWith('/') ? baseUrl : baseUrl + '/';
  }
  url(path = '') { return new URL(path, this.baseUrl).toString(); }
  async fetchJson(path) {
    const r = await fetch(this.url(path), { headers: { 'accept': 'application/json' }});
    if (!r.ok) throw new Error(`AgentPress fetch failed ${r.status}: ${path}`);
    return await r.json();
  }
  async fetchText(path) {
    const r = await fetch(this.url(path));
    if (!r.ok) throw new Error(`AgentPress fetch failed ${r.status}: ${path}`);
    return await r.text();
  }
  manifest() { return this.fetchJson('.well-known/agentpress.json'); }
  ingestion() { return this.fetchJson('.well-known/ai-ingestion.json'); }
  locales() { return this.fetchJson('locales/locale-index.json'); }
  articles() { return this.fetchJson('agentpress/articles/article-index.json'); }
  hubDirectory() { return this.fetchJson('agentpress/hub/agent-directory.json'); }
  hashManifest() { return this.fetchJson('agentpress/hash-manifest.json'); }
  llms(locale = 'en') { return locale === 'en' ? this.fetchText('llms.txt') : this.fetchText(`locales/llms.${locale}.txt`); }
  async selfTest() {
    const checks = await Promise.allSettled([
      this.manifest(), this.ingestion(), this.locales(), this.articles(), this.hubDirectory(), this.hashManifest(), this.llms()
    ]);
    return { ok: checks.every(x => x.status === 'fulfilled'), checks: checks.map((x, i) => ({ index: i, status: x.status, reason: x.reason?.message })) };
  }
}
export default AgentPress;
