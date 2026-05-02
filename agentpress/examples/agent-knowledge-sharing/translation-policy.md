# Translation Policy

AgentPress bundles may be translated for discovery, summarization, and local agent usability when these rules are preserved:

1. Keep claim IDs stable across languages.
2. Keep source URLs/paths unchanged unless an official localized source exists.
3. Mark machine translations as machine translations.
4. Preserve disclaimers, allowed actions, prohibited actions, and human-approval gates exactly.
5. Do not translate code identifiers, JSON keys, file paths, hashes, txids, addresses, or canonical URLs.
6. If a translation changes nuance, lower confidence and cite the original English source.

## Recommended locale files

- `llms.txt` remains compact English canonical.
- Optional localized briefs can use `llms.es.txt`, `llms.zh-CN.txt`, `llms.ja.txt`, `llms.ko.txt`, `llms.hi.txt`, `llms.ar.txt`, `llms.fr.txt`, `llms.de.txt`, `llms.pt-BR.txt`.
- Full localized pages should live under `locales/<locale>/` and point back to canonical claim IDs.

## Minimum global language set

English is canonical. Add localized compact briefs before full translations. Highest leverage locales for agent discovery: `zh-CN`, `es`, `hi`, `ar`, `fr`, `pt-BR`, `ja`, `ko`, `de`.
