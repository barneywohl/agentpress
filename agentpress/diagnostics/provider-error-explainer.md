# Provider error remediation pack

## rate_limit_or_quota
Why: Provider throttled or quota is exhausted.

Commands:
- `sleep 60 && retry the previous command`
- `python3 scripts/agentpress.py budget-check --tier small --json`
## tool_schema_or_vocabulary
Why: Provider/host rejected a tool call or schema.

Commands:
- `python3 scripts/agentpress.py tool-vocabulary-compatibility-check --json`
- `python3 scripts/agentpress.py tool-schema-serialization-check --json`
- `python3 scripts/agentpress.py tool-contract-check --manifest <tools.json> --sample-result <tool-result.json> --json`
