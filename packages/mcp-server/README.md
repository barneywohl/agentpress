# @agentpress/mcp-server

> Model Context Protocol (MCP) server that exposes `agents.txt` as queryable tools and resources for any MCP-speaking agent: Claude Code, Cursor, Devin, Aider, Continue, Replit Agent, etc.

## Why

`agents.txt` declares what an agent may do on a given repo or site. With this MCP server installed, an agent can ask, in real time:

> "Before I open this PR, fetch the repo's `agents.txt` and tell me if `merge_to_main` is allowed."

…and get a structured, deterministic answer.

## Install

```bash
npm install -g @agentpress/mcp-server
```

## Wire into Claude Code

Edit `~/.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "agentpress": {
      "command": "npx",
      "args": ["-y", "@agentpress/mcp-server"]
    }
  }
}
```

Restart Claude Code. The four `agents_txt_*` tools and two resources become available.

## Wire into Cursor

Edit `~/.cursor/mcp.json` (or via Settings → MCP):

```json
{
  "mcpServers": {
    "agentpress": {
      "command": "npx",
      "args": ["-y", "@agentpress/mcp-server"]
    }
  }
}
```

## Tools surfaced

| Tool | Description |
|---|---|
| `agents_txt_fetch(url)` | Fetch + parse an agents.txt file from a URL. Returns the typed contract. |
| `agents_txt_check_action(url, action)` | Decide if an action is `allow` / `deny` / `requires_approval` / `unknown`. |
| `agents_txt_validate(text)` | Validate raw agents.txt content against the v1.0 spec. |
| `agents_txt_summarize(url)` | One-paragraph human summary of a contract. |

## Resources surfaced

| URI | Description |
|---|---|
| `agentstxt://spec` | The full v1.0 specification (markdown). |
| `agentstxt://example` | A canonical example agents.txt with sensible defaults. |

## Example interaction

```
User: Run `gh repo clone someorg/somerepo` and start working on issue #42.
Agent: [calls agents_txt_fetch("https://github.com/someorg/somerepo/raw/main/agents.txt")]
       → contract requires PR label "agent-authored", prohibits merge_to_main,
         and requires human approval for changes_touching=payments/**.
       I'll branch, label the PR, and skip touching payments/.
```

## Privacy

- Stdio-only. No network telemetry from the server itself.
- `agents_txt_fetch` and `agents_txt_summarize` make outbound HTTPS requests to the URLs you (or the calling agent) pass.
- No data is persisted on disk.

## Development

```bash
cd packages/mcp-server
npm install
npm run build
npm start  # speaks MCP over stdio; pipe to an MCP host
```

## License

MIT.
