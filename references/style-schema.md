# Style guide format

Every style is a folder: `styles/<name>/` (user styles) or `presets/<name>/` (shipped).

```
<name>/
  style-guide.md      prose rules + one ```json reel-style block + changelog
  assets/             fonts/, background files, style-specific logos. Copied to the job as public/style/
  references/         reference videos, links.md, frame sheets used to build it
```

`style-guide.md` has these sections, in this order. Prose sections are rules the beat planner (you) follows; the JSON block is what the Remotion components read. Both must agree.

1. **Summary**: 2-3 sentences on the feel, plus who/what it was built from.
2. **Fonts**: family, weight, size for heading, caption, label, with the source/licence.
3. **Colours**: every hex value and its role.
4. **Background**: colour, CSS gradient, or file, and where it shows (behind fullscreen graphics and the graphic half of split screens).
5. **Layouts & frequency**: shot types used (talking head, graphics, stills, B-roll, screenshots, screen recordings) and % of runtime each; how they're arranged; % of runtime per layout; when and how often the layout changes; how big the speaker is in frame; and the rules for when each layout is used.
6. **Pacing**: gaps kept between words and between sentences (typical and max, in seconds; this sets the rough-cut gap threshold), speaker framing, average beat length, max seconds without a visual change, punch-ins (how often, how big, fast cut or slow push, what they land on), animation speed.
7. **Motion graphics**: which graphic types are used and how often; their character: text density (words per graphic), code-drawn vs real assets, flat vs depth, any 3D, detail level (basic vs premium, with the concrete details), icon style, annotations (arrows, circles, highlights, cursors) and how they draw on; how long each graphic stays up and how many per 10 seconds; which moments get graphics and which stay plain; what subjects they illustrate; entrance/exit, easing, durations, and what keeps moving while on screen.
8. **Subtitles**: on/off (and when hidden), colour (text, active word, box/pill, outline, shadow), size, position per layout, words per line, word-by-word or phrase, entrance animation and effects, active-word highlight, emphasis rules, emoji, every word vs keywords only, punctuation and line breaks, and what captions do when a graphic is on screen.
9. **Images & real-world assets**: when logos, photos, screenshots and screen recordings are used, of what, and how they're framed.
10. **Transitions**: which ones, and when.
11. **Audio**: music mood/genre, music level vs voice, SFX density, and which events get which SFX tags.
12. **Hook (0-3s)**: what the first beat must look like.
13. **Ending**: last beat, CTA treatment, loop-friendliness.
14. **Do / Don't**: explicit lists.
15. **Learned rules** (added by the app): rules learned from approved edits, each citing the video it came from. They override older rules above where they conflict.
15b. **Gaps**: anything in the references the editor can't reproduce yet (e.g. 3D graphics, screen recordings, B-roll) and the fallback used instead.
16. **Machine block**: the ```json reel-style block, described below.
17. **Changelog**: dated bullet per change, newest first.

The answers to `analysis-checklist.md` are kept in `references/analysis.md` next to the guide, as the evidence it was built from.

Also in the style folder, managed by the app's approve flow:
- `examples/<job-id>/`: approved edits (`beat-plan.json`, `notes.md`, `poster.jpg`) plus `examples/index.json`. Edit mode reads the newest three before planning.
- `learning.json`: approvals (with how many changes each needed) and "watch for it" observations with counts.
- `history/`: a copy of `style-guide.md` before every change (hand edits, Ask-Claude changes, applied lessons), restorable from the Style Editor.

## The `reel-style` JSON block

`reel.py style-check <name>` validates it. All sizes are px on a 1080x1920 canvas.

