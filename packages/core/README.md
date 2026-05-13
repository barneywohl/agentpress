# @agent_press/core

> Zero-dependency reference parser for [`agents.txt v1.0`](https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md).

The TypeScript parser used by every `@agent_press/*` package and recommended for any agent runtime that needs to read `agents.txt` files.

## Install

```bash
npm install @agent_press/core
```

## Quick start

```ts
import { parse, validate, isActionAllowed, checkRateLimit, fetchAndParse } from "@agent_press/core";

// Parse a local file
const text = await Deno.readTextFile("./agents.txt");  // or fs.readFileSync etc.
const data = parse(text);

// Validate against the spec
const { ok, issues } = validate(data);
if (!ok) {
  for (const issue of issues) console.warn(issue.severity, issue.message);
}

// Decide what an agent may do
const decision = isActionAllowed(data, "merge_to_main");
//   "allow" | "deny" | "requires_approval" | "unknown"

// Respect rate limits
if (!checkRateLimit(data, "pr", currentDailyPrCount)) {
  throw new Error("agents.txt rate limit reached for this repo");
}

// Or just fetch directly from a URL
const remoteData = await fetchAndParse("https://github.com/barneywohl/agentpress/raw/main/agents.txt");
```

## API

| Function | Description |
|---|---|
| `parse(text)` | Parse a raw `agents.txt` string into a typed object. Tolerant — won't throw. |
| `validate(data)` | Returns `{ ok, issues[] }`. Errors fail validation; warnings don't. |
| `isActionAllowed(data, action)` | Returns `"allow" \| "deny" \| "requires_approval" \| "unknown"`. |
| `checkRateLimit(data, kind, count)` | `kind` ∈ `"pr" \| "issue" \| "comment" \| "branch"`. |
| `fetchAndParse(url)` | `fetch` + `parse` — for agent runtimes. |
| `load(url)` | `fetchAndParse` + `validate` — convenience. |

## Why zero deps

- Auditable in 30 minutes.
- Safe to bundle into agent runtimes.
- Same surface ports cleanly to other languages (see [`agentpress-core`](https://pypi.org/project/agentpress-core/) for Python).

## License

MIT — implementation, copies, and forks are welcome.
