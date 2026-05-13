/**
 * @agent_press/core — zero-dependency reference parser for agents.txt v1.0.
 *
 * Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
 */

// ---------- Types ----------

export type ActionDecision = "allow" | "deny" | "requires_approval" | "unknown";

export interface AgentsTxtMeta {
  specVersion: string;
  project?: string;
  maintainer?: string;
  contactForAgents?: string;
  lastUpdated?: string;
  license?: string;
  aiDisclosureRequired?: boolean;
}

export interface AgentsTxtMcp {
  server?: string;
  auth?: "oauth2" | "api_key" | "none";
  capabilities?: string[];
}

export interface AgentsTxtVerification {
  ciRunner?: string;
  ciWorkflow?: string;
  requiredChecks?: string[];
  expectedExit?: number;
  proofCommand?: string;
}

export interface AgentsTxtRateLimits {
  maxPullRequestsPerDay?: number;
  maxIssuesPerDay?: number;
  maxCommentsPerDay?: number;
  maxConcurrentBranches?: number;
}

export interface AgentsTxtScope {
  maxFilesChanged?: number;
  maxLinesChanged?: number;
  singlePurposePr?: boolean;
}

export interface AgentsTxtDisclosure {
  prLabel?: string;
  commitTrailer?: string;
  requireAttributionInPrBody?: boolean;
}

export interface AgentsTxtContact {
  escalation?: string;
  escalationEmail?: string;
}

export interface AgentsTxt {
  meta: AgentsTxtMeta;
  allowedActions: string[];
  prohibitedActions: string[];
  requiresHumanApproval: Record<string, string[] | boolean>;
  entryPoints: Record<string, string>;
  mcp?: AgentsTxtMcp;
  verification?: AgentsTxtVerification;
  rateLimits: AgentsTxtRateLimits;
  scope: AgentsTxtScope;
  disclosure: AgentsTxtDisclosure;
  contact?: AgentsTxtContact;
  fyi: Record<string, string>;
  /** Sections we didn't explicitly model — preserved for forward compat. */
  unknownSections: Record<string, Record<string, string | string[]>>;
}

export interface ValidationIssue {
  severity: "error" | "warning";
  section?: string;
  key?: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

// ---------- Constants ----------

export const SPEC_VERSION = "1.0";
export const SUPPORTED_VERSIONS = new Set(["1.0"]);
export const REQUIRED_SECTIONS = [
  "meta",
  "allowed_actions",
  "prohibited_actions",
  "requires_human_approval",
  "entry_points",
  "disclosure",
] as const;

const TRUE_VALUES = new Set(["true", "yes", "1", "on"]);
const FALSE_VALUES = new Set(["false", "no", "0", "off"]);

// ---------- Parser ----------

interface RawSection {
  name: string;
  rawKeyValues: Array<[string, string]>;
  rawList: string[];
}

function tokenize(text: string): RawSection[] {
  const sections: RawSection[] = [];
  let current: RawSection | null = null;
  const lines = text.split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("[") && line.endsWith("]")) {
      const name = line.slice(1, -1).trim().toLowerCase();
      current = { name, rawKeyValues: [], rawList: [] };
      sections.push(current);
      continue;
    }
    if (!current) continue;
    const eqIdx = line.indexOf("=");
    if (eqIdx === -1) {
      current.rawList.push(line);
    } else {
      const key = line.slice(0, eqIdx).trim().toLowerCase();
      const value = line.slice(eqIdx + 1).trim();
      current.rawKeyValues.push([key, value]);
    }
  }
  return sections;
}

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function asBool(v: string | undefined): boolean | undefined {
  if (v == null) return undefined;
  const lower = v.toLowerCase();
  if (TRUE_VALUES.has(lower)) return true;
  if (FALSE_VALUES.has(lower)) return false;
  return undefined;
}

function asInt(v: string | undefined): number | undefined {
  if (v == null) return undefined;
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) ? n : undefined;
}

function kvMap(section: RawSection | undefined): Record<string, string> {
  if (!section) return {};
  const out: Record<string, string> = {};
  for (const [k, v] of section.rawKeyValues) out[k] = v;
  return out;
}

function bareList(section: RawSection | undefined): string[] {
  if (!section) return [];
  return [...section.rawList];
}

