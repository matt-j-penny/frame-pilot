---
name: reel-editor
description: "One-pass AI editor for vertical talking-head Reels / Shorts / TikToks. Give it a raw video and a style name and it does the whole edit: rough cut (silences, fillers, retakes), word-by-word captions, motion graphics, logos/screenshots, music, SFX, loudness, Remotion render and a visual QA loop. Also creates, refines, locks and lists reusable named styles built from reference videos. Use when the user says '/reel-editor', 'edit this reel in <style>', 'create style <name>', 'refine style <name>', 'list styles', or hands over raw vertical footage plus a style name."
metadata:
  version: 1.0.0
  last_updated: 2026-10-17
---

# Frame Pilot

Raw vertical talking-head video + a style name in, a postable 1080x1920 MP4 out. Every visual decision comes from the style guide, so the same style looks the same across videos.

`SKILL_DIR` = the folder this file is in. All commands below run `python3 $SKILL_DIR/scripts/reel.py ...` (shown as `reel.py`).

## Pick the mode from the request

| Request | Mode | Read |
|---|---|---|
| `list styles` | List | Run `reel.py styles`, print the table, stop |
| `create style <name>` + reference videos / own videos / notes | Create | `references/create-style.md` |
| `refine style <name>` + feedback | Refine | `references/create-style.md` § Refine |
| raw video + style name (nothing else) | Edit | `references/edit.md` |

Unknown style name in Edit mode: list the available styles (`reel.py styles`) and stop.

## Requirements (check once per session, before the first job)

- `ffmpeg`, `ffprobe`, `node`, `python3` on PATH. Missing: stop and say what to install (`brew install ffmpeg node`).
- `remotion/node_modules` exists. If not: `cd $SKILL_DIR/remotion && npm install`.
- `DEEPGRAM_API_KEY` and `BRAVE_API_KEY` in the process environment or the `env` block of `config.local.json` in this folder (legacy `~/.claude/settings.json` is also supported). Never ask for or write keys in chat; if missing, tell the user to add them. No Brave key: skip real-world images and fall back to graphics.
- Music/SFX libraries: `reel.py lib-check`. Empty libraries don't block an edit: render without music/SFX and say so in the delivery summary.

## Layout

```
SKILL.md
references/   create-style.md, edit.md, style-schema.md (style + beat-plan format)
presets/      clean-minimal, bold-energy, tech-explainer   (shipped, read-only unless asked)
styles/       user styles (same format as presets)
music/ sfx/   audio files + dictionary.json each
remotion/     the Remotion project (components read everything from the style)
scripts/      reel.py (every pipeline step)
jobs/<id>/    one folder per edit; every stage writes here
```

## Ground rules

- **Edit mode never asks questions** except one batched message for essential assets that can't be fetched automatically (see edit.md Stage 5). No "should I proceed", no approvals between stages.
- **The style guide is the authority.** Fonts, colours, layouts, frequencies, caption treatment, SFX density all come from it. If the style can't express something the video needs, use the closest allowed option and note it in the summary, then suggest a refinement.
- **Locked styles** (`"locked": true`) change only on an explicit request to edit that style.
- **Never invent facts.** Stats and numbers on screen come only from what's said in the video.
- **Every stage writes to the job folder**, so any stage can be re-run alone (e.g. tweak `beat-plan.json`, then re-run `render` and `verify`).
- Errors from `reel.py` print `ERROR:` and `FIX:` lines. Relay both to the user and stop that stage.
