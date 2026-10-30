# Create / refine a style

A style guide is what makes edits consistent and good. Spend the effort here. Format: `style-schema.md`.

## Create: `create style <name>`

Inputs (any combination): reference reels the user likes, the user's own past edits, written notes, or "start from preset X".

1. **Set up**: `styles/<name>/` with `assets/fonts/`, `references/`. Name in kebab-case. If the name exists, ask whether to refine it instead.
2. **Collect references**: local files go into `references/` (copy). For URLs, download with `yt-dlp` if installed (`yt-dlp -f "bv*[height<=1920]+ba/b" -o "references/%(id)s.%(ext)s" <url>`), otherwise ask the user for the files. List them in `references/links.md` with their source.
3. **Analyse each reference**:
   - `reel.py frames <video> styles/<name>/references/<ref-id>/ --every 0.5` gives contact sheets (8 frames each) plus `sheets.json` mapping sheets to timestamps. Read every sheet.
   - Transcribe it for pacing: extract audio and run the same Deepgram call as `reel.py transcribe` (or create a scratch job with `reel.py ingest <ref> clean-minimal` + `transcribe` and read `transcript.json`), then measure words per caption line, average shot/beat length, and where graphics land relative to speech.
   - Shot/beat changes: `ffmpeg -i <ref> -vf "select='gt(scene,0.25)',showinfo" -f null - 2>&1 | grep pts_time` gives cut times, so you can work out average shot length and layout-change rate.
   - For each reference, note: layout per segment (talking head / split / fullscreen / overlay) with time ranges, caption style (font look, case, size relative to frame width, words per line, highlight method, position), colours (sample from frames; give hex), graphic types and how they enter/exit, punch-in frequency and scale, transitions, background treatment, hook (first 3s) and ending.
   - Audio: music genre/energy, music level relative to voice (`ffmpeg -i <ref> -af ebur128 -f null -` for overall loudness), SFX events and frequency.
   - **Answer every question in `references/analysis-checklist.md`** for each reference, with timestamps or measurements as evidence, and write the answers to `styles/<name>/references/analysis.md`. Don't start writing the guide until every question has an answer (or "not present").
4. **Merge into one guide**: what's consistent across references becomes a rule; what varies becomes a range or a frequency. Compute the layout percentages from your time ranges. Write every section in `style-schema.md` order with exact values: no "large font", but "Montserrat 900, 84px". Every checklist answer must land somewhere in the guide; anything the editor can't reproduce goes in the "Gaps" section with its fallback.
5. **Fonts**: identify the closest match. Use an open-licence font from Google Fonts (`https://github.com/google/fonts/raw/main/ofl/<family>/<File>.ttf`, variable files have `%5Bwght%5D` in the name) into `assets/fonts/`, or the user's own font file. Record source and licence.
6. **Ask once** for what can't be detected reliably, as a single batched question (AskUserQuestion when available): exact brand fonts (offer your best match as the default), exact hex colours (offer the sampled ones), a background asset or texture, the music mood if references disagree, and anything they explicitly dislike. Apply the answers.
7. **Write the machine block** to match the prose exactly, then `reel.py style-check <name>` until it passes.
8. **Test**: if the user gave a raw test video, run the full edit on it now (`references/edit.md`), show the result, and start the refine loop. Otherwise tell them the style is ready and to send a test video.

## Refine: `refine style <name>` + feedback

1. If the style is locked and the request isn't explicitly about changing it, confirm first.
2. Translate each piece of feedback into exact value changes ("captions too big" → `captions` font size 84 → 70, and update the prose). Change the prose section and the machine block together.
3. Add a dated changelog entry: what changed, why (quote the feedback), old → new values.
4. `reel.py style-check <name>`.
5. Re-run the edit on the last test video. Jobs are re-runnable: copy the latest job's `beat-plan.json` approach, re-ingest the same source with the updated style, and re-plan, so the change is visible. Show the new render.
6. Repeat until the user is happy.

## Lock

When the user says they're happy ("lock it", "that's the one"): set `"locked": true`, add a changelog entry "Locked". Locked styles are used as-is by Edit mode and only change on an explicit refine request.

## Presets

`presets/` ships `clean-minimal`, `bold-energy`, `tech-explainer`. A preset can be used directly by name, or copied into `styles/<name>/` as a starting point ("create style <name> from bold-energy") and refined from there. Don't modify presets in place unless the user asks.
