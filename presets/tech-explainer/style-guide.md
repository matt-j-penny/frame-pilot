# Tech Explainer

## Summary
Dark, precise, "AI/tech creator" look. Deep navy grid background, violet + cyan accents, lots of split screen with real logos, product screenshots and stat callouts. Monospace labels give it a technical edge. Preset, not built from references.

## Fonts
- Heading: Space Grotesk 700, 88px, tracking -1 (OFL, assets/fonts/SpaceGrotesk.ttf, variable 300-700)
- Caption: Inter 800, 60px (OFL, assets/fonts/Inter.ttf)
- Label: JetBrains Mono 500, 34px, uppercase, tracking 2 (OFL, assets/fonts/JetBrainsMono.ttf)
Source: Google Fonts (google/fonts repo), SIL Open Font License.

## Colours
| Role | Hex |
|---|---|
| primary | #7C5CFF |
| secondary | #141B2D |
| accent | #22D3EE |
| text | #F5F7FF |
| muted | #8A93A8 |
| highlight | #7C5CFF |
| background | #0A0F1C |

## Background
#0A0F1C with a violet glow at the top and a faint 60px grid (CSS, no file). Behind fullscreen graphics and the graphic half of splits.

## Layouts & frequency
- Split (speaker top, 50%, cyan divider): 35%. The workhorse: any time a tool, product, logo, screenshot, number or list is mentioned.
- Talking head: 35%. Opinions, stories, the hook and the ending.
- Fullscreen graphic: 15%. Key stat, comparison, or the core list.
- Overlay card: 15%. Tool name + logo, a short term definition.
Rules: when a named product/company is mentioned, show its real logo (overlay or split). Never invent stats; only numbers that are said.

## Pacing
- Average beat 2.8s; nothing static longer than 4s.
- Punch-ins (1.1x, hard cut) about every 5s on talking-head beats.
- Animations crisp: 8 frames in, 5 out, slide-up with a controlled spring (damping 15).

## Motion graphics
Types: logo (20%), screenshot (15%), stat (20%), list (15%), compare (10%), text (10%), icon (10%). Headings use one *accent* (cyan) word. Labels in mono uppercase. Entrance: slide up 90px + fade; exit: fade.

## Subtitles
Always on. Phrase mode, 3 words per line, sentence case, Inter 800 60px, white. The active word sits in a violet (#7C5CFF) rounded box with white text. Emphasis words (product names, numbers) in cyan #22D3EE. Position: 68% on talking head/overlay, 44% (on the footage, above the divider) on split, 74% on fullscreen.

## Images & real-world assets
Logos on dark cards (#141B2D, 1px #26304A border, radius 24, deep shadow), centred with padding. Screenshots on the same card, cropped from the top, never stretched. Prefer official transparent PNG/SVG logos.

## Transitions
Cuts, `slide` into fullscreen graphics, `zoom` back to the face after a fullscreen beat. No whips.

## Audio
Music: modern electronic, minimal tech, synthwave-lite, medium energy. Music 0.12, ducked to 0.06 under speech. SFX moderate (about 2 per 10s): whoosh on fullscreen/slide entrances, click/tick on list items and screenshot entrances, subtle digital blip on stats. Target -14 LUFS.

## Hook (0-3s)
Talking head at 1.1 punch-in with the hook line captioned. If the hook names a product, split to its logo at about 1.5s.

## Ending
Talking head, 1.0, final line captioned; optional overlay CTA card ("Follow for more AI tools") in the dark card style. 1s music fade.

## Do / Don't
Do: show real logos and real UI; keep labels mono and uppercase; use cyan sparingly (one accent per graphic).
Don't: use stock photos of robots/brains; use more than 3 list items on a split; put light cards on the dark background; put SFX on captions.

## Machine block
```json reel-style
{
  "name": "tech-explainer",
  "description": "Dark grid, violet/cyan, split screens with logos and screenshots",
  "locked": false,
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "safe_zone": {"top": 220, "bottom": 420, "right": 130},
  "fonts": {
    "heading": {"family": "Space Grotesk", "file": "fonts/SpaceGrotesk.ttf", "weight": 700, "size": 88, "letter_spacing": -1, "weight_range": "300 700"},
    "caption": {"family": "Inter", "file": "fonts/Inter.ttf", "weight": 800, "size": 60},
    "label": {"family": "JetBrains Mono", "file": "fonts/JetBrainsMono.ttf", "weight": 500, "size": 34, "letter_spacing": 2, "uppercase": true, "weight_range": "100 800"}
  },
  "colors": {"primary": "#7C5CFF", "secondary": "#141B2D", "accent": "#22D3EE", "text": "#F5F7FF", "muted": "#8A93A8", "highlight": "#7C5CFF", "background": "#0A0F1C"},
  "background": {"color": "#0A0F1C", "css": "radial-gradient(ellipse at 50% 0%, rgba(124,92,255,0.35) 0%, rgba(10,15,28,0) 60%), linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)", "size": "100% 100%, 60px 60px, 60px 60px", "file": null},
  "layouts": {"split": 0.35, "talking_head": 0.35, "fullscreen": 0.15, "overlay": 0.15},
  "split": {"speaker": "top", "ratio": 0.5, "face_y": 0.3, "divider": "#22D3EE"},
  "pacing": {"avg_beat_s": 2.8, "max_static_s": 4, "punch_in_every_s": 5, "punch_in_scale": 1.1, "punch_style": "cut", "anim_in_frames": 8, "anim_out_frames": 5},
  "motion": {"entrance": "slide-up", "exit": "fade", "stagger_frames": 5, "spring_damping": 15},
  "cards": {"background": "#141B2D", "text": "#F5F7FF", "radius": 24, "shadow": "0 24px 70px rgba(0,0,0,0.55)", "border": "1px solid #26304A", "padding": 38},
  "captions": {
    "enabled": true, "mode": "phrase", "words_per_line": 3, "uppercase": false, "color": "#FFFFFF",
    "y": {"talking_head": 0.68, "overlay": 0.68, "split": 0.44, "fullscreen": 0.74},
    "highlight": {"type": "box", "color": "#FFFFFF", "box_color": "#7C5CFF"},
    "emphasis_color": "#22D3EE", "emphasis_scale": 1.0,
    "stroke": null, "shadow": "0 4px 16px rgba(0,0,0,0.6)", "pop_frames": 5
  },
  "transitions": {"allowed": ["cut", "slide", "zoom"], "duration_frames": 7},
  "graphics": {"allowed": ["logo", "screenshot", "stat", "list", "compare", "text", "icon", "image"], "weights": {"logo": 0.2, "screenshot": 0.15, "stat": 0.2, "list": 0.15, "compare": 0.1, "text": 0.1, "icon": 0.1}},
  "audio": {"music_moods": ["electronic", "tech", "minimal", "synthwave"], "music_volume": 0.12, "duck_volume": 0.06, "sfx_volume": 0.3, "sfx_per_10s": 2,
            "sfx_events": {"fullscreen_in": ["whoosh"], "graphic_in": ["click", "tick"], "list_item": ["click", "tick"], "stat": ["blip", "digital"]}, "lufs": -14, "music_fade_out_s": 1}
}
```

## Changelog
- 2026-10-17: Preset created.
