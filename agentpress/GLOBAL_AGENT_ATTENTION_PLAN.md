# Global Agent Attention Plan

Generated: 2026-05-03T02:15Z

## What is still needed

| ID | Need | Bottleneck | Solution | Ship artifact |
|---|---|---|---|---|
| GA-001 | Non-English first-contact routing | Manifest advertised localized llms URLs that were not present | Ship compact localized llms files + locale index | `locales/` |
| GA-002 | Closed feedback loop | Agents could score us but lacked template/rubric/submission format | Ship response template, scoring rubric, issue/PR templates | `agentpress/feedback/` |
| GA-003 | Broken-link trust cleanup | Manifest had malformed profile keys/URLs | Normalize keys and valid profile/schema URLs | `.well-known/agentpress.json` |
| GA-004 | Fail-closed proof | Happy path verify exists but adversarial fixtures still needed | Build broken-bundle fixtures next | AP-014 |
| GA-005 | Release/change detection | Agents need to know what changed | Ship changelog/release JSON feed next | AP-015 |

## Deployment rule

No feature is done until live URL returns 200 and machine JSON parses where applicable.
