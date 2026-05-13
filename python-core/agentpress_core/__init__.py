"""agentpress-core — zero-dependency reference parser for agents.txt v1.0.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
"""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field
from typing import Literal, Optional, Union

__version__ = "1.0.0rc2"

SPEC_VERSION = "1.0"
SUPPORTED_VERSIONS = {"1.0"}
REQUIRED_SECTIONS = (
    "meta",
    "allowed_actions",
    "prohibited_actions",
    "requires_human_approval",
    "entry_points",
    "disclosure",
)

ActionDecision = Literal["allow", "deny", "requires_approval", "unknown"]
RateLimitKind = Literal["pr", "issue", "comment", "branch"]

_TRUE = {"true", "yes", "1", "on"}
_FALSE = {"false", "no", "0", "off"}


# ---------- Dataclasses ----------


@dataclass
class Meta:
    spec_version: str = ""
    project: Optional[str] = None
    maintainer: Optional[str] = None
    contact_for_agents: Optional[str] = None
    last_updated: Optional[str] = None
    license: Optional[str] = None
    ai_disclosure_required: Optional[bool] = None


@dataclass
class Mcp:
    server: Optional[str] = None
    auth: Optional[str] = None  # "oauth2" | "api_key" | "none"
    capabilities: list[str] = field(default_factory=list)


@dataclass
class Verification:
    ci_runner: Optional[str] = None
    ci_workflow: Optional[str] = None
    required_checks: list[str] = field(default_factory=list)
    expected_exit: Optional[int] = None
    proof_command: Optional[str] = None


@dataclass
class RateLimits:
    max_pull_requests_per_day: Optional[int] = None
    max_issues_per_day: Optional[int] = None
    max_comments_per_day: Optional[int] = None
    max_concurrent_branches: Optional[int] = None


@dataclass
class Scope:
    max_files_changed: Optional[int] = None
    max_lines_changed: Optional[int] = None
    single_purpose_pr: Optional[bool] = None


@dataclass
class Disclosure:
    pr_label: Optional[str] = None
    commit_trailer: Optional[str] = None
    require_attribution_in_pr_body: Optional[bool] = None


@dataclass
class Contact:
    escalation: Optional[str] = None
    escalation_email: Optional[str] = None


@dataclass
class AgentsTxt:
    meta: Meta
    allowed_actions: list[str] = field(default_factory=list)
    prohibited_actions: list[str] = field(default_factory=list)
    requires_human_approval: dict[str, Union[list[str], bool]] = field(default_factory=dict)
    entry_points: dict[str, str] = field(default_factory=dict)
    mcp: Optional[Mcp] = None
    verification: Optional[Verification] = None
    rate_limits: RateLimits = field(default_factory=RateLimits)
    scope: Scope = field(default_factory=Scope)
    disclosure: Disclosure = field(default_factory=Disclosure)
    contact: Optional[Contact] = None
    fyi: dict[str, str] = field(default_factory=dict)
    unknown_sections: dict[str, dict[str, Union[str, list[str]]]] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    severity: Literal["error", "warning"]
    message: str
    section: Optional[str] = None
    key: Optional[str] = None


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue]


# ---------- Helpers ----------


def _as_bool(v: Optional[str]) -> Optional[bool]:
    if v is None:
        return None
    s = v.strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return None


def _as_int(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v.strip())
    except (TypeError, ValueError):
        return None


def _split_list(v: str) -> list[str]:
    return [s.strip() for s in v.split(",") if s.strip()]


# ---------- Tokenizer + parser ----------


_SECTION_RE = re.compile(r"^\[(.+?)\]\s*$")


def _tokenize(text: str) -> list[tuple[str, list[tuple[str, str]], list[str]]]:
    """Returns list of (section_name, kv_pairs, bare_list_items)."""
    sections: list[tuple[str, list[tuple[str, str]], list[str]]] = []
    current: Optional[tuple[str, list[tuple[str, str]], list[str]]] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _SECTION_RE.match(line)
        if m:
            current = (m.group(1).strip().lower(), [], [])
            sections.append(current)
            continue
        if current is None:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            current[1].append((key.strip().lower(), value.strip()))
        else:
            current[2].append(line)
    return sections


