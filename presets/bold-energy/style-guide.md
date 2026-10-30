# Bold Energy

## Summary
High-energy, retention-first. Huge uppercase word-by-word captions with a black stroke, yellow active word, constant punch-ins, fast graphic hits and dense SFX. Business/money/motivation content. Preset, not built from references.

## Fonts
- Heading: Montserrat 900, 104px, uppercase, tracking -1 (OFL, assets/fonts/Montserrat.ttf, variable)
- Caption: Montserrat 900, 84px, uppercase
- Label: Montserrat 700, 42px, uppercase, tracking 1
Source: Google Fonts (google/fonts repo), SIL Open Font License.

## Colours
| Role | Hex |
|---|---|
| primary | #FFD60A |
| secondary | #FF3B30 |
| accent | #FFD60A |
| text | #FFFFFF |
| muted | #C9C9C9 |
| highlight | #FFD60A |
| background | #0B0B0B |
Emphasis words (money, numbers, negatives) go #3DDC84 green; a negative word may use #FF3B30.

## Background
Near-black #0B0B0B with a subtle centre vignette. Behind fullscreen graphics and the graphic half of splits.

## Layouts & frequency
- Talking head: 50%. Always punched in or punching; never a flat 1.0 for more than one beat.
- Overlay card: 20%. Icons, logos, short text hits at the top while the speaker keeps talking.
- Fullscreen graphic: 20%. Stat hits, big text slams, lists. Short (1.2-2.5s).
- Split (speaker top, 55%): 10%. Screenshots and compares.
Rules: something changes on screen at least every 2.5s (punch-in, graphic, caption emphasis). Fullscreen beats are short; return to the face fast.

## Pacing
- Average beat 2.2s; nothing static longer than 3s.
- Punch-ins are hard cuts, alternating 1.0 / 1.15 / 1.25 on consecutive talking-head beats.
- Animations snap: 6 frames in, 4 out, punchy spring (damping 11).

## Motion graphics
Types: text (30%), stat (25%), icon (20%), list (10%), logo (10%), compare (5%). Text slams use 2-4 words with one *accent* word. Stats always count up. Entrance: pop (scale from 0.55, overshoot); exit: scale down + fade.

## Subtitles
Always on. Word-by-word (words appear as spoken), 2 words per line, UPPERCASE Montserrat 900 84px, white with 10px black stroke and hard shadow. The active word turns #FFD60A and scales 1.12. Emphasis words (1-3 per beat) #3DDC84 at 1.1x. Position: 66% height on talking head/overlay, 47% on split, 74% on fullscreen.

## Images & real-world assets
Logos on white rounded cards (radius 24) with heavy shadow. Screenshots on cards, cropped to the relevant part. Overlay cards are white with black text.

## Transitions
Cuts by default, `zoom` on most fullscreen exits back to the face, `whip` at most twice per video on topic changes.

## Audio
Music: upbeat, driving, hip-hop/trap or electronic, high energy. Music 0.14, ducked to 0.07 under speech. SFX dense (about 3 per 10s): whoosh on fullscreen entrances and whips, pop on overlay/icon entrances, ding/cash on stats and money words, click on list items. Target -14 LUFS.

## Hook (0-3s)
Frame 0 is already at 1.15 punch-in, word-by-word captions on the first word, an emphasised keyword. If the first line has a number or a bold claim, follow it immediately (around 1.5s) with a fullscreen text or stat slam with a whoosh.

## Ending
Last beat punches to 1.25 for the final line. CTA as an overlay text card ("FOLLOW FOR MORE") with a pop. Music cuts off with the last word (0.4s fade), loop-friendly.

## Do / Don't
Do: keep it moving; emphasise numbers and money; hit SFX on every graphic entrance; keep the face big.
Don't: put more than 4 words in a text slam; use sentence-case captions; leave a beat flat; let the music compete with the voice; use soft/fade-only entrances.

## Machine block
```json reel-style
{
  "name": "bold-energy",
  "description": "High-energy word-by-word captions, punch-ins, dense SFX",
  "locked": false,
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "safe_zone": {"top": 220, "bottom": 420, "right": 130},
  "fonts": {
    "heading": {"family": "Montserrat", "file": "fonts/Montserrat.ttf", "weight": 900, "size": 104, "letter_spacing": -1, "uppercase": true},
    "caption": {"family": "Montserrat", "file": "fonts/Montserrat.ttf", "weight": 900, "size": 84},
    "label": {"family": "Montserrat", "file": "fonts/Montserrat.ttf", "weight": 700, "size": 42, "letter_spacing": 1, "uppercase": true}
  },
  "colors": {"primary": "#FFD60A", "secondary": "#FF3B30", "accent": "#FFD60A", "text": "#FFFFFF", "muted": "#C9C9C9", "highlight": "#FFD60A", "background": "#0B0B0B"},
  "background": {"color": "#0B0B0B", "css": "radial-gradient(ellipse at 50% 45%, #1C1C1C 0%, #0B0B0B 70%)", "file": null},
  "layouts": {"talking_head": 0.5, "overlay": 0.2, "fullscreen": 0.2, "split": 0.1},
  "split": {"speaker": "top", "ratio": 0.55, "face_y": 0.3, "divider": "#FFD60A"},
  "pacing": {"avg_beat_s": 2.2, "max_static_s": 3, "punch_in_every_s": 2.5, "punch_in_scale": 1.15, "punch_style": "cut", "anim_in_frames": 6, "anim_out_frames": 4},
  "motion": {"entrance": "pop", "exit": "scale", "stagger_frames": 4, "spring_damping": 11},
  "cards": {"background": "#FFFFFF", "text": "#0B0B0B", "radius": 24, "shadow": "0 24px 60px rgba(0,0,0,0.6)", "border": "none", "padding": 36},
  "captions": {
    "enabled": true, "mode": "word", "words_per_line": 2, "uppercase": true, "color": "#FFFFFF",
    "y": {"talking_head": 0.66, "overlay": 0.66, "split": 0.47, "fullscreen": 0.74},
    "highlight": {"type": "scale", "color": "#FFD60A", "scale": 1.12},
    "emphasis_color": "#3DDC84", "emphasis_scale": 1.1,
    "stroke": {"width": 10, "color": "#000000"}, "shadow": "0 6px 0 rgba(0,0,0,0.85)", "pop_frames": 4
  },
  "transitions": {"allowed": ["cut", "zoom", "whip"], "duration_frames": 6},
  "graphics": {"allowed": ["text", "stat", "icon", "list", "logo", "compare", "screenshot", "image"], "weights": {"text": 0.3, "stat": 0.25, "icon": 0.2, "list": 0.1, "logo": 0.1, "compare": 0.05}},
  "audio": {"music_moods": ["upbeat", "driving", "hiphop", "trap", "electronic"], "music_volume": 0.14, "duck_volume": 0.07, "sfx_volume": 0.4, "sfx_per_10s": 3,
            "sfx_events": {"fullscreen_in": ["whoosh"], "graphic_in": ["pop"], "stat": ["ding", "cash", "riser"], "list_item": ["click"], "whip": ["whoosh", "swish"]}, "lufs": -14, "music_fade_out_s": 0.4}
}
```

## Changelog
- 2026-10-17: Preset created.
