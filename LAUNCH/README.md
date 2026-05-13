# LAUNCH/

Everything needed to take AgentPress v1.0 public. Each file is a copy-pasteable artifact.

## Order of operations on launch day

1. **08:00 ET** — Final pre-flight checks ([LAUNCH_DAY_RUNBOOK.md](LAUNCH_DAY_RUNBOOK.md) §1).
2. **09:00 ET (06:00 PT)** — Publish to npm + PyPI ([LAUNCH_DAY_RUNBOOK.md](LAUNCH_DAY_RUNBOOK.md) §2).
3. **09:30 ET** — Submit Show HN ([HN_POST.md](HN_POST.md)).
4. **09:30 ET** — Post X/Bluesky launch thread ([X_THREAD.md](X_THREAD.md), [BLUESKY_THREAD.md](BLUESKY_THREAD.md)).
5. **10:00 ET** — Submit to Product Hunt ([PRODUCT_HUNT.md](PRODUCT_HUNT.md)).
6. **10:00 ET** — Cross-post to relevant Reddit subs ([REDDIT_POSTS.md](REDDIT_POSTS.md)).
7. **11:00 ET** — Send newsletter outreach ([NEWSLETTER_OUTREACH.md](NEWSLETTER_OUTREACH.md)).
8. **12:00 ET** — Send AI-lab outreach ([AI_LAB_OUTREACH.md](AI_LAB_OUTREACH.md)).
9. **All day** — Respond to comments / issues within 60 min.
10. **18:00 ET** — Post launch-numbers thread.
11. **Day +1** — Begin filing the 20 prepped PRs ([TARGET_REPOS.md](TARGET_REPOS.md), [PR_TEMPLATE.md](PR_TEMPLATE.md)).

## Files

| File | Purpose |
|---|---|
| [LAUNCH_DAY_RUNBOOK.md](LAUNCH_DAY_RUNBOOK.md) | Hour-by-hour playbook for launch day. |
| [HN_POST.md](HN_POST.md) | Show HN submission (title + first comment). |
| [X_THREAD.md](X_THREAD.md) | X/Twitter launch thread (8 tweets). |
| [BLUESKY_THREAD.md](BLUESKY_THREAD.md) | Bluesky mirror, slight tone shift. |
| [LINKEDIN_POST.md](LINKEDIN_POST.md) | Single LinkedIn post for executive audience. |
| [PRODUCT_HUNT.md](PRODUCT_HUNT.md) | Product Hunt page copy + comment. |
| [REDDIT_POSTS.md](REDDIT_POSTS.md) | Tailored posts for r/programming, r/MachineLearning, r/OpenAI, r/Anthropic, r/LocalLLaMA, r/devops. |
| [NEWSLETTER_OUTREACH.md](NEWSLETTER_OUTREACH.md) | Email templates for TLDR, Pragmatic Engineer, AI Tidbits, Latent Space, Rest of World. |
| [AI_LAB_OUTREACH.md](AI_LAB_OUTREACH.md) | Email templates for Anthropic, Cursor, Replit, Cognition, Aider. |
| [TARGET_REPOS.md](TARGET_REPOS.md) | The 20 high-signal repos to file `agents.txt` PRs to. |
| [PR_TEMPLATE.md](PR_TEMPLATE.md) | The PR body template for each filing. |
| [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) | 30-second screen-recording script with shot list. |
| [METRICS_DASHBOARD.md](METRICS_DASHBOARD.md) | What to track post-launch and the 7d / 30d / 90d gates. |

## What I can't do for you

These steps require your hands on a keyboard:
- **`npm publish` and `pip publish`** — both require interactive 2FA.
- **Submit to Hacker News, Product Hunt, X, Bluesky, Reddit, LinkedIn** — your accounts.
- **Send the outreach emails** — your inbox / signature.
- **File the 20 repo PRs** — `gh pr create` per repo (templates are ready).
- **Buy `agentpress.dev`** — registrar account + payment.

Everything below the surface is queued and ready.