def parse(text: str) -> AgentsTxt:
    """Parse a raw agents.txt string into a typed AgentsTxt object.

    Tolerant — never raises. Use ``validate()`` to surface issues.
    """
    # Strip UTF-8 BOM if present (Python's str.strip() does not remove it)
    if text and text[0] == "﻿":
        text = text[1:]
    tokens = _tokenize(text)
    by_name: dict[str, tuple[str, list[tuple[str, str]], list[str]]] = {}
    for name, kv, bare in tokens:
        by_name[name] = (name, kv, bare)

    def kv_map(name: str) -> dict[str, str]:
        sec = by_name.get(name)
        if not sec:
            return {}
        return {k: v for k, v in sec[1]}

    def bare_list(name: str) -> list[str]:
        sec = by_name.get(name)
        if not sec:
            return []
        return list(sec[2])

    meta_kv = kv_map("meta")
    meta = Meta(
        spec_version=meta_kv.get("spec_version", ""),
        project=meta_kv.get("project"),
        maintainer=meta_kv.get("maintainer"),
        contact_for_agents=meta_kv.get("contact_for_agents"),
        last_updated=meta_kv.get("last_updated"),
        license=meta_kv.get("license"),
        ai_disclosure_required=_as_bool(meta_kv.get("ai_disclosure_required")),
    )

    allowed_actions = bare_list("allowed_actions")
    prohibited_actions = bare_list("prohibited_actions")

    rha_section = by_name.get("requires_human_approval")
    requires_human_approval: dict[str, Union[list[str], bool]] = {}
    if rha_section:
        for item in rha_section[2]:
            requires_human_approval[item] = True
        for k, v in rha_section[1]:
            lst = _split_list(v)
            requires_human_approval[k] = lst if lst else True

    entry_points = kv_map("entry_points")

    mcp_kv = kv_map("mcp")
    mcp: Optional[Mcp] = None
    if mcp_kv:
        mcp = Mcp(
            server=mcp_kv.get("server") or None,
            auth=mcp_kv.get("auth") or None,
            capabilities=_split_list(mcp_kv.get("capabilities", "")),
        )

    v_kv = kv_map("verification")
    verification: Optional[Verification] = None
    if v_kv:
        verification = Verification(
            ci_runner=v_kv.get("ci_runner"),
            ci_workflow=v_kv.get("ci_workflow"),
            required_checks=_split_list(v_kv.get("required_checks", "")),
            expected_exit=_as_int(v_kv.get("expected_exit")),
            proof_command=v_kv.get("proof_command"),
        )

    rl_kv = kv_map("rate_limits")
    rate_limits = RateLimits(
        max_pull_requests_per_day=_as_int(rl_kv.get("max_pull_requests_per_day")),
        max_issues_per_day=_as_int(rl_kv.get("max_issues_per_day")),
        max_comments_per_day=_as_int(rl_kv.get("max_comments_per_day")),
        max_concurrent_branches=_as_int(rl_kv.get("max_concurrent_branches")),
    )

    sc_kv = kv_map("scope")
    scope = Scope(
        max_files_changed=_as_int(sc_kv.get("max_files_changed")),
        max_lines_changed=_as_int(sc_kv.get("max_lines_changed")),
        single_purpose_pr=_as_bool(sc_kv.get("single_purpose_pr")),
    )

    d_kv = kv_map("disclosure")
    disclosure = Disclosure(
        pr_label=d_kv.get("pr_label"),
        commit_trailer=d_kv.get("commit_trailer"),
        require_attribution_in_pr_body=_as_bool(d_kv.get("require_attribution_in_pr_body")),
    )

    c_kv = kv_map("contact")
    contact: Optional[Contact] = None
    if c_kv:
        contact = Contact(
            escalation=c_kv.get("escalation"),
            escalation_email=c_kv.get("escalation_email"),
        )

    fyi = kv_map("fyi")

    known = {
        "meta",
        "allowed_actions",
        "prohibited_actions",
        "requires_human_approval",
        "entry_points",
        "mcp",
        "verification",
        "rate_limits",
        "scope",
        "disclosure",
        "contact",
        "fyi",
    }
    unknown_sections: dict[str, dict[str, Union[str, list[str]]]] = {}
    for name, kv, bare in tokens:
        if name in known:
            continue
        bag: dict[str, Union[str, list[str]]] = {k: v for k, v in kv}
        if bare:
            bag["__list"] = list(bare)
        unknown_sections[name] = bag

    return AgentsTxt(
        meta=meta,
        allowed_actions=allowed_actions,
        prohibited_actions=prohibited_actions,
        requires_human_approval=requires_human_approval,
        entry_points=entry_points,
        mcp=mcp,
        verification=verification,
        rate_limits=rate_limits,
        scope=scope,
        disclosure=disclosure,
        contact=contact,
        fyi=fyi,
        unknown_sections=unknown_sections,
    )


