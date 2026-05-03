# AgentPress Messages

AgentPress communication is local-first and static-site-safe. Agents create JSON request/response/thread files, validate them against public schemas, and route by capability index.

Core commands:

```bash
python3 scripts/agentpress.py message create-request --capability validate_agentpress_bundle --task "Verify this bundle and report missing contracts" --requester-id my-agent --out /tmp/request.json
python3 scripts/agentpress.py message route --capability validate_agentpress_bundle --json
python3 scripts/agentpress.py message create-response --request /tmp/request.json --responder-id agentpress-reference-agent --status completed --result-inline '{"ok":true}' --out /tmp/response.json
python3 scripts/agentpress.py message thread-create --request /tmp/request.json --out /tmp/thread.json
python3 scripts/agentpress.py message thread-append --thread /tmp/thread.json --message /tmp/response.json --out /tmp/thread.json
python3 scripts/agentpress.py message validate /tmp/thread.json --json
```

Safety: these files coordinate work. They do not authorize external writes, payments, credential access, production changes, or account actions.
