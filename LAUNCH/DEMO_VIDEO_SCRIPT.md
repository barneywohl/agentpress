# Demo video script (30 seconds)

Single take, screen recording, no narration. Captions on-screen. Goal: someone watching with sound off should understand what the product does and want to try it.

## Tools

- **Recorder:** macOS QuickTime Player (Cmd-Shift-5) or screen.studio if budget allows
- **Editor:** screen.studio (auto-zoom, easy captions) or DaVinci Resolve (free)
- **Output:** 1080p, MP4, no music (or very subtle synth pad), 30 seconds max

## Shot list

| Time | Shot | Caption (top center, sans-serif) |
|---|---|---|
| 0:00–0:02 | Open terminal in a clean repo (`my-cool-project/`); `ls` shows just src/, README.md, package.json | `What's allowed on your repo?` |
| 0:02–0:05 | Type `npx @agent_press/agentpress init` and hit enter | (no caption) |
| 0:05–0:10 | The init wizard runs through 5 questions; answer with reasonable defaults (just press enter) | (no caption — let the wizard speak) |
| 0:10–0:13 | Wizard finishes; `ls` again shows the new `agents.txt` and `.well-known/` | `agents.txt at the repo root.` |
| 0:13–0:17 | `cat agents.txt` — scroll smoothly through the file showing [meta], [allowed_actions], [prohibited_actions] sections | `Three lists. Open standard. MIT.` |
| 0:17–0:20 | Quick cut: VS Code opens the file with syntax highlighting; cursor hovers over a section header showing autocomplete | `Editor support included.` |
| 0:20–0:23 | Quick cut: a GitHub PR page; the AgentPress action shows a green check and a Step Summary with the contract verified | `CI lint on every PR.` |
| 0:23–0:26 | Quick cut: Claude Code in a terminal asks "before merging — let me check the agents.txt contract" and gets back `merge_to_main: deny` | `Agents respect it natively (MCP).` |
| 0:26–0:30 | Final card: `agentpress.dev` text in serif, blue accent, on the dark background. Small subtitle: "robots.txt → llms.txt → agents.txt" | (no caption needed; the card IS the caption) |

## Audio

- No music: quieter, more serious, lets the text breathe
- OR: very subtle ambient synth pad (Brian Eno style, 30dB below normal) for emotional lift

## Captions style

- Font: Inter or IBM Plex Sans
- Size: 36-44pt at 1080p
- Color: white with subtle dark shadow OR var(--accent) blue depending on background
- Position: top-center, 8% from top
- Timing: appear 200ms after shot starts, disappear 200ms before shot ends

## Export & distribution

- Export at 1080p H.264, < 5 MB if possible (HN/X have file size limits)
- Also export a 1:1 square crop for Instagram / Bluesky
- Generate a GIF (ezgif.com) for embedding in HN comments / GitHub README

## Where to use

- X launch thread tweet 1 (attach as video)
- Bluesky launch post (same)
- LinkedIn post (LinkedIn rewards native video heavily — DO upload directly, not as a YouTube link)
- Product Hunt gallery (PH supports video gallery items)
- agentpress.dev hero section (replace static install snippet with auto-playing muted video)
- README.md as an animated GIF

## Don't

- Don't add talking-head footage. Increases run time, decreases re-watch rate, hurts share rate.
- Don't use stock music. Free music libraries are obvious and cheapen the brand.
- Don't add a logo intro. Wastes 3 of your 30 seconds.
- Don't include an "AI" voiceover. Audience this product targets will mock it.

## Backup: animated GIF version

If video editing isn't possible by launch day, ship a 1080×720 animated GIF made from the same shot list at ~12fps. Keep it under 6 MB. Loops infinitely. Embed in README and posts as a fallback.
