# Edit a video

Run every stage in order, without stopping. Each stage's output is on disk in the job folder.

## Stage 1: Ingest

```bash
reel.py ingest <video> <style>
```

Validates the file (readable, video + audio streams, resolution/fps/duration), resolves the style (`styles/` first, then `presets/`), validates its machine block and font/background files, creates `jobs/<id>/` and copies the style's assets to `public/style/`. Prints the job path; use it for every later command. Unknown style: it prints what's available and exits; relay that and stop.

Then read the style's `style-guide.md` in full. It is the spec for Stages 4-9.

## Stage 2: Transcribe

```bash
reel.py transcribe <job>
```

Deepgram nova-2 with word timestamps and `filler_words=true` (fillers must be kept in the transcript so they can be cut). Writes `transcript.json` (`{i, word, start, end, conf}` per word).

## Stage 3: Rough cut

1. `reel.py sentences <job>` prints every sentence with word indices and flags:
   - `RETAKE? -> sN(ratio)`: a later sentence is similar, so this one is probably an earlier take.
   - `TRAILS OFF`: no end punctuation, probably abandoned.
   - `LOWCONF word@i`: mumbled/garbled words.
2. Decide what to remove. Read the sentences as an editor would:
   - **Retakes**: when two sentences say the same thing, keep the **last** complete one and cut the earlier one(s). Partial restarts count ("So the best— So the best way to...").
   - **Incomplete sentences**: abandoned lines, cut unless the next sentence depends on them.
   - **Garbled words**: low-confidence words followed by a redo, cut the garbled part.
   - **Explicit flags**: "let me say that again", "cut that", "one more time", cut the flag and the take it refers to.
   - Keep anything that's a deliberate repetition for emphasis.
3. Write `<job>/cuts.json`, inclusive word-index ranges:
   ```json
   [{"from": 12, "to": 27, "reason": "retake of s4"}, {"from": 40, "to": 41, "reason": "garbled, redone"}]
   ```
   Write `[]` if nothing needs cutting.
