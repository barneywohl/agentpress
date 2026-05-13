import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parse,
  validate,
  isActionAllowed,
  checkRateLimit,
  SPEC_VERSION,
} from "../dist/index.mjs";

const FIXTURE = `# agents.txt v1.0
[meta]
spec_version = 1.0
project = test-project
maintainer = jane@example.com
contact_for_agents = bot-relations@example.com
last_updated = 2026-05-13
license = MIT
ai_disclosure_required = true

[allowed_actions]
read_documentation
read_source_code
file_pull_request

[prohibited_actions]
merge_to_main
exfiltrate_secrets

[requires_human_approval]
schema_migrations
changes_touching = payments/**, billing/**

[entry_points]
agent_guide = /AGENTS.md
test_command = npm test

[mcp]
server = https://example.com/mcp
auth = oauth2
capabilities = search_docs, run_tests, draft_pr

[verification]
ci_runner = github_actions
required_checks = lint, test
expected_exit = 0

[rate_limits]
max_pull_requests_per_day = 5
max_issues_per_day = 10

[scope]
max_files_changed = 25
max_lines_changed = 800
single_purpose_pr = true

[disclosure]
pr_label = agent-authored
commit_trailer = Authored-by-Agent: <agent-name>
require_attribution_in_pr_body = true

[contact]
escalation = https://example.com/help

[fyi]
preferred_branch_naming = agent/<purpose>
`;

test("parse: meta fields extracted", () => {
  const data = parse(FIXTURE);
  assert.equal(data.meta.specVersion, "1.0");
  assert.equal(data.meta.project, "test-project");
  assert.equal(data.meta.maintainer, "jane@example.com");
  assert.equal(data.meta.aiDisclosureRequired, true);
});

test("parse: allowed_actions list extracted", () => {
  const data = parse(FIXTURE);
  assert.deepEqual(data.allowedActions, [
    "read_documentation",
    "read_source_code",
    "file_pull_request",
  ]);
});

test("parse: prohibited_actions list extracted", () => {
  const data = parse(FIXTURE);
  assert.deepEqual(data.prohibitedActions, ["merge_to_main", "exfiltrate_secrets"]);
});

test("parse: requires_human_approval mixes bare items + keyed patterns", () => {
  const data = parse(FIXTURE);
  assert.equal(data.requiresHumanApproval.schema_migrations, true);
  assert.deepEqual(data.requiresHumanApproval.changes_touching, [
    "payments/**",
    "billing/**",
  ]);
});

test("parse: mcp section parsed with comma-list capabilities", () => {
  const data = parse(FIXTURE);
  assert.equal(data.mcp?.server, "https://example.com/mcp");
  assert.equal(data.mcp?.auth, "oauth2");
  assert.deepEqual(data.mcp?.capabilities, ["search_docs", "run_tests", "draft_pr"]);
});

test("parse: rate_limits ints", () => {
  const data = parse(FIXTURE);
  assert.equal(data.rateLimits.maxPullRequestsPerDay, 5);
  assert.equal(data.rateLimits.maxIssuesPerDay, 10);
});

test("parse: scope bool", () => {
  const data = parse(FIXTURE);
  assert.equal(data.scope.singlePurposePr, true);
});

test("validate: well-formed file is OK", () => {
  const result = validate(parse(FIXTURE));
  assert.equal(result.ok, true);
  assert.equal(result.issues.filter((i) => i.severity === "error").length, 0);
});

test("validate: missing required fields surface errors", () => {
  const bad = `[meta]\nspec_version = 1.0\n`;
  const result = validate(parse(bad));
  assert.equal(result.ok, false);
  const errors = result.issues.filter((i) => i.severity === "error");
  assert.ok(errors.some((e) => e.key === "project"));
  assert.ok(errors.some((e) => e.key === "maintainer"));
});

test("validate: unknown spec_version warns but not errors", () => {
  const future = FIXTURE.replace("spec_version = 1.0", "spec_version = 9.9");
  const result = validate(parse(future));
  assert.equal(result.ok, true);
  assert.ok(result.issues.some((i) => i.severity === "warning" && i.key === "spec_version"));
});

test("isActionAllowed: prohibited returns deny", () => {
  const data = parse(FIXTURE);
  assert.equal(isActionAllowed(data, "merge_to_main"), "deny");
});

test("isActionAllowed: requires_human_approval returns requires_approval", () => {
  const data = parse(FIXTURE);
  assert.equal(isActionAllowed(data, "schema_migrations"), "requires_approval");
});

test("isActionAllowed: allowed returns allow", () => {
  const data = parse(FIXTURE);
  assert.equal(isActionAllowed(data, "read_documentation"), "allow");
});

test("isActionAllowed: not listed returns unknown", () => {
  const data = parse(FIXTURE);
  assert.equal(isActionAllowed(data, "send_email_blast"), "unknown");
});

test("isActionAllowed: case-insensitive", () => {
  const data = parse(FIXTURE);
  assert.equal(isActionAllowed(data, "MERGE_TO_MAIN"), "deny");
});

test("checkRateLimit: under limit returns true", () => {
  const data = parse(FIXTURE);
  assert.equal(checkRateLimit(data, "pr", 4), true);
});

test("checkRateLimit: at-or-over limit returns false", () => {
  const data = parse(FIXTURE);
  assert.equal(checkRateLimit(data, "pr", 5), false);
});

test("checkRateLimit: no limit set returns true", () => {
  const data = parse(FIXTURE);
  assert.equal(checkRateLimit(data, "branch", 99), true);
});

test("parse tolerates CRLF line endings", () => {
  const crlf = FIXTURE.replace(/\n/g, "\r\n");
  const data = parse(crlf);
  assert.equal(data.meta.project, "test-project");
});

test("parse tolerates extra whitespace and comments", () => {
  const noisy = `\n\n   # comment\n[meta]\n  spec_version  =  1.0  \n  project = noisy\n  maintainer = a@b\n[allowed_actions]\n  read_documentation  \n[prohibited_actions]\n  merge_to_main\n[requires_human_approval]\n[entry_points]\n[disclosure]\n  pr_label = agent\n`;
  const data = parse(noisy);
  assert.equal(data.meta.specVersion, "1.0");
  assert.deepEqual(data.allowedActions, ["read_documentation"]);
});

test("SPEC_VERSION constant matches v1.0", () => {
  assert.equal(SPEC_VERSION, "1.0");
});

test("unknown sections are preserved for forward compat", () => {
  const future = FIXTURE + "\n[experimental_v2_thing]\nfoo = bar\n";
  const data = parse(future);
  assert.equal(data.unknownSections.experimental_v2_thing.foo, "bar");
});