/**
 * Parse a raw `agents.txt` string into a typed `AgentsTxt` object.
 * Throws nothing; tolerates malformed input. Use `validate()` to surface issues.
 */
export function parse(text: string): AgentsTxt {
  const sections = tokenize(text);
  const byName = new Map<string, RawSection>();
  for (const s of sections) byName.set(s.name, s);

  // Meta
  const metaKv = kvMap(byName.get("meta"));
  const meta: AgentsTxtMeta = {
    specVersion: metaKv.spec_version ?? "",
    project: metaKv.project,
    maintainer: metaKv.maintainer,
    contactForAgents: metaKv.contact_for_agents,
    lastUpdated: metaKv.last_updated,
    license: metaKv.license,
    aiDisclosureRequired: asBool(metaKv.ai_disclosure_required),
  };

  // Allowed / prohibited (bare lists)
  const allowedActions = bareList(byName.get("allowed_actions"));
  const prohibitedActions = bareList(byName.get("prohibited_actions"));

  // Requires-human-approval: mixed bare + keyed
  const rhaSection = byName.get("requires_human_approval");
  const requiresHumanApproval: Record<string, string[] | boolean> = {};
  if (rhaSection) {
    for (const item of rhaSection.rawList) requiresHumanApproval[item] = true;
    for (const [k, v] of rhaSection.rawKeyValues) {
      const list = splitList(v);
      requiresHumanApproval[k] = list.length > 0 ? list : true;
    }
  }

  // Entry points
  const entryPoints = kvMap(byName.get("entry_points"));

  // MCP
  let mcp: AgentsTxtMcp | undefined;
  const mcpKv = kvMap(byName.get("mcp"));
  if (Object.keys(mcpKv).length > 0) {
    mcp = {
      server: mcpKv.server || undefined,
      auth: (mcpKv.auth as AgentsTxtMcp["auth"]) || undefined,
      capabilities: mcpKv.capabilities ? splitList(mcpKv.capabilities) : undefined,
    };
  }

  // Verification
  let verification: AgentsTxtVerification | undefined;
  const vKv = kvMap(byName.get("verification"));
  if (Object.keys(vKv).length > 0) {
    verification = {
      ciRunner: vKv.ci_runner,
      ciWorkflow: vKv.ci_workflow,
      requiredChecks: vKv.required_checks ? splitList(vKv.required_checks) : undefined,
      expectedExit: asInt(vKv.expected_exit),
      proofCommand: vKv.proof_command,
    };
  }

  // Rate limits
  const rlKv = kvMap(byName.get("rate_limits"));
  const rateLimits: AgentsTxtRateLimits = {
    maxPullRequestsPerDay: asInt(rlKv.max_pull_requests_per_day),
    maxIssuesPerDay: asInt(rlKv.max_issues_per_day),
    maxCommentsPerDay: asInt(rlKv.max_comments_per_day),
    maxConcurrentBranches: asInt(rlKv.max_concurrent_branches),
  };

  // Scope
  const scKv = kvMap(byName.get("scope"));
  const scope: AgentsTxtScope = {
    maxFilesChanged: asInt(scKv.max_files_changed),
    maxLinesChanged: asInt(scKv.max_lines_changed),
    singlePurposePr: asBool(scKv.single_purpose_pr),
  };

  // Disclosure
  const dKv = kvMap(byName.get("disclosure"));
  const disclosure: AgentsTxtDisclosure = {
    prLabel: dKv.pr_label,
    commitTrailer: dKv.commit_trailer,
    requireAttributionInPrBody: asBool(dKv.require_attribution_in_pr_body),
  };

  // Contact
  let contact: AgentsTxtContact | undefined;
  const cKv = kvMap(byName.get("contact"));
  if (Object.keys(cKv).length > 0) {
    contact = {
      escalation: cKv.escalation,
      escalationEmail: cKv.escalation_email,
    };
  }

  // FYI
  const fyi = kvMap(byName.get("fyi"));

  // Unknown sections (forward compat preservation)
  const known = new Set([
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
  ]);
  const unknownSections: Record<string, Record<string, string | string[]>> = {};
  for (const s of sections) {
    if (known.has(s.name)) continue;
    const bag: Record<string, string | string[]> = {};
    for (const [k, v] of s.rawKeyValues) bag[k] = v;
    if (s.rawList.length > 0) bag.__list = s.rawList;
    unknownSections[s.name] = bag;
  }

  return {
    meta,
    allowedActions,
    prohibitedActions,
    requiresHumanApproval,
    entryPoints,
    mcp,
    verification,
    rateLimits,
    scope,
    disclosure,
    contact,
    fyi,
    unknownSections,
  };
}

