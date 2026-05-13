# Launch-day runbook

Hour-by-hour playbook. All times in **ET (Eastern)** — adjust if you're elsewhere. Dates `T-1` = day before launch, `T0` = launch day.

---

## T-1 (day before launch)

| Time | Task | Owner |
|---|---|---|
| Anytime | Final repo review — make sure v1.0 branch is in good shape | You |
| Anytime | Domain bought + DNS pointed (`agentpress.dev` → Cloudflare Pages) | You |
| Anytime | Pre-write all launch posts (already done — see LAUNCH/) | ✅ Done |
| Anytime | Demo video recorded + edited (see DEMO_VIDEO_SCRIPT.md) | You |
| Anytime | Schedule HN submission slot — best windows: Tue/Wed 09:00–10:00 ET or 13:00–14:00 ET | You |
| 22:00 ET | Run final `npm pack --dry-run` and `python3 -m build --dry-run`; verify nothing missing | You |

---

## T0 launch day

### §1 — 08:00 ET — Final pre-flight

- [ ] Open laptop. Coffee.
- [ ] Verify `npm view @agent_press/agentpress dist-tags` shows current state
- [ ] Verify `pip index versions agentpress-static` shows current state
- [ ] Verify `gh repo view barneywohl/agentpress --json defaultBranchRef` shows main is healthy
- [ ] Verify `https://agentpress.dev` (or fallback) returns the new landing page
- [ ] Verify the `agents.txt` at the repo root is publicly accessible
- [ ] Open all 5 outreach email drafts in your mail client (Newsletter + AI Lab) — DO NOT send yet
- [ ] Open all 6 Reddit posts in browser tabs — DO NOT submit yet

### §2 — 09:00 ET — Publish to npm + PyPI

- [ ] Bump version in `package.json` from `1.0.0-rc.1` to `1.0.0`
- [ ] Bump version in `pyproject.toml` from `1.0.0rc1` to `1.0.0`
- [ ] Bump version in `python-core/pyproject.toml` from `1.0.0rc1` to `1.0.0`
- [ ] Bump version in `packages/core/package.json` from `1.0.0-rc.1` to `1.0.0`
- [ ] Bump version in `packages/mcp-server/package.json` from `1.0.0-rc.1` to `1.0.0`
- [ ] Commit: `git commit -am "release: v1.0.0"`
- [ ] Tag: `git tag v1.0.0`
- [ ] Push: `git push && git push --tags`
- [ ] Publish main CLI: `npm publish` (or `npm publish --tag latest --access public`)
   - Will prompt for npm 2FA — have your authenticator ready
- [ ] Publish core: `cd packages/core && npm run build && npm publish --access public`
- [ ] Publish MCP server: `cd packages/mcp-server && npm install && npm run build && npm publish --access public`
- [ ] Publish Python CLI: `python3 -m build && python3 -m twine upload dist/agentpress-static-1.0.0*`
- [ ] Publish Python parser: `cd python-core && python3 -m build && python3 -m twine upload dist/agentpress_core-1.0.0*`
- [ ] Verify all 5 are live: `npm view @agent_press/agentpress version`, etc.

### §3 — 09:30 ET — Show HN

- [ ] Submit Show HN ([HN_POST.md](HN_POST.md))
- [ ] Within 60 seconds, post the first comment from HN_POST.md as the maker
- [ ] Pin the HN URL — you'll need it everywhere

### §4 — 09:30 ET — X / Bluesky / LinkedIn

- [ ] Post X thread ([X_THREAD.md](X_THREAD.md)) — schedule all 8 tweets in one click via Typefully or post manually
- [ ] Quote-tweet the HN URL
- [ ] Mirror to Bluesky ([BLUESKY_THREAD.md](BLUESKY_THREAD.md))
- [ ] Post LinkedIn ([LINKEDIN_POST.md](LINKEDIN_POST.md)) — IMPORTANT: upload demo video natively, not as a link

### §5 — 10:00 ET — Product Hunt + Reddit

- [ ] Submit Product Hunt ([PRODUCT_HUNT.md](PRODUCT_HUNT.md))
- [ ] Post maker comment within 60 seconds
- [ ] Submit Reddit posts ([REDDIT_POSTS.md](REDDIT_POSTS.md)) one per sub, **wait 30 min between subs** to avoid throttle

### §6 — 11:00 ET — Newsletter outreach

- [ ] Send 5 personalized emails ([NEWSLETTER_OUTREACH.md](NEWSLETTER_OUTREACH.md))
   - TLDR, Pragmatic Engineer, AI Tidbits, Latent Space, Rest of World
- [ ] DO NOT BCC. Send each individually.
- [ ] Track sends in a simple spreadsheet (recipient, date, response status)

### §7 — 12:00 ET — AI lab outreach

- [ ] Send 5 personalized emails ([AI_LAB_OUTREACH.md](AI_LAB_OUTREACH.md))
   - Anthropic devrel, Cursor, Replit Agent, Cognition, Aider
- [ ] Same hygiene: individually, real signature, no BCC

### §8 — 12:00–18:00 ET — Active response window

- [ ] Set notifications for: HN mentions, Product Hunt comments, X mentions, GitHub issues, Reddit replies, email
- [ ] Respond to every comment within 30 minutes during this window
- [ ] If a real bug surfaces, ship a v1.0.1 patch within 4 hours
- [ ] If something genuinely confusing in docs surfaces, edit docs same-day
- [ ] Don't argue. Acknowledge. Iterate.

### §9 — 18:00 ET — Numbers thread

- [ ] Pull initial metrics:
   - HN: rank + comment count
   - Product Hunt: rank + upvote count
   - npm downloads (last 24h via `npm view @agent_press/agentpress` or npm-stats.com)
   - GitHub stars + traffic (`gh api repos/barneywohl/agentpress/traffic/views`)
   - Reddit: aggregate upvotes across subs
- [ ] Post a "5 hours in" transparency thread on X with the numbers (the AI/dev community rewards this)
- [ ] Mirror to Bluesky

### §10 — 22:00 ET — Wrap

- [ ] Skim all open issues — triage them
- [ ] Note any patterns (e.g., "5 people asked about cryptographic signing — bump v1.1 priority")
- [ ] Sleep. Tomorrow is bigger than today.

---

## T+1 to T+7 — Wave-riding

- Daily: respond within 60 min
- Daily: ship 1 patch release based on real feedback
- Daily: file 2-3 PRs to target repos ([TARGET_REPOS.md](TARGET_REPOS.md), [PR_TEMPLATE.md](PR_TEMPLATE.md))
- T+3: VS Code extension submitted to Marketplace (requires Azure DevOps publisher account)
- T+5: Browser extension submitted to Chrome Web Store ($5 dev fee + manual review)
- T+7: Write "week 1" post — numbers + lessons + thanks

## T+30 — Metrics gate

Pull numbers and check against goal targets ([METRICS_DASHBOARD.md](METRICS_DASHBOARD.md)).

If we missed the gate hard (<2k npm downloads/wk + <30 stars), write a postmortem and walk away cleanly.

If we hit (or stretched), kick off v1.1 design work.

---

## Things to NOT do on launch day

- Don't post to LinkedIn before X (X audience finds out from HN; LinkedIn audience needs the social proof of HN ranking)
- Don't pay for promotion. Organic + earned = legitimacy. Paid = "marketing."
- Don't argue with a single critic, no matter how unfair. Time-box every response to 5 minutes.
- Don't ship a v1.0.1 patch with anything other than bug fixes. Every feature added on launch day undermines the v1.0 narrative.
- Don't drink. Tomorrow morning matters more than tonight feels.
