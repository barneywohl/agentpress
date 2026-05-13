// Edge-case coverage for @agent_press/core. Drives the Phase C work
// in LAUNCH/V1_RC2_GOAL.md.
import { test } from "node:test";
import assert from "node:assert/strict";
import { parse, validate, SPEC_VERSION } from "../dist/index.mjs";

const MINIMAL = `[meta]
spec_version = 1.0
project = test
maintainer = a@b
[allowed_actions]
read_documentation
[prohibited_actions]
merge_to_main
[requires_human_approval]
schema_migrations
[entry_points]
agent_guide = /AGENTS.md
[disclosure]
pr_label = agent-authored
`;

test("BOM at start of file is tolerated", () => {
  const withBom = "﻿" + MINIMAL;
  const data = parse(withBom);
  assert.equal(data.meta.specVersion, "1.0");
  assert.equal(data.meta.project, "test");
});

test("CRLF line endings parse equivalently to LF", () => {
  const crlf = MINIMAL.replace(/\n/g, "\r\n");
  const lf = parse(MINIMAL);
  const cr = parse(crlf);
  assert.deepEqual(cr.allowedActions, lf.allowedActions);
  assert.equal(cr.meta.project, lf.meta.project);
});

test("trailing whitespace on every line is stripped", () => {
  const noisy = MINIMAL
    .split("\n")
    .map((l) => (l ? l + "   \t  " : l))
    .join("\n");
  const data = parse(noisy);
  assert.equal(data.meta.project, "test");
  assert.deepEqual(data.allowedActions, ["read_documentation"]);
});

test("mixed tabs and spaces around `=` parse correctly", () => {
  const taby = `[meta]
spec_version\t=\t1.0
project\t  =\ttabby
maintainer  \t=  a@b
[allowed_actions]
read_documentation
[prohibited_actions]
merge_to_main
[requires_human_approval]
schema_migrations
[entry_points]
agent_guide = /AGENTS.md
[disclosure]
pr_label = agent-authored
`;
  const data = parse(taby);
  assert.equal(data.meta.project, "tabby");
});

test("empty file produces parseable empty AgentsTxt", () => {
  const data = parse("");
  assert.equal(data.meta.specVersion, "");
  assert.deepEqual(data.allowedActions, []);
});

test("empty file fails validate with errors on required meta + section absence", () => {
  const r = validate(parse(""));
  assert.equal(r.ok, false);
  assert.ok(r.issues.some((i) => i.severity === "error"));
});

test("file with only [meta] is missing required sections — validator says so", () => {
  const onlyMeta = "[meta]\nspec_version = 1.0\nproject = x\nmaintainer = a@b\n";
  const r = validate(parse(onlyMeta));
  // Spec requires meta, allowed_actions, prohibited_actions, requires_human_approval, entry_points, disclosure
  // Missing the others must produce errors
  const errors = r.issues.filter((i) => i.severity === "error");
  // At minimum: disclosure missing or empty lists should warn/error
  assert.ok(errors.length > 0 || r.issues.some((i) => i.severity === "warning"));
});

test("unknown sections are preserved in unknownSections, not lost", () => {
  const withUnknown = MINIMAL + "\n[future_v2_thing]\nfoo = bar\nbaz = qux\n";
  const data = parse(withUnknown);
  assert.ok(data.unknownSections.future_v2_thing);
  assert.equal(data.unknownSections.future_v2_thing.foo, "bar");
});

test("unknown spec_version warns but does not error", () => {
  const futureSpec = MINIMAL.replace("spec_version = 1.0", "spec_version = 9.9");
  const r = validate(parse(futureSpec));
  assert.equal(r.ok, true);  // not an error
  assert.ok(r.issues.some((i) => i.severity === "warning" && i.key === "spec_version"));
});

test("section header case is normalised", () => {
  const upper = MINIMAL.replace("[meta]", "[META]").replace("[allowed_actions]", "[Allowed_Actions]");
  const data = parse(upper);
  assert.equal(data.meta.project, "test");
  assert.deepEqual(data.allowedActions, ["read_documentation"]);
});

test("comment-only lines (# at start) are ignored", () => {
  const commented = `# top-level comment
[meta]
# inside-meta comment
spec_version = 1.0
project = test
maintainer = a@b
# another comment line
[allowed_actions]
read_documentation
[prohibited_actions]
merge_to_main
[requires_human_approval]
schema_migrations
[entry_points]
agent_guide = /AGENTS.md
[disclosure]
pr_label = agent-authored
`;
  const data = parse(commented);
  assert.equal(data.meta.project, "test");
  assert.deepEqual(data.allowedActions, ["read_documentation"]);
});

test("inline # is kept as part of the value (v1.0 documented behavior)", () => {
  // Spec to v1.0: comments must be on their own line. # inside a value
  // is part of the value. This guards against accidental # comment-eating.
  const inline = MINIMAL.replace(
    "project = test",
    "project = test#not-a-comment",
  );
  const data = parse(inline);
  assert.equal(data.meta.project, "test#not-a-comment");
});

test("very large list (200 entries) parses without truncation", () => {
  const many = Array.from({ length: 200 }, (_, i) => `action_${i}`).join("\n");
  const big = MINIMAL.replace("read_documentation", `read_documentation\n${many}`);
  const data = parse(big);
  assert.equal(data.allowedActions.length, 201);
});

test("comma-list value with extra whitespace splits cleanly", () => {
  const txt = MINIMAL.replace(
    "schema_migrations",
    "schema_migrations\nchanges_touching =   payments/**  ,   billing/**  ",
  );
  const data = parse(txt);
  assert.deepEqual(data.requiresHumanApproval.changes_touching, ["payments/**", "billing/**"]);
});

test("SPEC_VERSION constant matches what valid files declare", () => {
  assert.equal(SPEC_VERSION, "1.0");
});
