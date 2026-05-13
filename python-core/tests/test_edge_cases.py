"""Edge-case coverage for agentpress-core. Mirrors
packages/core/test/edge-cases.test.mjs so Node and Python parsers stay
behaviorally identical."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentpress_core import SPEC_VERSION, parse, validate

MINIMAL = """[meta]
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
"""


def test_bom_tolerated():
    data = parse("﻿" + MINIMAL)
    assert data.meta.spec_version == "1.0"
    assert data.meta.project == "test"


def test_crlf_parses_same_as_lf():
    lf = parse(MINIMAL)
    cr = parse(MINIMAL.replace("\n", "\r\n"))
    assert cr.allowed_actions == lf.allowed_actions
    assert cr.meta.project == lf.meta.project


def test_trailing_whitespace_stripped():
    noisy = "\n".join(line + "   \t  " if line else line for line in MINIMAL.split("\n"))
    data = parse(noisy)
    assert data.meta.project == "test"
    assert data.allowed_actions == ["read_documentation"]


def test_mixed_tabs_and_spaces_around_eq():
    taby = (
        "[meta]\n"
        "spec_version\t=\t1.0\n"
        "project\t  =\ttabby\n"
        "maintainer  \t=  a@b\n"
        "[allowed_actions]\n"
        "read_documentation\n"
        "[prohibited_actions]\n"
        "merge_to_main\n"
        "[requires_human_approval]\n"
        "schema_migrations\n"
        "[entry_points]\n"
        "agent_guide = /AGENTS.md\n"
        "[disclosure]\n"
        "pr_label = agent-authored\n"
    )
    data = parse(taby)
    assert data.meta.project == "tabby"


def test_empty_file_parseable():
    data = parse("")
    assert data.meta.spec_version == ""
    assert data.allowed_actions == []


def test_empty_file_fails_validation():
    r = validate(parse(""))
    assert r.ok is False
    assert any(i.severity == "error" for i in r.issues)


def test_only_meta_section_warns_or_errors():
    only = "[meta]\nspec_version = 1.0\nproject = x\nmaintainer = a@b\n"
    r = validate(parse(only))
    errors = [i for i in r.issues if i.severity == "error"]
    warnings = [i for i in r.issues if i.severity == "warning"]
    # Either errors or warnings must surface
    assert errors or warnings


def test_unknown_section_preserved():
    body = MINIMAL + "\n[future_v2_thing]\nfoo = bar\nbaz = qux\n"
    data = parse(body)
    assert "future_v2_thing" in data.unknown_sections
    assert data.unknown_sections["future_v2_thing"]["foo"] == "bar"


def test_unknown_spec_version_warns_not_errors():
    future = MINIMAL.replace("spec_version = 1.0", "spec_version = 9.9")
    r = validate(parse(future))
    assert r.ok is True
    assert any(i.severity == "warning" and i.key == "spec_version" for i in r.issues)


def test_section_header_case_insensitive():
    upper = MINIMAL.replace("[meta]", "[META]").replace("[allowed_actions]", "[Allowed_Actions]")
    data = parse(upper)
    assert data.meta.project == "test"
    assert data.allowed_actions == ["read_documentation"]


def test_comment_only_lines_ignored():
    commented = (
        "# top-level comment\n"
        "[meta]\n"
        "# inside-meta comment\n"
        "spec_version = 1.0\n"
        "project = test\n"
        "maintainer = a@b\n"
        "# another comment line\n"
        "[allowed_actions]\n"
        "read_documentation\n"
        "[prohibited_actions]\n"
        "merge_to_main\n"
        "[requires_human_approval]\n"
        "schema_migrations\n"
        "[entry_points]\n"
        "agent_guide = /AGENTS.md\n"
        "[disclosure]\n"
        "pr_label = agent-authored\n"
    )
    data = parse(commented)
    assert data.meta.project == "test"
    assert data.allowed_actions == ["read_documentation"]


def test_inline_hash_kept_in_value():
    inline = MINIMAL.replace(
        "project = test",
        "project = test#not-a-comment",
    )
    data = parse(inline)
    assert data.meta.project == "test#not-a-comment"


def test_large_list_no_truncation():
    many = "\n".join(f"action_{i}" for i in range(200))
    big = MINIMAL.replace("read_documentation", f"read_documentation\n{many}")
    data = parse(big)
    assert len(data.allowed_actions) == 201


def test_comma_list_with_whitespace():
    txt = MINIMAL.replace(
        "schema_migrations",
        "schema_migrations\nchanges_touching =   payments/**  ,   billing/**  ",
    )
    data = parse(txt)
    assert data.requires_human_approval["changes_touching"] == ["payments/**", "billing/**"]


def test_spec_version_constant():
    assert SPEC_VERSION == "1.0"
