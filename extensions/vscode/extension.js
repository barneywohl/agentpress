// agents.txt — VS Code extension entry point
//
// Surfaces:
//   - syntax highlighting (declared in package.json contributes.grammars)
//   - snippets (declared in package.json contributes.snippets)
//   - command: "agents.txt: Validate active file"
//   - command: "agents.txt: Open v1.0 spec"
//   - on-save: validate against v1.0 spec, surface diagnostics in Problems panel
//
// Validator is inlined for zero-dependency activation. Mirrors the actions/setup-action validator.

const vscode = require("vscode");
const path = require("path");

const SUPPORTED_VERSIONS = new Set(["1.0"]);
const TRUE = new Set(["true", "yes", "1", "on"]);
const FALSE = new Set(["false", "no", "0", "off"]);

let diagnosticCollection;

function asBool(v) {
  if (v == null) return undefined;
  const s = String(v).trim().toLowerCase();
  if (TRUE.has(s)) return true;
  if (FALSE.has(s)) return false;
  return undefined;
}
function splitList(v) { return String(v).split(",").map((s) => s.trim()).filter(Boolean); }

function tokenize(text) {
  const sections = [];
  let current = null;
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("[") && line.endsWith("]")) {
      current = { name: line.slice(1, -1).trim().toLowerCase(), kv: [], bare: [], lineNo: i };
      sections.push(current);
      continue;
    }
    if (!current) continue;
    const eq = line.indexOf("=");
    if (eq === -1) current.bare.push({ value: line, lineNo: i });
    else current.kv.push({ key: line.slice(0, eq).trim().toLowerCase(), value: line.slice(eq + 1).trim(), lineNo: i });
  }
  return sections;
}

function parse(text) {
  const sections = tokenize(text);
  const by = new Map(sections.map((s) => [s.name, s]));
  const kvMap = (n) => Object.fromEntries((by.get(n) || { kv: [] }).kv.map((p) => [p.key, p.value]));
  const bareList = (n) => (by.get(n) || { bare: [] }).bare.map((b) => b.value);

  const m = kvMap("meta");
  const meta = {
    specVersion: m.spec_version || "",
    project: m.project,
    maintainer: m.maintainer,
    aiDisclosureRequired: asBool(m.ai_disclosure_required),
  };
  const allowedActions = bareList("allowed_actions");
  const prohibitedActions = bareList("prohibited_actions");
  const entryPoints = kvMap("entry_points");
  const d = kvMap("disclosure");
  return {
    meta,
    allowedActions,
    prohibitedActions,
    entryPoints,
    disclosure: { prLabel: d.pr_label, commitTrailer: d.commit_trailer },
    sections,
    sectionsByName: by,
  };
}

