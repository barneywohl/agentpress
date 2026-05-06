# AgentPress Gorilla Execution Queue

Generated: 2026-05-06T01:00:46Z

Status: **prepared_not_posted** — exact targets and utility-first drafts are ready; no public posting is automated.

## Guardrail
Do not post/comment/DM externally without explicit approval of the exact target and draft. Security/credential issues require maintainer opt-in.

## Targets

### 1. OpenHands — git marketplace/plugin distribution without packaging overhead
- URL: https://github.com/OpenHands/OpenHands/issues/12316
- Pack: `openhands-runtime-hang`
- Artifact: `agentpress/repro/runtime-hang-repro-capsule.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/openhands-runtime-hang-result.json`
- Risk: low-medium
- Next action: prepare neutral static plugin/connector manifest compatibility note
- Draft: I saw the plugin marketplace discussion and made a small static manifest/receipt pattern that may be useful as a neutral fixture: it keeps connector metadata, expected runtime behavior, and proof receipts in repo-native JSON. If useful, I can adapt it into a minimal OpenHands-specific example without telemetry or external writes.

### 2. Roo Code — malformed/partial tool call response stops task
- URL: https://github.com/RooCodeInc/Roo-Code/issues/12185
- Pack: `cline-provider-repro`
- Artifact: `agentpress/compatibility/provider-adapter-repro-pack.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/cline-provider-repro-result.json`
- Risk: medium-low
- Next action: prepare minimal malformed-tool-call fixture attachment
- Draft: This looks like a good candidate for a tiny machine-checkable repro fixture rather than a long issue thread. I have a static provider/tool-call repro pack format that records the failing tool payload, expected adapter contract, and result receipt; happy to trim it into a Roo-specific fixture if useful.

### 3. OpenHands — repo cloned into subdirectory breaks setup/hook root assumptions
- URL: https://github.com/OpenHands/OpenHands/issues/13475
- Pack: `openhands-runtime-hang`
- Artifact: `agentpress/repro/runtime-hang-repro-capsule.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/openhands-runtime-hang-result.json`
- Risk: medium-low
- Next action: prepare root/cwd manifest example
- Draft: For the workspace-root ambiguity here, a small static root manifest may help make expected repo root, setup hooks, cwd, and runtime evidence explicit. I can attach a minimal JSON fixture showing root path, hook discovery paths, and validation receipt if that would help the reproduction.

### 4. LangGraph — sub-agent handoff routes back incorrectly / waiting state ambiguity
- URL: https://github.com/langchain-ai/langgraph/issues/6064
- Pack: `langgraph-checkpoint-replay`
- Artifact: `agentpress/repro/checkpoint-replay-minimal-repro.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/langgraph-checkpoint-replay-result.json`
- Risk: medium-low
- Next action: prepare handoff/task-card fixture
- Draft: This seems like a state/handoff ambiguity where an explicit task-card + handoff receipt could make the expected next actor and waiting state machine-checkable. I can attach a minimal static fixture/replay packet if useful.

### 5. Cline — MCP auto-approve disabled but tool calls execute without prompt
- URL: https://github.com/cline/cline/issues/10499
- Pack: `cline-tool-approval`
- Artifact: `agentpress/security/approval-bypass-risk-result.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/cline-tool-approval-result.json`
- Risk: high
- Next action: hold unless maintainer invites; security-sensitive
- Draft: Security-sensitive; do not post unsolicited. If maintainers request fixtures, provide only a minimal fail-closed approval receipt format and avoid exploit details.

### 6. LangGraph — multiple tool results for one tool call around human approval flow
- URL: https://github.com/langchain-ai/langgraph/issues/4397
- Pack: `langgraph-checkpoint-replay`
- Artifact: `agentpress/repro/checkpoint-replay-minimal-repro.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/langgraph-checkpoint-replay-result.json`
- Risk: medium
- Next action: prepare runnable approval-flow replay packet only if code fixture can be specific
- Draft: This looks like a human-approval/tool-result routing repro. A compact replay packet with expected tool_call_id, approval state, and resulting messages may help keep the fixture small. I can prepare one if useful.

### 7. LlamaIndex — ContextVar propagation differs between FunctionTool sync/async paths
- URL: https://github.com/run-llama/llama_index/issues/21555
- Pack: `llamaindex-rag-safety`
- Artifact: `agentpress/safety/rag-tool-safety-bundle.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/llamaindex-rag-safety-result.json`
- Risk: medium
- Next action: prepare tiny tool context metadata fixture
- Draft: This seems fixture-friendly: record expected context metadata, sync/async tool path, and observed propagation result in a static receipt so regressions are easy to compare. I can trim a LlamaIndex-specific example if helpful.

### 8. Cline — large files/context window failures with no recovery
- URL: https://github.com/cline/cline/issues/4389
- Pack: `cline-provider-repro`
- Artifact: `agentpress/compatibility/provider-adapter-repro-pack.json`
- Receipt: `agentpress/growth/gorilla-utility-pack/receipts/cline-provider-repro-result.json`
- Risk: medium
- Next action: prepare focused source-map/context bundle example
- Draft: A source-map + focused task-card bundle can make large repo context failures reproducible without pasting huge files into context. I can attach a small static example if this issue is still active.
