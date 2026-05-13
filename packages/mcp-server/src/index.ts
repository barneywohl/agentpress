#!/usr/bin/env node
/**
 * @agentpress/mcp-server — MCP server that exposes agents.txt as callable tools.
 *
 * Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
 *
 * Tools surfaced to agents:
 *   - agents_txt_fetch        Fetch + parse an agents.txt file from a URL.
 *   - agents_txt_check_action Decide if an action is allowed/denied/requires-approval.
 *   - agents_txt_validate     Validate a raw agents.txt string against the v1.0 spec.
 *   - agents_txt_summarize    Get a one-paragraph human-readable summary of a contract.
 *
 * Resources:
 *   - agentstxt://spec       The full v1.0 specification (markdown).
 *   - agentstxt://example    A canonical example agents.txt (good defaults).
 *
 * Wire into Claude Code (~/.claude/mcp_settings.json), Cursor, or any MCP host:
 *   {
 *     "mcpServers": {
 *       "agentpress": {
 *         "command": "npx",
 *         "args": ["@agentpress/mcp-server"]
 *       }
 *     }
 *   }
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import {
  parse,
  validate,
  isActionAllowed,
  fetchAndParse,
  type AgentsTxt,
} from "@agentpress/core";

const SPEC_DOC_URL =
  "https://raw.githubusercontent.com/barneywohl/agentpress/main/docs/AGENTSTXT_SPEC.md";

const EXAMPLE_AGENTS_TXT = `# agents.txt v1.0
# Canonical example. Substitute your project's values.

[meta]
spec_version = 1.0
project = my-project
maintainer = you@example.com
ai_disclosure_required = true

[allowed_actions]
read_documentation
read_source_code
run_tests_in_ci
file_pull_request
comment_on_issue

[prohibited_actions]
merge_to_main
deploy_to_production
modify_secrets
exfiltrate_secrets
bypass_2fa

[requires_human_approval]
schema_migrations
production_deploys
changes_touching = payments/**, billing/**

[entry_points]
agent_guide = /AGENTS.md
test_command = npm test

[disclosure]
pr_label = agent-authored
commit_trailer = Authored-by-Agent: <agent-name>
`;

function summarize(data: AgentsTxt): string {
  const allowed = data.allowedActions.length;
  const prohibited = data.prohibitedActions.length;
  const approval = Object.keys(data.requiresHumanApproval).length;
  const v = data.meta.specVersion || "?";
  const project = data.meta.project || "(unnamed)";
  return [
    `Project ${project} declares an agents.txt v${v} contract.`,
    `It permits ${allowed} action(s) (${data.allowedActions.slice(0, 5).join(", ") || "none listed"}${allowed > 5 ? ", …" : ""}),`,
    `forbids ${prohibited} action(s) (${data.prohibitedActions.slice(0, 5).join(", ") || "none listed"}${prohibited > 5 ? ", …" : ""}),`,
    `and requires human approval for ${approval} pattern(s).`,
    data.disclosure.prLabel
      ? `Agent-authored PRs should carry the label "${data.disclosure.prLabel}".`
      : "",
    data.disclosure.commitTrailer
      ? `Commit trailer convention: "${data.disclosure.commitTrailer}".`
      : "",
  ]
    .filter(Boolean)
    .join(" ");
}

const server = new Server(
  { name: "agentpress-mcp-server", version: "1.0.0-rc.1" },
  { capabilities: { tools: {}, resources: {} } },
);

// -------- Tools --------

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "agents_txt_fetch",
      description:
        "Fetch and parse an agents.txt file from a URL. Returns the typed contract (meta, allowed/prohibited/approval actions, entry points, rate limits, etc.). Use this whenever you encounter a new repo or website to learn what you're allowed to do there.",
      inputSchema: {
        type: "object",
        properties: {
          url: {
            type: "string",
            description:
              "Direct URL to the agents.txt file, e.g. https://github.com/owner/repo/raw/main/agents.txt or https://example.com/agents.txt",
          },
        },
        required: ["url"],
      },
    },
    {
      name: "agents_txt_check_action",
      description:
        "Given an agents.txt URL and an action name, decide whether an autonomous agent may perform that action. Returns one of: allow, deny, requires_approval, unknown. ALWAYS call this before taking any non-trivial action on a repo or site that publishes an agents.txt.",
      inputSchema: {
        type: "object",
        properties: {
          url: { type: "string", description: "URL to the agents.txt file." },
          action: {
            type: "string",
            description:
              "Action name to check, e.g. merge_to_main, file_pull_request, deploy_to_production.",
          },
        },
        required: ["url", "action"],
      },
    },
    {
      name: "agents_txt_validate",
      description:
        "Validate a raw agents.txt string against the v1.0 spec. Returns errors and warnings. Use this when authoring or editing a contract before committing it.",
      inputSchema: {
        type: "object",
        properties: {
          text: {
            type: "string",
            description: "Raw contents of an agents.txt file.",
          },
        },
        required: ["text"],
      },
    },
    {
      name: "agents_txt_summarize",
      description:
        "Fetch an agents.txt and return a one-paragraph human-readable summary. Useful for telling the user what a project's contract says without showing them the full file.",
      inputSchema: {
        type: "object",
        properties: {
          url: { type: "string", description: "URL to the agents.txt file." },
        },
        required: ["url"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  try {
    if (name === "agents_txt_fetch") {
      const url = String(args?.url ?? "");
      const data = await fetchAndParse(url);
      return {
        content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
      };
    }
    if (name === "agents_txt_check_action") {
      const url = String(args?.url ?? "");
      const action = String(args?.action ?? "");
      const data = await fetchAndParse(url);
      const decision = isActionAllowed(data, action);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              { url, action, decision, project: data.meta.project },
              null,
              2,
            ),
          },
        ],
      };
    }
    if (name === "agents_txt_validate") {
      const text = String(args?.text ?? "");
      const data = parse(text);
      const result = validate(data);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
    if (name === "agents_txt_summarize") {
      const url = String(args?.url ?? "");
      const data = await fetchAndParse(url);
      return { content: [{ type: "text", text: summarize(data) }] };
    }
    return {
      content: [{ type: "text", text: `Unknown tool: ${name}` }],
      isError: true,
    };
  } catch (err) {
    return {
      content: [
        {
          type: "text",
          text: `Error in ${name}: ${err instanceof Error ? err.message : String(err)}`,
        },
      ],
      isError: true,
    };
  }
});

// -------- Resources --------

server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "agentstxt://spec",
      name: "agents.txt v1.0 specification",
      description:
        "The full v1.0 spec for agents.txt. Read this first if you've never encountered one.",
      mimeType: "text/markdown",
    },
    {
      uri: "agentstxt://example",
      name: "Canonical agents.txt example",
      description:
        "A well-formed example agents.txt with sensible defaults. Use it as a template.",
      mimeType: "text/plain",
    },
  ],
}));

server.setRequestHandler(ReadResourceRequestSchema, async (req) => {
  const uri = req.params.uri;
  if (uri === "agentstxt://spec") {
    const res = await fetch(SPEC_DOC_URL);
    const text = await res.text();
    return {
      contents: [{ uri, mimeType: "text/markdown", text }],
    };
  }
  if (uri === "agentstxt://example") {
    return {
      contents: [{ uri, mimeType: "text/plain", text: EXAMPLE_AGENTS_TXT }],
    };
  }
  throw new Error(`Unknown resource: ${uri}`);
});

// -------- Wire stdio transport and start --------

const transport = new StdioServerTransport();
await server.connect(transport);
