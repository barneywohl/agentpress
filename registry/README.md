# Registry

A curated, public index of repositories that publish an `agents.txt` v1.0 contract.

→ Browse the registry: <https://agentpress.pages.dev/registry/> (live data: [`registry.json`](./registry.json))

## Why it exists

- Humans: see real `agents.txt` files in production to learn good defaults.
- AI agents: discover repositories whose owners explicitly welcome agent contributions and have declared what's allowed.
- Standards adoption: a public count helps agents.txt cross the chasm.

## How to get listed

1. **Make sure your `agents.txt` is live** at the repo root and parses against the [v1.0 spec](../docs/AGENTSTXT_SPEC.md).
   Validate it locally:
   ```bash
   npx @agent_press/agentpress lint .
   ```
   Or via the GitHub Action:
   ```yaml
   - uses: barneywohl/agentpress/actions/setup-action@v1
   ```

2. **Open a pull request** that adds an entry to `registry.json` under `entries[]`. Use this shape:

   ```json
   {
     "id": "your-org-your-repo",
     "name": "Your Repo Name",
     "owner": "your-org",
     "repo": "your-org/your-repo",
     "url": "https://github.com/your-org/your-repo",
     "agents_txt": "https://github.com/your-org/your-repo/raw/main/agents.txt",
     "category": "library | application | infrastructure | docs | data",
     "stars_at_listing": 1234,
     "language": "TypeScript",
     "description": "One sentence — what your project does.",
     "highlights": [
       "Why your agents.txt is a good example for others",
       "Anything notable about your contract"
     ],
     "added_at": "YYYY-MM-DD"
   }
   ```

3. A maintainer will review:
   - The `agents.txt` resolves and parses cleanly.
   - The repo is actively maintained.
   - The description is accurate.

   Approval typically takes 1–3 business days.

## Inclusion criteria

- Your `agents.txt` parses against the v1.0 spec without errors.
- The repo is publicly accessible.
- The repo is not abandoned (commit within the last 12 months).
- The description is honest. We do not screen for ideology, technology choice, or company affiliation.

## Removal policy

Entries can be removed if:
- The `agents.txt` becomes invalid or inaccessible for >30 days.
- The repo is deleted, archived, or made private.
- The owner requests removal.

## Schema

The full schema for `registry.json` is defined in [../docs/AGENTSTXT_SPEC.md](../docs/AGENTSTXT_SPEC.md) (registry section, coming v1.1). For v1.0, follow the example entries.

## License

The registry data is in the public domain (CC0). The submission tooling is MIT.