| Key | Meaning |
|---|---|
| `name`, `description` | Shown by `reel.py styles` |
| `locked` | `true` = only change on explicit request |
| `canvas` | `{width, height, fps}`, normally 1080/1920/30 |
| `safe_zone` | `{top, bottom, right}` px Instagram UI covers. Default 220/420/130 |
| `fonts.heading/caption/label` | `{family, file (relative to assets/), weight, size, weight_range?, letter_spacing?, uppercase?}`. `weight_range` defaults to `"100 900"` (right for variable fonts; set the real range if narrower) |
| `colors` | `primary, secondary, accent, text, highlight, background, muted` hex. Text on backgrounds uses `text`; the stat value and `*accent*` words use `accent` |
| `background` | `{color, css?, size?, file?, opacity?}`. `css` is a CSS `background-image` value (gradients, grids), `size` its `background-size`. `file` is an image or video in assets/ |
| `layouts` | Fractions of runtime: `talking_head, split, fullscreen, overlay`; must sum to 1. 0 = layout banned |
| `split` | `{speaker: "top"/"bottom", ratio (speaker share of height), face_y (0-1 vertical focus of the face in the crop), divider (CSS colour or null)}` |
| `pacing` | `{avg_beat_s, max_static_s, punch_in_every_s, punch_in_scale, punch_style: "cut"/"ease", anim_in_frames, anim_out_frames}` |
| `motion` | `{entrance: "pop"/"slide-up"/"fade"/"scale", exit: "fade"/"scale"/"slide-down", stagger_frames, spring_damping}` |
| `cards` | Framing for overlay cards, logos, screenshots, compare: `{background, text, radius, shadow, border, padding}` |
| `captions` | `{enabled, mode: "word"/"phrase", words_per_line, uppercase, color, y: {talking_head, split, fullscreen, overlay} (0-1 vertical centre), highlight: {type: "color"/"box"/"scale"/"underline", color, box_color?, scale?}, emphasis_color, emphasis_scale?, stroke?: {width, color}, shadow?, pop_frames?}` |
| `backgrounds` | named variants `{color, css?, size?, file?, shader?, shader_colors?}`, picked per beat with `"bg"`. `shader`: `aurora` / `silk` (fragment shaders) or `glass` (three.js scene); `shader_colors` = `[base, a, b, highlight]` |
| `detail` | `{float_px, grain}`: idle float on every graphic, film grain on WebGL backgrounds |
| `transitions` | `{allowed: [...], duration_frames}`. Types: `cut, zoom, slide, whip` |
| `graphics` | `{allowed: [...], weights: {type: share}}`: which graphic types this style uses, and how often |
| `audio` | `{music_moods: [...], music_volume, duck_volume (music level under speech, 0-1), sfx_volume, sfx_per_10s, sfx_events: {event: [dictionary tags]}, lufs, music_fade_out_s}` |

`pacing.avg_beat_s`, `punch_in_every_s`, `transitions.allowed`, `graphics` and `audio.sfx_*` drive planning, not rendering. Everything else is read by the components.

## Beat plan (`jobs/<id>/beat-plan.json`)

Times are seconds on the **cut** timeline (`transcript-cut.json`). Beats must tile 0 → duration with no gaps.

```json
{
  "music": {"file": "track.mp3", "volume": 0.14},
  "beats": [
    {"id": 1, "start": 0, "end": 2.4, "text": "...", "layout": "talking_head", "zoom": 1.12,
     "transition": "cut", "emphasis": ["money"], "captions": true,
     "sfx": [{"file": "pop_01.wav", "at": 0.9, "volume": 0.3}]},
    {"id": 2, "start": 2.4, "end": 5.1, "text": "...", "layout": "split",
     "graphic": {"type": "stat", "value": "73%", "label": "of creators quit in year one"}}
  ]
}
```

Graphic types and fields:

