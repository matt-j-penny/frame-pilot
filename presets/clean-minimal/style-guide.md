# Clean Minimal

## Summary
Calm, premium, educational. Off-white surfaces, near-black type, one blue accent. Lots of plain talking head; graphics are sparse, small and purposeful. The look of a thoughtful creator explaining an idea. Preset, not built from references.

## Fonts
- Heading: Inter 800, 92px, tracking -1.5 (OFL, assets/fonts/Inter.ttf, variable)
- Caption: Inter 700, 62px, sentence case
- Label: Inter 500, 40px
Source: Google Fonts (google/fonts repo), SIL Open Font License.

## Colours
| Role | Hex |
|---|---|
| primary | #1F6FEB |
| secondary | #E8EEF7 |
| accent | #1F6FEB |
| text | #111111 |
| muted | #5B6472 |
| highlight | #1F6FEB |
| background | #F6F5F2 |
Caption text is white with a soft shadow over footage; the active word turns pale blue (#9CC3FF).

## Background
Flat #F6F5F2 with a very faint top-to-bottom warm gradient. Shows behind fullscreen graphics and the graphic half of split screens. No textures.

## Layouts & frequency
- Talking head: 60%. The default. Every point is made on camera first.
- Talking head + overlay card: 15%. A small card at the top for a name, a term, a logo.
- Split (speaker top, 55%): 15%. When something has to be shown: a list, a screenshot, a comparison.
- Fullscreen graphic: 10%. One or two key moments only: the core stat or the core idea.
Rules: never two fullscreen beats in a row. Never a graphic in the first 1.5s. Go back to talking head after every graphic beat.

## Pacing
- Average beat 3.5s; nothing static longer than 6s.
- Punch-in (1.08x, eased slow push) about every 8s on talking-head beats, alternating 1.0 / 1.08.
- Animations are quick and soft: 9 frames in, 6 out, gentle spring (damping 18).

## Motion graphics
Types: text (40%), list (20%), stat (15%), icon (10%), logo (10%), compare (5%). Generous spacing, centred, no more than ~8 words in a heading. Entrance: scale from 0.88 + fade; exit: fade. List items stagger in, synced across the beat.

## Subtitles
Always on. Phrase mode, 4 words per line, sentence case, Inter 700 62px, white, soft drop shadow, no stroke. The active word turns #9CC3FF. Emphasis words (1-2 per beat max: numbers, the key noun) in #9CC3FF too. Position: 70% height on talking head and overlay, 47% (on the footage, just above the split line) on split, 74% on fullscreen (below the graphic, above the IG UI).

## Images & real-world assets
Logos and screenshots sit on white cards: radius 28, shadow `0 18px 50px rgba(17,17,17,0.12)`, 1px #E4E2DC border. Logos padded and centred; screenshots top-aligned, cropped to fit. Never full-bleed photos.

## Transitions
Mostly hard cuts. `zoom` only on the beat after the hook. No whips.

## Audio
Music: calm, lo-fi, acoustic or soft piano, low energy. Music 0.10, ducked to 0.05 under speech. SFX sparse (about 1 per 10s): a soft pop on graphic entrances, a light whoosh on fullscreen entrances. Never on captions. Target -14 LUFS.

## Hook (0-3s)
Talking head, 1.08 punch-in from frame 0, captions on, the most important 1-2 words emphasised. No graphic until the hook line ends.

## Ending
Last beat: talking head returning to 1.0 scale, captions on. If there's a CTA, a small overlay text card ("Follow for part 2"). Music fades over the final 1.2s.

## Do / Don't
Do: leave whitespace; keep one idea per graphic; use real logos; keep the face visible most of the time.
Don't: use more than 2 colours in a graphic; stack graphics back to back; use emoji; caption in ALL CAPS; put SFX on every cut.

## Machine block
```json reel-style
{
  "name": "clean-minimal",
  "description": "Calm, premium, sparse graphics, off-white + blue",
  "locked": false,
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "safe_zone": {"top": 220, "bottom": 420, "right": 130},
  "fonts": {
    "heading": {"family": "Inter", "file": "fonts/Inter.ttf", "weight": 800, "size": 92, "letter_spacing": -1.5},
    "caption": {"family": "Inter", "file": "fonts/Inter.ttf", "weight": 700, "size": 62},
    "label": {"family": "Inter", "file": "fonts/Inter.ttf", "weight": 500, "size": 40}
  },
  "colors": {"primary": "#1F6FEB", "secondary": "#E8EEF7", "accent": "#1F6FEB", "text": "#111111", "muted": "#5B6472", "highlight": "#1F6FEB", "background": "#F6F5F2"},
  "background": {"color": "#F6F5F2", "css": "linear-gradient(180deg, #FAF9F6 0%, #F1EFEA 100%)", "file": null},
  "layouts": {"talking_head": 0.6, "overlay": 0.15, "split": 0.15, "fullscreen": 0.1},
  "split": {"speaker": "top", "ratio": 0.55, "face_y": 0.32, "divider": null},
  "pacing": {"avg_beat_s": 3.5, "max_static_s": 6, "punch_in_every_s": 8, "punch_in_scale": 1.08, "punch_style": "ease", "anim_in_frames": 9, "anim_out_frames": 6},
  "motion": {"entrance": "scale", "exit": "fade", "stagger_frames": 5, "spring_damping": 18},
  "cards": {"background": "#FFFFFF", "text": "#111111", "radius": 28, "shadow": "0 18px 50px rgba(17,17,17,0.12)", "border": "1px solid #E4E2DC", "padding": 40},
  "captions": {
    "enabled": true, "mode": "phrase", "words_per_line": 4, "uppercase": false, "color": "#FFFFFF",
    "y": {"talking_head": 0.70, "overlay": 0.70, "split": 0.47, "fullscreen": 0.74},
    "highlight": {"type": "color", "color": "#9CC3FF"},
    "emphasis_color": "#9CC3FF", "emphasis_scale": 1.0,
    "stroke": null, "shadow": "0 3px 14px rgba(0,0,0,0.55)", "pop_frames": 5
  },
  "transitions": {"allowed": ["cut", "zoom"], "duration_frames": 8},
  "graphics": {"allowed": ["text", "list", "stat", "icon", "logo", "compare", "screenshot", "image"], "weights": {"text": 0.4, "list": 0.2, "stat": 0.15, "icon": 0.1, "logo": 0.1, "compare": 0.05}},
  "audio": {"music_moods": ["calm", "lofi", "acoustic", "piano"], "music_volume": 0.10, "duck_volume": 0.05, "sfx_volume": 0.25, "sfx_per_10s": 1,
            "sfx_events": {"graphic_in": ["pop", "soft"], "fullscreen_in": ["whoosh", "soft"]}, "lufs": -14, "music_fade_out_s": 1.2}
}
```

## Changelog
- 2026-10-17: Preset created.