4. `reel.py cut <job>` (default `--gap 0.4 --pad 0.12`; use the style's value if it sets one). Fillers are removed automatically. Pauses longer than the gap are trimmed, keeping `pad` either side, and every cut lands on a word boundary (it never cuts inside a word or into a neighbouring removed word). The voice is levelled with `speechnorm`, and the result is scaled/cropped to the canvas.

   Writes `edl.json`, `transcript-cut.json` (re-timed words), `cut-log.md` (every removal and why) and `public/cut.mp4`.
5. Read `cut-log.md`. If anything important was cut by mistake, fix `cuts.json` and re-run `cut`.

## Stage 4: Beat plan

Write `<job>/beat-plan.json` (format in `style-schema.md` § Beat plan) from `transcript-cut.json` and the style guide.

0. **Learn from approved edits first.** The style folder is `style_dir` in `job.json`. If it has `examples/index.json`, read the 3 most recent examples listed there: each `examples/<id>/notes.md` (what the user asked to change before approving) and `beat-plan.json` (the plan they approved). Match their choices where the content is comparable: layout mix, which moments got graphics, graphic types, punch-in rhythm, caption handling. Also follow the style guide's "Learned rules" section. The style guide still wins where an example contradicts it (the guide may have been updated since).

1. **Split into beats**: sentence or phrase level, aiming for the style's `pacing.avg_beat_s`. Long sentences split at commas/clauses. Beats must tile 0 → cut duration exactly (next `start` = previous `end`; first starts at 0, last ends at the duration). Snap boundaries to word starts.
2. **Pick a layout per beat** following the style's prose rules first, then its frequencies. Tally runtime per layout as you go and keep each within about ±8% of `layouts`. The hook and ending follow the style's Hook/Ending sections exactly.
3. **Pick the visual** for every non-talking-head beat, from the style's `graphics.allowed` and roughly its `weights`:
   - A named product/company/tool → `logo` (real logo, Stage 5).
   - A website, app or UI being described → `screenshot`.
   - A number said aloud → `stat` (exactly the number said).
   - 2-4 parallel points → `list` (items = short versions of what's said, spanning the beat).
   - X vs Y → `compare`. A memorable line → `quote` or `text`. An abstract concept → `icon` or `text`.
   - Only use a graphic when there's something genuinely showable. Otherwise it's a talking-head beat.
4. **Punch-ins**: on talking-head beats, roughly every `pacing.punch_in_every_s`, with `zoom` set to `punch_in_scale` (alternate with 1.0 so it reads as a change).
5. **Transitions**: only types in `transitions.allowed`, used where the style's Transitions section says.
6. **Captions & emphasis**: `emphasis` is 1-3 words per beat that carry the meaning (numbers, key nouns, contrast words), within the style's emphasis rules. Set `captions: false` only when the graphic shows the same words and the style allows it.
7. **SFX**: place from `sfx/dictionary.json` by matching `tags` to the style's `audio.sfx_events` (graphic entrances at the beat start, list items at their stagger times, stats at the count-up, whips/transitions at the cut). Stay at or below `audio.sfx_per_10s`. `at` is absolute seconds on the cut timeline. Never put SFX on plain caption changes.
8. **Music**: one track from `music/dictionary.json` whose mood/energy matches the style's `music_moods` and the content. Longer than the video is ideal; shorter loops automatically. No suitable track or empty library: omit `music` and note it.
9. Self-check before writing: layout share per layout, longest stretch without a visual change (≤ `pacing.max_static_s`), no two fullscreen beats in a row unless the style allows it, every `src` you plan to use is listed for Stage 5.

## Stage 5: Assets

For every `logo`, `image` and `screenshot` beat:

- **Logos / photos**: `reel.py search "<brand> logo png transparent"`. Pick the highest-resolution clean result (official site, Wikimedia, brand press kits; transparent PNG or SVG preferred; no watermarks, no mockups). `reel.py fetch <job> <url> <name>` saves to `public/assets/` and logs the source URL in `sources.json`. Set the beat's `src` to the returned path. If the result is low-res or wrong, try the next one.
- **Screenshots of a public page**: `reel.py shot <job> <url> <name>` (headless Chrome, 1080x1350 default). For pages that need interaction or a login, use the Playwright MCP (`browser_take_screenshot` with a filename inside `public/assets/`). Check the screenshot with Read before using it; cookie banners or blank pages don't count.
- **Can't get it automatically**:
  - Essential to the beat (the video is *about* that thing): add it to an ask list.
  - Not essential: change the beat to a `text`/`icon` graphic or talking head, and note it.
- If the ask list isn't empty, send **one** message listing every item: what's needed, which beat/timestamp, and where to drop the file (`<job>/public/assets/<name>`). Wait, then continue. This is the only allowed interruption.

Look at every fetched image (Read it) before it goes in the plan.

## HyperFrames templates

Pre-built HTML motion graphics in `hyperframes/` (index: `hyperframes/templates/templates.json`, plus `captured-templates.json` and the user's own in `custom-templates.json`). Use one when a transcript instruction names a `template` id (required), or when one clearly fits a beat better than a built-in graphic.

1. Map the passage onto the cut timeline (source words -> `edl.json`), then `reel.py template <job> <template-id> <name> <start> <end>` (cut seconds, `name` lowercase-dashes). It copies the template to `hf/<name>/`, bakes that moment of `cut.mp4` in as its footage and writes `TEMPLATE.md`.
2. Edit only the slots `TEMPLATE.md` lists in `hf/<name>/index.html`: the copy (from the instruction, or the spoken words when it's empty), and entrance/exit timing so everything is out by the end. Keep its structure, CSS and GSAP.
3. `reel.py template-render <job> <name>` renders `public/assets/tpl-<name>.mov` (alpha kept, includes the template's own SFX).
4. In `beat-plan.json`, make a beat spanning exactly `<start>`-`<end>` with `"graphic": {"type": "template", "src": "assets/tpl-<name>.mov"}`. Layout `overlay` when the template sits over the speaker (lower thirds, hooks, captions), `fullscreen` when it fills the frame. Set `captions: false` when the template already shows the spoken words, and add no extra SFX on it.

Check the beat in the verify sheets like any other: wrong copy or clipped text means editing `index.html` and re-rendering.

## Preview mode (only when the job asks for it)

The user reviews static stills of every beat before anything is rendered. Run Stages 1-5 as normal, then:

1. **Ideas.** With N ideas per beat, give every beat that has a graphic N-1 `alternatives`: genuinely different treatments of the same moment (a different graphic type, layout or angle on the content, not the same card reworded). Each alternative overrides only the fields it changes (`layout`, `graphic`, `zoom`, `transition`, `captions`, `emphasis`, `sfx`), never `id`/`start`/`end`/`text`, and follows the same rules as the beat itself (allowed layouts, real assets fetched in Stage 5, SFX in the library). Give the beat and each alternative a short `label` (2-4 words, e.g. "Stat count-up", "Logo card"). Talking-head beats get none. With N = 1, skip alternatives and just label the graphic beats.
   ```json
   {"id": 2, "start": 1.7, "end": 3.3, "layout": "split", "label": "Bold headline", "graphic": {"type": "text", "title": "..."},
    "alternatives": [{"label": "Stat card", "graphic": {"type": "stat", "value": "100+", "label": "..."}}]}
   ```
2. `reel.py storyboard <job>` validates every idea and renders one still per beat and per idea to `preview/`, plus `preview/preview.json`. Fix any validation error and re-run.
3. Read a few stills to check they look right, then stop with a short summary. Do not render or verify: Frame Pilot shows the storyboard, merges the user's picks into `beat-plan.json` (removing `alternatives`) and then asks you to continue from Stage 6.

`reel.py render` refuses a plan that still has `alternatives`.

## Stage 6-8: Build, audio, render

The Remotion project already has all the components (captions, split, fullscreen, overlay card, logo/screenshot cards, stat, list, icon, quote, compare, punch-ins, transitions, background, music ducking, SFX). They read fonts, colours and timings from `style.json`, and content from the beat plan.

```bash
reel.py render <job> --preview     # optional fast half-res pass for a first look
reel.py render <job>               # full render -> output/raw.mp4 -> loudness-normalised output/final.mp4
```

`render` validates the beat plan first (layouts allowed by the style, beats tile the timeline, assets/music/SFX exist) and refuses with a list of errors. Fix them and re-run.

Audio: the voice is levelled in Stage 3, music is ducked to `duck_volume` under speech and rises to `music_volume` in pauses, SFX at `sfx_volume` (or per-SFX `volume`), music fades out at the end, then a two-pass loudnorm to `audio.lufs` (-14) at -1.5 dBTP.

If the beat plan needs a graphic type that doesn't exist, add it to the component library (see the end of `style-schema.md`). Don't hard-code a one-off.

## Stage 9: Verify (required, max 3 fix loops)

```bash
reel.py verify <job>
```

Checks spec (1080x1920, fps, H.264, duration matches the cut), loudness (integrated within 1.5 LU of target, true peak < -0.5 dBTP), then writes contact sheets to `verify/sheet_NN.png`: 8 frames each, every 1.5s plus the start/middle/end of every beat. Red bands mark the Instagram UI zones (top, bottom, right edge). `verify/report.json` maps each sheet to its timestamps and beats.

Read **every** sheet and check each frame for:
- Captions overlapping a graphic, a card, or the face; text over the face.
- Broken graphics: missing image, text overflowing or cut off, layout collapsed, empty card.
- Important content (captions, headings, logos) inside a red UI band.
- Colours outside the style palette, low contrast, text too small to read on a phone.
- The split layout: face visible and sensibly framed (adjust `split.face_y` in the job's `style.json` if the crop misses the face).
- Caption timing: spot-check captions against `transcript-cut.json` at 3-4 timestamps.

Audio: `auto_issues` covers loudness/clipping. Check the music isn't overpowering by comparing the plan's `music.volume` with the style. If voice clarity is in doubt, lower it.

Fix by editing `beat-plan.json` (or the job's `style.json` for job-only tweaks; never the style guide during an edit), re-render, re-verify. Stop after 3 loops and report what's left.

## Stage 10: Deliver

Reply with:
- The final file path: `jobs/<id>/output/final.mp4`.
- Duration (source → cut), style used, cuts made (segments, fillers, retakes, pauses) from `cut-log.md`.
- Layout mix achieved vs the style's targets, graphics count, music track and SFX count.
- Assets skipped or replaced, assumptions made, and any issue verification couldn't fix.
- If the style itself caused a problem (e.g. captions too big for long words), suggest the refinement.