| type | fields |
|---|---|
| `text` | `title` (`*word*` = accent colour), `subtitle?` |
| `stat` | `value` (numbers count up, keeps prefix/suffix), `label` |
| `list` | `title?`, `items` (staggered across the first 60% of the beat) |
| `logo` | `src` (`assets/<file>`), `label?` |
| `image` / `screenshot` | `src`, `caption?`; screenshot also `scroll?: [from, to]` (0-1, pans a tall full-page capture inside a browser window over the beat) `url?` (address bar text); a screenshot `src` ending in .mp4/.mov/.webm plays a screen recording in the window from `from?` seconds; `zoom?: [a, b]` scales the content around `origin?` (CSS, e.g. `"80% 70%"`) over the beat; `fill: true` on a fullscreen beat plays the recording full-bleed with no frame (add `fit: "width"` for a landscape clip shown full width above the captions, pushing in over `zoom`) |
| `icon` | `icon` (lucide-react PascalCase name, e.g. `Rocket`, `Brain`, `DollarSign`), `title`, `subtitle?` |
| `quote` | `text`, `author?` |
| `compare` | `left: {label, value?}`, `right: {label, value?}` |
| `videogrid` | `clips: [{src, from}]` (2-column grid of playing video tiles, staggered pop-in; 4 fits the split top) |
| `repo` | `repo` ("owner/name"), `items` (file names, `dir/` for folders), `subtitle` (commit message), `marks: [list, highlight last file, cursor stars repo]` (seconds from beat start). GitHub-style repo page |
| `editor` | `src` (preview video, e.g. `cut.mp4`), `from` (its start seconds), `items` (5 step labels), `title`, `marks: [silences, bad take, graphics, sfx, music, done]`. Editor window whose timeline is cut in sync with the voice; fullscreen hero |
| `desktop` | `src` (file thumbnail image), `label` (file name), `text` (typed prompt), `items` (progress steps), `marks: [drag, drop, type start, type end, enter, reply]`. Drag a file into Claude, type, send, steps tick, result card; fullscreen hero |
| `comment` | `text` (comment typed), `marks: [type start, type end, post, arrow]`. Social comment composer |
| `badge` | `icon` (lucide name), `title`, `subtitle` (mono chip). App-icon badge, use as an `overlay` with `position: "top"` |
| `code` | `items` (code lines, syntax-coloured automatically), `title` (file tab), `label` (agent name), `marks: [typing end]`. Light code editor the AI writes at speed: ghost text ahead, agent caret + name tag, diff gutter, minimap |
| `role` | `title` (role), `subtitle` (eyebrow), `icon`, `color` (icon tile), `items` (tasks), `icons` (task icons), `stamp` (text), `tone` (stamp colour), `marks: [stamp, flip row 1, flip row 2, ...]`. Job card slams in, each task flips Human -> AI on its mark (rows without a mark show "Working"), then an ink stamp slams on with shake and shards; fullscreen |
| `queue` | `title` (header), `icon`/`color` (row 1 tile), `items` (row 1 shown; later rows stay redacted, their word lengths set the bars), `marks: [row 1 done, focus moves to row 2]`. "Who's next" list: row 1 ticks Done and strikes through, the focus ring moves to the locked "Next" row |
| `timeline` | `clips: [{src}]` (thumbnail stills), `src`/`from` (program-monitor video, e.g. `cut.mp4`), `title`, `label` (agent), `marks: [cursor lands, cut 1, cut 2, ...]`. NLE timeline the AI cursor flies into and razor-cuts; header pill flips "Editing: you" -> agent |
| `template` | `src` (`assets/tpl-<name>.mov` from `reel.py template-render`). A pre-rendered HyperFrames template played full canvas with its alpha and SFX; see "HyperFrames templates" in `references/edit.md` |

Overlay graphics also take `position: "top" | "center"`, `y` (0-1 top edge) and `align: "left" | "right"` (horizontal placement, e.g. beside a centred speaker on 16:9). Overlay and fullscreen graphics take `scale` (size multiplier, e.g. 1.5 for UI cards on a 1920x1080 canvas). Set `captions: false` on a beat whose graphic already shows the same words. `enter: false` on a graphic skips its entrance (use on the hook so frame 0 is already fully drawn).

Beat plan extras: an SFX entry takes `dur` (seconds; trims a long hit or tail with a short fade). `music` takes `from` (start offset in the track, e.g. to land a downbeat on the first word).

Job-level `style.json` knobs (not needed in saved styles): `transitions.fade_frames: 0` makes cuts into fullscreen graphics hard cuts (default fades over `anim_in_frames`), and scenes then skip the wrapper fade too; `captions.break_on_beats: true` starts a new caption phrase at every beat boundary. Snap beat boundaries to frames (`k/fps - 0.0001`) so the first and last frame of every beat are drawn.

Need a graphic the library can't draw? Add a new `type` to `remotion/src/Graphic.tsx` (styled only from `style`), document it here, and add it to `GRAPHICS` in `scripts/reel.py`. Then every style can use it.

## Music / SFX dictionaries

`music/dictionary.json` and `sfx/dictionary.json` are arrays, one entry per file in that folder:

```json
{"file": "whoosh_02.wav", "duration": 0.8, "tags": ["whoosh", "fast"], "mood": "airy, quick", "energy": "high",
 "use": "fullscreen graphic entrances and whip transitions"}
```

Music entries also have `tempo` (BPM or slow/medium/fast). `tags` are what styles' `audio.sfx_events` match against, so use the common words: `whoosh, swish, pop, click, tick, ding, cash, riser, blip, digital, soft, impact`.

`reel.py lib-import <folder> music|sfx` copies files in and adds stub entries (file + duration). Then fill `tags/mood/energy/use` from the filenames and by listening/asking the user. `reel.py lib-check` lists undescribed or missing files. Only use licensed files the user owns or has rights to.
