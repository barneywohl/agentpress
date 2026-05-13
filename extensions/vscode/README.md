# agents.txt — VS Code extension

> Syntax highlighting, snippets, and on-save validation for `agents.txt` v1.0 — the open standard for telling AI agents what they're allowed to do on your repo.

## Features

- **Syntax highlighting** for `agents.txt` files (sections, keys, values, comments, common action vocabulary).
- **Snippets**:
  - Type `agents-txt` and Tab → insert a complete v1.0 starter template.
  - Type `[meta]`, `[allowed_actions]`, `[prohibited_actions]`, etc. → insert pre-filled section blocks.
- **On-save validation**: violations of the v1.0 spec appear in the **Problems** panel with red squigglies.
- **Commands**:
  - `agents.txt: Validate active file` — re-run the validator on demand.
  - `agents.txt: Open v1.0 spec` — open the spec in your browser.
- **Zero dependencies**: the parser is inlined, so the extension activates instantly.

## Install

Search "agents.txt" in the VS Code Marketplace, or:

```
ext install barneywohl.agents-txt
```

## What gets validated

- `[meta] spec_version` is present and supported.
- `[meta] project` and `[meta] maintainer` are non-empty.
- All required sections exist: `[meta]`, `[allowed_actions]`, `[prohibited_actions]`, `[requires_human_approval]`, `[entry_points]`, `[disclosure]`.
- `[disclosure]` has at least one of `pr_label` or `commit_trailer`.
- Lists in `[allowed_actions]` and `[prohibited_actions]` are non-empty (warning if empty).

## Configuration

| Setting | Default | Description |
|---|---|---|
| `agentstxt.validateOnSave` | `true` | Re-validate when the file is saved. |
| `agentstxt.failOnWarnings` | `false` | Promote warnings to errors in the Problems panel. |

## Don't have an `agents.txt` yet?

```
npx @agent_press/agentpress init
```

Then open the generated file in VS Code — this extension takes over from there.

## Links

- Spec: <https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md>
- Repo: <https://github.com/barneywohl/agentpress>
- Registry: <https://agentpress.pages.dev/registry/>

## License

MIT.
