# Post-launch playbook (Phase 13-14)

What to do every day after launch through the first 90 days. This is the work between "we shipped" and "we won."

---

## Daily rhythm — first 7 days

### Morning (45 min)

- Pull metrics ([METRICS_DASHBOARD.md](METRICS_DASHBOARD.md))
- Triage GitHub issues from overnight (label, respond, close obvious bugs with patch PRs)
- File 2-3 new PRs from [TARGET_REPOS.md](TARGET_REPOS.md), waiting at least 24h between filings to the same agent platform

### Midday (15 min)

- Reply to overnight comments on HN / PH / X / Bluesky / Reddit
- Check email for any AI-lab responses or newsletter editor follow-ups

### Evening (30 min)

- One quick patch release if there's a real bug surfaced (1.0.1, 1.0.2…)
- Post a daily numbers thread on X (transparency keeps attention; "wow we're at X downloads" beats silence)
- Update `LAUNCH/PR_TRACKER.md` with new PR statuses

---

## Daily rhythm — days 8-30

Drop to:
- 30 min/day for issue triage + PR tracking + responses
- 1-2 PR filings per week (slower, more thoughtful, target only repos with active maintainers)
- Weekly "weekly numbers" thread on Mondays

---

## Weekly priorities

| Week | Focus |
|---|---|
| 1 | Wave-ride the launch. File seed PRs. Patch bugs. Don't add features. |
| 2 | First PR merges land — celebrate publicly. Reach out to second-tier repos (the next 20). |
| 3 | Newsletter coverage hopefully landing. Pitch a podcast (Latent Space, Software Engineering Daily). |
| 4 | First "cool, you adopted it" post showcasing 5+ public repos. Begin v1.1 design doc. |
| 5-8 | v1.1 design + community discussion. Open RFC issues for cryptographic signing, per-agent ACLs. |
| 9-12 | Ship v1.1 if community signal is strong. Prep a conference talk submission (AI Engineer Summit, Anthropic Builder Summit). |

---

## v1.1 design (queue for week 4)

### v1.1 priorities (in order)

1. **Cryptographic signing**: `agents.txt.sig` companion file. Lets agents verify the file hasn't been tampered with mid-route. Use ed25519. Spec: include a public key in `[meta]` section, sign the canonical-form bytes, append signature to `agents.txt.sig`.

2. **Per-agent overrides**: `[allowed_actions:devin]`, `[prohibited_actions:cursor]` etc. Allow projects to grant different agents different latitudes. Vendor-namespaced.

3. **Validation API**: a hosted endpoint `https://agentpress.dev/api/validate?url=…` that returns the parsed + validated contract as JSON. For agents that can't bundle a parser. Free, rate-limited, no signup.

4. **Compliance mode**: a stricter parse mode that requires every action to be in a controlled vocabulary (no free-form). For enterprise / regulated environments.

### v1.1 NOT yet

- Hosted SaaS dashboard
- Agent identity verification (separate problem; defer to existing OAuth/OIDC)
- Replacement for CONTRIBUTING.md / LICENSE

---

## Thirty-day retrospective

At day 30, write a public retrospective post on the agentpress.dev blog (which doesn't exist yet — create `/blog/30-days.html` if needed):

```
## 30 days of agents.txt

Numbers:
- npm downloads/wk: [actual]
- GitHub stars: [actual]
- Repos in registry: [actual]
- AI labs / editors with native support: [list]
- PRs filed by us: [count]
- PRs merged: [count]

What worked:
- [3 things]

What didn't:
- [3 things]

What we're shipping next:
- [v1.1 priorities + dates]

Thanks to:
- [individuals who helped, especially those who landed PRs in their own repos]
```

This post is itself a viral mechanic if the numbers are good.

---

## Sustainability

If this catches:

- Move the spec to a vendor-neutral GitHub org (e.g., `agentstxt-org/spec`). Keeps the standard from being a "barneywohl thing."
- Form a small RFC process for v1.x changes. Three maintainers, public discussion via issues, decisions documented in `docs/rfcs/`.
- Decline acquisition offers from any AI lab unless the offer includes vendor-neutral governance. The standard's value is its neutrality.

If this doesn't catch:

- Hard-kill at day 30 per [METRICS_DASHBOARD.md](METRICS_DASHBOARD.md).
- Deprecate (don't unpublish) the npm + PyPI packages with a clear notice.
- Open-source the postmortem.
- Reuse the parser code + GH Action infrastructure for whatever comes next. Nothing built was wasted.

---

## What "won" looks like

90 days from launch, agents.txt has won if:

1. At least one of {Anthropic, Cursor, Replit, Cognition, Aider} ships native support, citing the spec by name.
2. ≥ 200 third-party repos publish an `agents.txt` (organic, not from our PRs).
3. The phrase "agents.txt" shows up in tech press without the word "AgentPress" — meaning the standard has decoupled from the brand.

That's the bar. Build for that.