# ---------- Validator ----------


def validate(data: AgentsTxt) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if not data.meta.spec_version:
        issues.append(ValidationIssue("error", "spec_version is required", "meta", "spec_version"))
    elif data.meta.spec_version not in SUPPORTED_VERSIONS:
        issues.append(
            ValidationIssue(
                "warning",
                f'unknown spec_version "{data.meta.spec_version}"; this parser supports {sorted(SUPPORTED_VERSIONS)}',
                "meta",
                "spec_version",
            )
        )
    if not data.meta.project:
        issues.append(ValidationIssue("error", "project name is required", "meta", "project"))
    if not data.meta.maintainer:
        issues.append(ValidationIssue("error", "maintainer is required", "meta", "maintainer"))

    if not data.allowed_actions:
        issues.append(
            ValidationIssue(
                "warning",
                "allowed_actions is empty; agents will treat all actions as unknown",
                "allowed_actions",
            )
        )
    if not data.prohibited_actions:
        issues.append(
            ValidationIssue(
                "warning",
                "prohibited_actions is empty; consider explicitly forbidding at least secret exfiltration and 2FA bypass",
                "prohibited_actions",
            )
        )

    if not data.entry_points:
        issues.append(
            ValidationIssue(
                "warning",
                "entry_points is empty; agents will not know where to start",
                "entry_points",
            )
        )

    if not data.disclosure.pr_label and not data.disclosure.commit_trailer:
        issues.append(
            ValidationIssue(
                "warning",
                "neither pr_label nor commit_trailer set; agent contributions cannot be identified",
                "disclosure",
            )
        )

    ok = all(i.severity != "error" for i in issues)
    return ValidationResult(ok=ok, issues=issues)


# ---------- High-level helpers ----------


def is_action_allowed(data: AgentsTxt, action: str) -> ActionDecision:
    a = action.strip().lower()
    if any(x.lower() == a for x in data.prohibited_actions):
        return "deny"
    if any(k.lower() == a for k in data.requires_human_approval):
        return "requires_approval"
    if any(x.lower() == a for x in data.allowed_actions):
        return "allow"
    return "unknown"


def check_rate_limit(data: AgentsTxt, kind: RateLimitKind, current_count: int) -> bool:
    limit: Optional[int] = None
    if kind == "pr":
        limit = data.rate_limits.max_pull_requests_per_day
    elif kind == "issue":
        limit = data.rate_limits.max_issues_per_day
    elif kind == "comment":
        limit = data.rate_limits.max_comments_per_day
    elif kind == "branch":
        limit = data.rate_limits.max_concurrent_branches
    if limit is None:
        return True
    return current_count < limit


def fetch_and_parse(url: str, timeout: float = 10.0) -> AgentsTxt:
    """Fetch agents.txt from a URL and parse it."""
    req = urllib.request.Request(url, headers={"Accept": "text/plain, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL is user-supplied)
        body = resp.read().decode("utf-8", errors="replace")
    return parse(body)


def load(url: str, timeout: float = 10.0) -> tuple[AgentsTxt, ValidationResult]:
    data = fetch_and_parse(url, timeout=timeout)
    return data, validate(data)


__all__ = [
    "SPEC_VERSION",
    "SUPPORTED_VERSIONS",
    "REQUIRED_SECTIONS",
    "ActionDecision",
    "RateLimitKind",
    "Meta",
    "Mcp",
    "Verification",
    "RateLimits",
    "Scope",
    "Disclosure",
    "Contact",
    "AgentsTxt",
    "ValidationIssue",
    "ValidationResult",
    "parse",
    "validate",
    "is_action_allowed",
    "check_rate_limit",
    "fetch_and_parse",
    "load",
]
