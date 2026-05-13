# Metrics dashboard

What to track post-launch and the gate criteria for hitting / killing the project.

## Live metrics

Pull these every Monday at 09:00 ET and log in `LAUNCH/PR_TRACKER.md`.

### npm

```bash
# Daily downloads, last 30 days
curl -s https://api.npmjs.org/downloads/range/last-month/@agent_press/agentpress | jq

# Last week aggregate
curl -s https://api.npmjs.org/downloads/point/last-week/@agent_press/agentpress | jq '.downloads'

# Sub-packages
for pkg in "@agentpress/core" "@agentpress/mcp-server"; do
  curl -s "https://api.npmjs.org/downloads/point/last-week/$pkg" | jq
done
```

### PyPI

```bash
# Via pypistats
pip install pypistats
pypistats recent agentpress-static
pypistats recent agentpress-core
```

### GitHub

```bash
# Stars + forks + watchers
gh repo view barneywohl/agentpress --json stargazerCount,forkCount,watchers

# Traffic (last 14 days)
gh api repos/barneywohl/agentpress/traffic/clones | jq '{count, uniques}'
gh api repos/barneywohl/agentpress/traffic/views | jq '{count, uniques}'
gh api repos/barneywohl/agentpress/traffic/popular/referrers
gh api repos/barneywohl/agentpress/traffic/popular/paths

# Open issues + PRs
gh issue list --repo barneywohl/agentpress --state open | wc -l
gh pr list --repo barneywohl/agentpress --state open | wc -l
```

### Registry adoption

```bash
# Count entries in registry.json
jq '.entries | length' registry/registry.json

# Sum stars at listing
jq '[.entries[].stars_at_listing] | add' registry/registry.json
```

### Hacker News rank

Manually note the rank + comment count via [hnrankings.info](https://hnrankings.info) once at launch + 2h + 6h + 24h + 7d.

### Product Hunt rank

Note daily rank + upvote count at end of launch day, day +1, day +7.

---

## Gate criteria (with hard kill)

| Window post-launch | Pass | Hard kill (archive + walk away) |
|---|---|---|
| **7 days** | npm downloads/wk ≥ 5,000 AND ≥ 100 GitHub stars AND ≥ 5 seed adopters in registry | npm downloads/wk < 2,000 AND GitHub stars < 30 |
| **30 days** | ≥ 50 organic adopters AND ≥ 2,500 GitHub stars AND at least 1 mention from {Anthropic, Cursor, Replit, Cognition, Aider} or major editor | npm downloads/wk < 5,000 AND organic adopters < 20 AND zero AI-lab mentions |
| **90 days** | At least one major code agent ships native support for agents.txt; ≥ 10,000 adopters | None of the above happens; spec didn't catch |

If any hard-kill condition triggers, write `LAUNCH/POSTMORTEM.md` covering:
- What metric specifically missed
- What was tried (post-launch tactics that failed)
- What you'd do differently
- What's salvageable (parsers, GH Action, MCP server can be repurposed)

Then archive the npm + PyPI packages (don't unpublish — leaves dead links; deprecate with a clear notice), close the registry to new submissions, and stop investing time.

---

## Adoption flywheel — the metric that actually matters

Single question: **how many third-party repos publish an `agents.txt` because they want to, not because we asked?**

This is the only metric that proves the standard is becoming a standard. Track it weekly:

```bash
# Approximate via GitHub code search
gh api -X GET search/code --field q='filename:agents.txt path:/' | jq '.total_count'
```

Note: GitHub code search has lag and can undercount; use as a directional signal not a precise number.

If this number doubles week-over-week for 4 consecutive weeks, the standard has caught. If it's flat after 6 weeks, it has not.

---

## What to NOT measure

- Twitter follower count (vanity)
- Newsletter subscribers (we don't have one; resist the urge to add one)
- Press mentions count (one Verge article > 50 niche blogs)
- Fork count (forks are signal of "I want to modify" not "I'm using"; less useful than stars or downloads)
- Time spent responding to comments (unlimited; use a calendar block)

---

## Reporting cadence

- **Daily for first 14 days:** quick numbers thread on X at end of day (transparency = continued attention)
- **Weekly for weeks 3-12:** Monday morning summary in a private notebook
- **Monthly thereafter:** full retrospective with what's working / what's not / what's next

---

## Data store

Keep all metrics history in a private spreadsheet (or `LAUNCH/METRICS.csv` if you want it in-repo and OK with publicness). Columns: date, npm_dl_7d, github_stars, registry_count, hn_rank, ph_rank, organic_adopters_estimate, top_referrer.

This data is the input to v1.1 prioritization decisions and the kill-decision at day 30.
