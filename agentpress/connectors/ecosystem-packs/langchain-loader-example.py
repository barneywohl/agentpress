import json, urllib.request
url="https://barneywohl.github.io/agentpress/agentpress/tools/agentpress-tools.json"
print(json.load(urllib.request.urlopen(url))["status"])
