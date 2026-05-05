"""AP-013: Sprint schema stub validation (wave-2 addition).

Validates all 7 sprint feature JSON Schema Draft 2020-12 stubs written by
wave-2 ruflo_sonnet_1.  Verifies:
  - File is parseable JSON
  - Structural completeness ($schema, $id, title, required, properties)
  - $id matches the canonical pointer in agentpress/schemas/index.json
  - schema_version property carries expected const
  - Safety-critical const constraints are present in property definitions
  - required array covers the documented minimum fields

Run: pytest tests/test_sprint_schemas.py -v
"""
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SCHEMAS = _ROOT / "agentpress" / "schemas"
_INDEX = _SCHEMAS / "index.json"

# ---------------------------------------------------------------------------
# Stub catalogue  (key = index.json key, file = filename, consts = list of
#   (path_tuple, expected_value) where path_tuple navigates properties)
# ---------------------------------------------------------------------------
STUBS = [
    {
        "key": "first_user_bootstrap_v2",
        "file": "first-user-bootstrap-v2.schema.json",
        "schema_version_const": "2026-05-04.agentpress-first-user-bootstrap.v2",
        "min_required": [
            "schema_version", "generated_utc", "status", "platform",
            "purpose", "steps", "mcp_snippet", "safety",
            "acceptance_gates", "finding_count", "findings",
        ],
        "safety_consts": [
            (("safety", "external_posts"), False),
        ],
    },
    {
        "key": "proof_capture_v2",
        "file": "proof-capture-v2.schema.json",
        "schema_version_const": "2026-05-04.agentpress-proof-capture.v2",
        "min_required": [
            "schema_version", "generated_utc", "status", "task_id",
            "purpose", "environment", "commands", "artifacts",
            "acceptance", "privacy", "reviewer_checklist",
        ],
        "safety_consts": [
            (("privacy", "operator_must_review_before_external_share"), True),
        ],
    },
    {
        "key": "sandbox_guard_v2",
        "file": "sandbox-guard-v2.schema.json",
        "schema_version_const": "2026-05-04.agentpress-sandbox-guard.v2",
        "min_required": [
            "schema_version", "generated_utc", "status", "scope",
            "allowed_paths", "forbidden_markers", "wrapper_script",
            "policy", "finding_count", "findings",
        ],
        "safety_consts": [
            (("policy", "default_deny_secrets"), True),
            (("policy", "external_effects_require_approval"), True),
        ],
    },
    {
        "key": "adoption_tracker_v1",
        "file": "adoption-tracker-v1.schema.json",
        "schema_version_const": "2026-05-04.agentpress-adoption-tracker.v1",
        "min_required": [
            "schema_version", "generated_utc", "status",
            "period", "root", "funnel", "conversion", "privacy",
        ],
        "safety_consts": [],
    },
    {
        "key": "handoff_pack_v1",
        "file": "handoff-pack-v1.schema.json",
        "schema_version_const": "2026-05-04.agentpress-handoff-pack.v1",
        "min_required": [
            "schema_version", "generated_utc", "status",
            "from_agent", "to_agent", "task_id", "objective",
            "constraints", "evidence_paths", "acceptance_gates",
            "pending_actions", "handoff_manifest",
        ],
        "safety_consts": [],
    },
    {
        "key": "batch_painpoints_v1",
        "file": "batch-painpoints-v1.schema.json",
        "schema_version_const": "2026-05-04.agentpress-batch-painpoints.v1",
        "min_required": [
            "schema_version", "generated_utc", "status",
            "processed_count", "output_dir", "items",
            "approval_required_for_all",
        ],
        "safety_consts": [
            (("approval_required_for_all",), True),
        ],
    },
    {
        "key": "adoption_fixpack_v1",
        "file": "adoption-fixpack-v1.schema.json",
        "schema_version_const": "2026-05-04.agentpress-adoption-fixpack.v1",
        "min_required": [
            "schema_version", "generated_utc", "status",
            "purpose", "inputs", "privacy", "blockers",
            "commands", "acceptance_gates", "errors",
        ],
        "safety_consts": [
            (("privacy", "hidden_telemetry"), False),
            (("privacy", "external_posts"), False),
            (("privacy", "local_files_only"), True),
        ],
    },
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def index():
    return json.loads(_INDEX.read_text())


@pytest.fixture(scope="module")
def loaded_stubs():
    out = {}
    for s in STUBS:
        path = _SCHEMAS / s["file"]
        out[s["key"]] = json.loads(path.read_text())
    return out


# ---------------------------------------------------------------------------
# Parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_file_exists(stub):
    path = _SCHEMAS / stub["file"]
    assert path.exists(), f"{stub['file']} not found at {path}"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_valid_json(stub):
    path = _SCHEMAS / stub["file"]
    data = json.loads(path.read_text())
    assert isinstance(data, dict), "Top-level schema document must be an object"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_draft_2020_12_schema_keyword(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    assert d.get("$schema") == "https://json-schema.org/draft/2020-12/schema", \
        "$schema must declare Draft 2020-12"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_has_id(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    assert "$id" in d and d["$id"].startswith("https://"), \
        "$id must be a https URI"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_id_matches_index_pointer(stub, index, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    pointer = index["schemas"].get(stub["key"])
    assert pointer is not None, \
        f"index.json must have an entry for '{stub['key']}'"
    # $id ends with the filename segment; pointer ends identically
    assert d["$id"].endswith(stub["file"]), \
        f"$id {d['$id']!r} must end with {stub['file']!r}"
    assert pointer.endswith(stub["file"]), \
        f"index pointer {pointer!r} must end with {stub['file']!r}"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_has_title(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    assert d.get("title"), "Schema must have a non-empty title"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_type_is_object(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    assert d.get("type") == "object", "Top-level type must be 'object'"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_has_properties(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    assert "properties" in d and isinstance(d["properties"], dict), \
        "Schema must have a 'properties' object"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_schema_version_const(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    sv_prop = d.get("properties", {}).get("schema_version", {})
    actual_const = sv_prop.get("const")
    assert actual_const == stub["schema_version_const"], (
        f"schema_version const mismatch: got {actual_const!r}, "
        f"expected {stub['schema_version_const']!r}"
    )


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_min_required_fields(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    required = d.get("required", [])
    missing = [f for f in stub["min_required"] if f not in required]
    assert not missing, \
        f"'required' array is missing fields: {missing}"


@pytest.mark.parametrize("stub", STUBS, ids=[s["key"] for s in STUBS])
def test_safety_critical_consts(stub, loaded_stubs):
    d = loaded_stubs[stub["key"]]
    props = d.get("properties", {})
    for path_tuple, expected_val in stub["safety_consts"]:
        node = props
        for segment in path_tuple[:-1]:
            node = node.get(segment, {}).get("properties", {})
        leaf_key = path_tuple[-1]
        leaf = node.get(leaf_key, {})
        actual = leaf.get("const", "__missing__")
        assert actual == expected_val, (
            f"Safety const at {'.'.join(path_tuple)} = {actual!r}, "
            f"expected {expected_val!r}"
        )
