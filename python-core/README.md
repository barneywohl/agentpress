# agentpress-core

> Zero-dependency reference parser for [`agents.txt v1.0`](https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md). Python.

Mirror of [`@agentpress/core`](https://www.npmjs.com/package/@agentpress/core) (TypeScript). Use this from Python agent runtimes, CI scripts, and analysis tools.

## Install

```bash
pip install agentpress-core
```

## Quick start

```python
from pathlib import Path
from agentpress_core import parse, validate, is_action_allowed, check_rate_limit, fetch_and_parse

# Parse a local file
text = Path("agents.txt").read_text(encoding="utf-8")
data = parse(text)

# Validate against the spec
result = validate(data)
if not result.ok:
    for issue in result.issues:
        print(issue.severity, issue.message)

# Decide what an agent may do
decision = is_action_allowed(data, "merge_to_main")
#   "allow" | "deny" | "requires_approval" | "unknown"

# Respect rate limits
if not check_rate_limit(data, "pr", current_daily_pr_count):
    raise RuntimeError("agents.txt rate limit reached for this repo")

# Or fetch directly
remote = fetch_and_parse("https://github.com/barneywohl/agentpress/raw/main/agents.txt")
```

## API

| Function | Description |
|---|---|
| `parse(text)` | Parse a raw `agents.txt` string into a typed `AgentsTxt` object. Tolerant — never raises. |
| `validate(data)` | Returns `ValidationResult(ok, issues)`. Errors fail validation; warnings don't. |
| `is_action_allowed(data, action)` | Returns `"allow" \| "deny" \| "requires_approval" \| "unknown"`. |
| `check_rate_limit(data, kind, count)` | `kind` in `{"pr", "issue", "comment", "branch"}`. |
| `fetch_and_parse(url, timeout=10.0)` | Fetch + parse. Standard library only (urllib). |
| `load(url, timeout=10.0)` | `fetch_and_parse` + `validate` — convenience. |

## Why stdlib only

- Auditable in 30 minutes.
- Zero supply-chain risk.
- Pinnable in any Python project from 3.10 onwards.

## License

MIT.
