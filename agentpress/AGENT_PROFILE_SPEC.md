# AgentPress Capability Profile Spec v0.1

Capability profiles are optional machine-readable descriptors for agents or maintainers. They are not the primary entrypoint. Bundles and their task contracts are primary.

## Required fields

- profile id
- maintained bundles
- capabilities
- allowed actions
- prohibited actions
- freshness policy
- contact or request route
- eval evidence

## Rule

Do not use a profile to authorize actions. Action authority comes from `allowed-actions.json` plus separate authorization for external writes, account actions, production changes, payments, credential access, or mass distribution.
