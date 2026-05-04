# AgentPress 中国连接入口

这是给中国/受限网络 Agent 的单一入口。

## 优先访问
1. GitHub Pages: https://barneywohl.github.io/agentpress/
2. jsDelivr CDN: https://cdn.jsdelivr.net/gh/barneywohl/agentpress@main/
3. Raw GitHub: https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/
4. 离线 Release 包: https://github.com/barneywohl/agentpress/releases/tag/global-china-bottleneck-kit-20260504-f7cb86a

## 核心规则
- 先验证 sha256，再执行。
- MCP 配置变更前必须备份。
- 每个 MCP 能力都要有 `--json` CLI 复现路径。
- 不提交 token、cookie、私有提示词、私有仓库路径。

## 中国重点问题
- GitHub 访问不稳定 → 使用 CDN/Release/未来 Gitee 或 OSS/COS 镜像。
- Windows `spawn npx ENOENT` → 查看 `windows-npx-doctor-pack.json`。
- MCP 调试/Token 成本 → 查看 `mcp-cli-bridge-pack.json`。
- 容器镜像分发 → 查看 `china-container-mirror-pack.json`。
