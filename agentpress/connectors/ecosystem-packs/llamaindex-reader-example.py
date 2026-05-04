import urllib.request
print(urllib.request.urlopen("https://barneywohl.github.io/agentpress/llms.txt").read().decode()[:500])
