"""Zero-dependency AgentPress SDK for Python agents."""
import json
from urllib.parse import urljoin
from urllib.request import Request, urlopen

class AgentPress:
    def __init__(self, base_url="https://barneywohl.github.io/agentpress/", timeout=20):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
    def url(self, path=""):
        return urljoin(self.base_url, path)
    def fetch_text(self, path):
        req = Request(self.url(path), headers={"Accept":"text/plain, application/json"})
        with urlopen(req, timeout=self.timeout) as r:
            return r.read().decode("utf-8")
    def fetch_json(self, path):
        return json.loads(self.fetch_text(path))
    def manifest(self): return self.fetch_json(".well-known/agentpress.json")
    def tools(self): return self.fetch_json("agentpress/tools/agentpress-tools.json")
    def routes(self): return self.fetch_json("agentpress/routes/agent-routes.json")
    def marketplace(self): return self.fetch_json("agentpress/marketplace/marketplace-index.json")
    def proof_scoreboard(self): return self.fetch_json("agentpress/external-proofs/proof-scoreboard.json")
    def browser_smoke(self): return self.fetch_json("agentpress/evidence/browser-smoke.json")
    def self_test(self):
        checks=[]
        for name, path in [("manifest",".well-known/agentpress.json"),("tools","agentpress/tools/agentpress-tools.json"),("routes","agentpress/routes/agent-routes.json"),("marketplace","agentpress/marketplace/marketplace-index.json"),("llms","llms.txt")]:
            try:
                body=self.fetch_text(path); checks.append({"name":name,"path":path,"ok":bool(body),"bytes":len(body)})
            except Exception as e:
                checks.append({"name":name,"path":path,"ok":False,"error":str(e)})
        return {"ok": all(c.get("ok") for c in checks), "checks": checks}