function validate(data, document) {
  const diagnostics = [];

  function diag(severity, lineNo, message) {
    const line = document.lineAt(Math.max(0, Math.min(lineNo, document.lineCount - 1)));
    const range = line.range;
    diagnostics.push(new vscode.Diagnostic(range, message, severity));
  }

  const metaSec = data.sectionsByName.get("meta");
  const metaLine = metaSec ? metaSec.lineNo : 0;

  if (!data.meta.specVersion) {
    diag(vscode.DiagnosticSeverity.Error, metaLine, "[meta] spec_version is required");
  } else if (!SUPPORTED_VERSIONS.has(data.meta.specVersion)) {
    diag(vscode.DiagnosticSeverity.Warning, metaLine, `[meta] unknown spec_version "${data.meta.specVersion}"; this extension supports ${[...SUPPORTED_VERSIONS].join(", ")}`);
  }
  if (!data.meta.project) diag(vscode.DiagnosticSeverity.Error, metaLine, "[meta] project name is required");
  if (!data.meta.maintainer) diag(vscode.DiagnosticSeverity.Error, metaLine, "[meta] maintainer is required");

  const allowedSec = data.sectionsByName.get("allowed_actions");
  if (allowedSec && data.allowedActions.length === 0) {
    diag(vscode.DiagnosticSeverity.Warning, allowedSec.lineNo, "[allowed_actions] is empty; agents will treat all actions as unknown");
  }
  if (!allowedSec) diag(vscode.DiagnosticSeverity.Error, 0, "Required section [allowed_actions] is missing");

  const prohibitedSec = data.sectionsByName.get("prohibited_actions");
  if (prohibitedSec && data.prohibitedActions.length === 0) {
    diag(vscode.DiagnosticSeverity.Warning, prohibitedSec.lineNo, "[prohibited_actions] is empty; consider explicitly forbidding at least secret exfiltration and 2FA bypass");
  }
  if (!prohibitedSec) diag(vscode.DiagnosticSeverity.Error, 0, "Required section [prohibited_actions] is missing");

  const entrySec = data.sectionsByName.get("entry_points");
  if (entrySec && Object.keys(data.entryPoints).length === 0) {
    diag(vscode.DiagnosticSeverity.Warning, entrySec.lineNo, "[entry_points] is empty; agents will not know where to start");
  }
  if (!entrySec) diag(vscode.DiagnosticSeverity.Error, 0, "Required section [entry_points] is missing");

  const discSec = data.sectionsByName.get("disclosure");
  if (discSec && !data.disclosure.prLabel && !data.disclosure.commitTrailer) {
    diag(vscode.DiagnosticSeverity.Warning, discSec.lineNo, "[disclosure] neither pr_label nor commit_trailer set; agent contributions cannot be identified");
  }
  if (!discSec) diag(vscode.DiagnosticSeverity.Error, 0, "Required section [disclosure] is missing");

  if (!data.sectionsByName.get("requires_human_approval")) {
    diag(vscode.DiagnosticSeverity.Error, 0, "Required section [requires_human_approval] is missing");
  }

  return diagnostics;
}

function validateDocument(document) {
  if (document.languageId !== "agentstxt") return;
  const config = vscode.workspace.getConfiguration("agentstxt");
  const data = parse(document.getText());
  let diagnostics = validate(data, document);
  if (config.get("failOnWarnings", false)) {
    diagnostics = diagnostics.map((d) => {
      if (d.severity === vscode.DiagnosticSeverity.Warning) {
        const promoted = new vscode.Diagnostic(d.range, d.message, vscode.DiagnosticSeverity.Error);
        return promoted;
      }
      return d;
    });
  }
  diagnosticCollection.set(document.uri, diagnostics);
}

function activate(context) {
  diagnosticCollection = vscode.languages.createDiagnosticCollection("agentstxt");
  context.subscriptions.push(diagnosticCollection);

  // On-save validation
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const config = vscode.workspace.getConfiguration("agentstxt");
      if (config.get("validateOnSave", true)) validateDocument(doc);
    }),
  );

  // Validate when an agents.txt is opened
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((doc) => validateDocument(doc)),
  );
  // And re-validate when changed (debounced by VS Code)
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => validateDocument(event.document)),
  );
  // Initial pass over already-open documents
  for (const doc of vscode.workspace.textDocuments) validateDocument(doc);

  // Command: validate
  context.subscriptions.push(
    vscode.commands.registerCommand("agentstxt.validate", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document.languageId !== "agentstxt") {
        vscode.window.showInformationMessage("agents.txt: open an agents.txt file first.");
        return;
      }
      validateDocument(editor.document);
      const issues = diagnosticCollection.get(editor.document.uri) || [];
      const errors = issues.filter((d) => d.severity === vscode.DiagnosticSeverity.Error).length;
      const warnings = issues.filter((d) => d.severity === vscode.DiagnosticSeverity.Warning).length;
      vscode.window.showInformationMessage(`agents.txt: ${errors} error(s), ${warnings} warning(s). See Problems panel.`);
    }),
  );

  // Command: open spec
  context.subscriptions.push(
    vscode.commands.registerCommand("agentstxt.openSpec", () => {
      vscode.env.openExternal(vscode.Uri.parse("https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md"));
    }),
  );
}

function deactivate() {
  if (diagnosticCollection) diagnosticCollection.dispose();
}

module.exports = { activate, deactivate };
