# README Badge

Add this to your README to show your repo follows [`agents.txt v1.0`](https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md):

## Recommended (flat-square, blue)

```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/barneywohl/agentpress)
```

Renders as: [![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/barneywohl/agentpress)

## Variants

### Plastic (subtle)
```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=plastic)](https://github.com/barneywohl/agentpress)
```

### Flat (no shadow)
```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=flat)](https://github.com/barneywohl/agentpress)
```

### For-the-badge (loud, hero header)
```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=for-the-badge)](https://github.com/barneywohl/agentpress)
```

### Custom color (your project's brand color)
Replace `2563eb` (blue) with your hex (no `#`):

```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-ec4899?style=flat-square)](https://github.com/barneywohl/agentpress)
```

## What it signals

- This repo has an `agents.txt` at its root.
- The file declares allowed/prohibited/requires-approval actions for autonomous AI agents.
- Coding agents that respect the standard (Claude Code, Cursor, Devin, Aider, …) will read and obey it before acting.

## Where to put it

- **Top of your README**, alongside other badges like CI status, npm version, license.
- Optionally on your project's marketing site.
- In your `CONTRIBUTING.md` to remind human contributors that agent contributions follow declared rules.

## Add yourself to the registry

Once your `agents.txt` is live, [submit a PR to the registry](../registry/README.md) so other developers and agent runtimes can find your repo as an example.
