# PR template — adopting agents.txt

Use this body for every PR that adds an `agents.txt` to a target repo. Tailor the contract itself to the project's actual constraints — do NOT ship a copy-paste contract.

---

## Title

```
Add agents.txt v1.0 — declare what autonomous AI agents may do on this repo
```

## PR body

```
This PR adds an agents.txt v1.0 file at the repo root, declaring what autonomous AI agents (Claude Code, Cursor, Devin, Aider, Replit Agent, Continue, etc.) are allowed and prohibited from doing on this project.

## Why

In 2026 coding agents land PRs in production codebases at scale. Without a machine-readable contract at the repo root, every agent has to guess at what the maintainers consider safe. The result is a mix of unsafe edits and over-cautious refusals.

agents.txt is the smallest possible answer: one file, three required lists (allowed / prohibited / requires_human_approval), plus entry points, rate limits, and disclosure rules. Same lineage as robots.txt (1994), sitemap.xml (2005), and llms.txt (2024).

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

## What this contract declares for {{REPO_NAME}}

I drafted the file to match what I believe are sensible defaults for this project. Specifically:

- **Allowed**: {list 3-5 from the contract; e.g., read_documentation, run_tests_in_ci, file_pull_request, comment_on_issue}
- **Requires human approval**: {2-3 from the contract; tailored to this repo's sensitive areas}
- **Prohibited**: {3-5 always-no items; e.g., merge_to_main, deploy_to_production, modify_secrets}
- **Rate limits**: {your guesses; e.g., max 5 PRs/day per agent}
- **Disclosure**: {pr_label = agent-authored, commit trailer convention}

You should review and tweak — these are guesses, not policy. If anything is wrong, just edit the file in this PR.

## Anything I shouldn't have done

- I did NOT touch CONTRIBUTING.md, LICENSE, or CODE_OF_CONDUCT.md. Those are complementary; agents.txt sits alongside them.
- I did NOT add a CI gate. If you want one, the GitHub Action is at https://github.com/barneywohl/agentpress/tree/main/actions/setup-action — three lines in your workflows file.
- I did NOT add a README badge. If you want one, the snippet is at https://github.com/barneywohl/agentpress/blob/main/docs/BADGE.md.

## What I'd love feedback on

- Are the prohibited_actions actually prohibited for this project? Anything missing?
- Are the entry_points (test_command, lint_command, agent_guide) right?
- Is `requires_human_approval` too restrictive or not restrictive enough?

This standard is at v1.0; adopting it now means your repo is one of the first dozen to have a machine-readable agent contract. If you maintain a different repo too, adoption is `npx @agent_press/agentpress init`.

Happy to iterate, or close this if it's not a fit. No hard feelings either way.

— [your name]

---

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Site: https://agentpress.dev
All code MIT.
```

## Filing checklist

- [ ] PR is from a personal fork, NOT a service account
- [ ] Single commit (squashable)
- [ ] Only adds `agents.txt` — no other file changes
- [ ] Contract is tailored to the project, not a copy-paste
- [ ] PR body uses the template above with the {{}} placeholders filled in
- [ ] Title matches the title above exactly
- [ ] Wait for response before filing more PRs (don't spam your queue)
- [ ] Track the PR in LAUNCH/PR_TRACKER.md (date, repo, URL, status)

## If the PR is questioned

- "Why this format / not YAML" → low cognitive load, familiarity from .gitconfig/.editorconfig
- "Why a new file / not extend CONTRIBUTING.md" → CONTRIBUTING.md is for humans, not parseable
- "Is this related to a startup" → no, fully MIT spec, no monetization plans, no signup
- "What if my agent doesn't read this" → today none do natively; we're working with the platforms (Anthropic, Cursor, Replit, Cognition, Aider) to ship native support