// ---------- Validator ----------

/** Validate an `AgentsTxt` against the v1.0 spec. */
export function validate(data: AgentsTxt): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (!data.meta.specVersion) {
    issues.push({
      severity: "error",
      section: "meta",
      key: "spec_version",
      message: "spec_version is required",
    });
  } else if (!SUPPORTED_VERSIONS.has(data.meta.specVersion)) {
    issues.push({
      severity: "warning",
      section: "meta",
      key: "spec_version",
      message: `unknown spec_version "${data.meta.specVersion}"; this parser supports ${[...SUPPORTED_VERSIONS].join(", ")}`,
    });
  }
  if (!data.meta.project) {
    issues.push({
      severity: "error",
      section: "meta",
      key: "project",
      message: "project name is required",
    });
  }
  if (!data.meta.maintainer) {
    issues.push({
      severity: "error",
      section: "meta",
      key: "maintainer",
      message: "maintainer is required",
    });
  }

  if (data.allowedActions.length === 0) {
    issues.push({
      severity: "warning",
      section: "allowed_actions",
      message: "allowed_actions is empty; agents will treat all actions as unknown",
    });
  }
  if (data.prohibitedActions.length === 0) {
    issues.push({
      severity: "warning",
      section: "prohibited_actions",
      message: "prohibited_actions is empty; consider explicitly forbidding at least secret exfiltration and 2FA bypass",
    });
  }

  if (Object.keys(data.entryPoints).length === 0) {
    issues.push({
      severity: "warning",
      section: "entry_points",
      message: "entry_points is empty; agents will not know where to start",
    });
  }

  if (!data.disclosure.prLabel && !data.disclosure.commitTrailer) {
    issues.push({
      severity: "warning",
      section: "disclosure",
      message: "neither pr_label nor commit_trailer set; agent contributions cannot be identified",
    });
  }

  return { ok: issues.every((i) => i.severity !== "error"), issues };
}

// ---------- High-level helpers ----------

/** Decide what an agent should do for a given action. */
export function isActionAllowed(data: AgentsTxt, action: string): ActionDecision {
  const a = action.toLowerCase().trim();
  if (data.prohibitedActions.some((x) => x.toLowerCase() === a)) return "deny";
  if (Object.keys(data.requiresHumanApproval).some((x) => x.toLowerCase() === a)) {
    return "requires_approval";
  }
  if (data.allowedActions.some((x) => x.toLowerCase() === a)) return "allow";
  return "unknown";
}

/** Returns true if `currentCount` is within the configured limit (or no limit set). */
export function checkRateLimit(
  data: AgentsTxt,
  kind: "pr" | "issue" | "comment" | "branch",
  currentCount: number,
): boolean {
  let limit: number | undefined;
  if (kind === "pr") limit = data.rateLimits.maxPullRequestsPerDay;
  else if (kind === "issue") limit = data.rateLimits.maxIssuesPerDay;
  else if (kind === "comment") limit = data.rateLimits.maxCommentsPerDay;
  else if (kind === "branch") limit = data.rateLimits.maxConcurrentBranches;
  if (limit == null) return true;
  return currentCount < limit;
}

/**
 * Fetch an agents.txt file from a URL and parse it.
 * Use this from agent runtimes; it's a thin wrapper around fetch.
 */
export async function fetchAndParse(url: string): Promise<AgentsTxt> {
  const res = await fetch(url, {
    headers: { Accept: "text/plain, */*" },
  });
  if (!res.ok) {
    throw new Error(`agents.txt fetch failed: ${res.status} ${res.statusText} (${url})`);
  }
  const text = await res.text();
  return parse(text);
}

/** Convenience: fetch + parse + validate in one call. */
export async function load(url: string): Promise<{ data: AgentsTxt; validation: ValidationResult }> {
  const data = await fetchAndParse(url);
  const validation = validate(data);
  return { data, validation };
}
