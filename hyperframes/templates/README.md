# HyperFrames Templates

Reusable HyperFrames composition references live here.

Use this folder when you want to start from an existing visual pattern instead of rebuilding layout, animation, and styling from scratch.

## How This Folder Works

- `templates.json` is the index of available templates.
- Each template is a single `.html` file — open it to read the composition code and comments.
- Copy the HTML into a new HyperFrames project folder, replace the placeholder content, and build from there.

## How To Use A Template

1. Open `templates.json` and pick the template that matches the video you want to make.
2. Open the corresponding `.html` file and read the `<!-- REPLACE -->` comments to understand what to swap out.
3. Copy the file into your new project folder as `index.html`.
4. Replace placeholder text, media sources, and timing values.
5. Run `npx hyperframes lint` after editing.

## Current Templates

- `glass-video-split.html` — fullscreen recording intro/outro with a glassmorphic notes panel and animated vertical video layout.
- `lower-third-video-overlay.html` — fullscreen source video with a single-line animated lower-third title over a dark bottom gradient.
- `lower-third-two-line-word-by-word.html` — overlay-only two-line lower third where words animate in one at a time; line 1 Satoshi (off-white), line 2 Kaushan Script (purple accent).
- `lower-third-purple-glow-hook-9x16.html` — portrait talking-head lower third with a small white setup line and a purple gradient/glow hero word.
- `stacked-headline-impact-bar-9x16.html` — 9:16 split layout with a reference-inspired stacked social hook and oversized impact bar over the classic off-white dot grid, with talking-head video below.
- `talking-head-zoom-bullets-9x16.html` — 9:16 split layout with a dark-on-light bullet-point graphic over the classic dot grid in the top half and an independently clipped talking head below.
- `screenshot-two-line-overlay.html` — static white-grid composition with a large screenshot and a two-line white/purple headline layered over it.
