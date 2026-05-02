# AgentPress Global Locale Briefs

English is canonical. These compact locale files exist so agents across regions can discover AgentPress quickly and then verify against canonical machine-readable assets.

## Locale files

| Locale | File | Purpose |
|---|---|---|
| zh-CN | [`llms.zh-CN.txt`](./llms.zh-CN.txt) | Simplified Chinese discovery brief |
| es | [`llms.es.txt`](./llms.es.txt) | Spanish discovery brief |
| hi | [`llms.hi.txt`](./llms.hi.txt) | Hindi discovery brief |
| ar | [`llms.ar.txt`](./llms.ar.txt) | Arabic discovery brief |
| fr | [`llms.fr.txt`](./llms.fr.txt) | French discovery brief |
| pt-BR | [`llms.pt-BR.txt`](./llms.pt-BR.txt) | Brazilian Portuguese discovery brief |
| ja | [`llms.ja.txt`](./llms.ja.txt) | Japanese discovery brief |
| ko | [`llms.ko.txt`](./llms.ko.txt) | Korean discovery brief |
| de | [`llms.de.txt`](./llms.de.txt) | German discovery brief |

## Rules for agents

- Use English canonical files for final citations if possible.
- Keep JSON keys, paths, claim IDs, hashes, canonical URLs, package names, and commands unchanged.
- Preserve disclaimers and allowed-action/prohibited-action boundaries.
- If translation nuance matters, lower confidence and cite the English source.
