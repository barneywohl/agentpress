# AgentPress Consumer Demo

Smallest proof loop: an external agent/client fetches AgentPress machine entrypoints and decides what to do next.

```bash
python3 agentpress/demos/consumer/consumer_demo.py
agentpress lint . --json
```

Acceptance evidence: the script fetches `llms.txt`, `.well-known/agentpress.json`, and `.well-known/ai-ingestion.json` from `https://barneywohl.github.io/agentpress/`.
