# agentpress/setup-action

> Validate `agents.txt` v1.0 on every PR and push. Fails CI when the contract is malformed.

## Usage

Add this to your repo at `.github/workflows/agents-txt.yml`:

```yaml
name: agents.txt
on:
  pull_request:
    paths: ['agents.txt']
  push:
    branches: [main]
    paths: ['agents.txt']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: barneywohl/agentpress/actions/setup-action@v1
        with:
          file: agents.txt
          fail-on-warnings: false
```

> **Note:** During the v1.0 release candidate, reference the action via
> `barneywohl/agentpress/actions/setup-action@v1.0` (the v1.0 branch).
> Once v1.0 ships final, a dedicated `agentpress/setup-action@v1`
> repo will be published and you can switch to that shorter form.

That's it. The action will:
1. Parse `agents.txt` against the [v1.0 spec](https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md).
2. Fail the job on any **error** (missing required fields, malformed sections).
3. Optionally fail on warnings if `fail-on-warnings: true`.
4. Render a structured report in the workflow Step Summary.
5. Expose outputs you can consume in later steps.

## Inputs

| Name | Required | Default | Description |
|---|---|---|---|
| `file` | no | `agents.txt` | Path to your `agents.txt` (relative to repo root). |
| `fail-on-warnings` | no | `false` | If `true`, also fail the job on warnings. |
| `json-output` | no | `false` | Print full JSON report to the log in addition to the human summary. |

## Outputs

| Name | Description |
|---|---|
| `ok` | `"true"` if valid, `"false"` otherwise. |
| `errors` | Number of errors found. |
| `warnings` | Number of warnings found. |
| `spec-version` | The `[meta].spec_version` declared in the file. |

## Why use it

- **Catch malformed contracts before they ship.** A broken `agents.txt` is worse than no `agents.txt` — agents may misread or default to permissive behavior.
- **Step summary in every CI run.** Readable report in the Actions UI, no log-diving.
- **Zero dependencies.** Single self-contained Node script. Runs fast, audits cleanly.
- **Forward compatible.** Warns (does not fail) on unknown spec versions so older actions don't break newer files.

## Don't have an agents.txt yet?

```bash
npx @agent_press/agentpress init
```

→ <https://github.com/barneywohl/agentpress>

## License

MIT.
