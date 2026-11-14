---
name: effects
description: Add any of 90 video effects to a talking-head video (orbit, spotlight, glass widgets, timeline, checklist, headline wall, comment box, phone fan, liquid glass graph, match-cut, iPhone toggles, LED sign, over-the-shoulder zoom, iMessage pop-ups, place-in-grid and more). Effects track the speaker's face and can sit behind their head. Use when the user types /effects, names one of the effects, or asks to add an effect, zoom, grade, sticker or animation to their video.
---

# Effects: 90 video effects (51 by @vibha.in.progress, 39 added for Applied AI Mastermind)

The user is usually not technical. Keep replies short and friendly, do the work for them, and never ask them to run commands themselves.

All paths below are relative to this skill's folder (the folder this SKILL.md is in). Use its absolute path in commands.

## 1. First run: set up (once)
Run `bash scripts/setup.sh`. It prints `READY` when done (the first time takes 1 to 3 minutes).
- `NEED_FFMPEG`: install it for them. On a Mac: `brew install ffmpeg` (if `brew` is missing, tell them to install Homebrew from brew.sh first). On Windows: `winget install ffmpeg`.
- `NEED_PYTHON`: install Python 3.12 (Mac: `brew install python@3.12`, Windows: `winget install Python.Python.3.12`), then run setup again.
- On Windows, the Python is at `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## 2. Get the video and the effect
- Video: the user drags the file into the chat, or gives a path. A vertical phone video works best.
- Effect: from `/effects <name>`, or from what they describe. Match their words to the table below. Unsure? Show them the list.

## 3. Find the timing
- If they say "on the word X" or "when I say ...", run `.venv/bin/python scripts/words.py <video>` and use those times.
- If they give no timing, apply the effect for the whole clip, or ask which part (one short question).
- Short windows look best: 1.5 to 4 seconds per effect.

## 4. Draft, check, render
1. Write the plan next to their video as `<video-name>_effects.json`:
   ```json
   {"effects": [
     {"fx": "orbit", "start": 3.2, "end": 6.0},
     {"fx": "backdrop-word", "start": 14.0, "end": 16.3, "text": "CLAUDE"}
   ]}
   ```
2. Check frames first (fast): `.venv/bin/python scripts/fx.py --plan <plan.json> <video> <folder>/check.png --still 4.5,15.2`, using the middle of each effect. Look at the PNGs yourself. Fix the text, timing or options if something looks off (covers the face, cut off by the edge, unreadable).
3. Render: `.venv/bin/python scripts/fx.py --plan <plan.json> <video> <video-name>_effects.mp4`. The output keeps their original audio. It renders at 1080p by default; add `--width 2160` for 4K (slower).
4. Tell them where the file is. Remind them in one line to watch it before posting: it drafts, they approve.

A single effect needs no plan: `.venv/bin/python scripts/fx.py orbit <video> <out.mp4> --start 3 --end 6 --text "..." --opt key=value`.

## The 90 effects
| # | `fx` name | What it does | Options (all optional) |
|---|---|---|---|
| 1 | `noise` | Reels pile up behind your head, one every quarter second | `images` (folder of screenshots or clips), `size` |
| 2 | `lineup` | Numbered tiles fan out in an arc above your head | `text` (tile names joined with `\|`) |
| 3 | `locked-on` | Corner brackets snap onto your face, the camera follows you | `zoom` (default 1.35), `text` (tag) |
| 4 | `orbit` | Your reels circle your head: in front at the bottom, behind at the top | `images`, `count`, `speed`, `size` |
| 5 | `lean-in` | A fast punch-in on one word | `zoom` (default 1.45, max 2), `speed` |
| 6 | `backdrop-word` | A giant word drops in behind you | `text`, `color` (hex), `font` (`bold` or `serif`) |
| 7 | `spotlight` | Kills the lights, keeps you lit | `text` (glowing word behind you), `color`, `push` |
| 8 | `the-bill` | Prints your instructions like a receipt into the wall above your head | `text` (lines joined with `\|`) |
| 9 | `moody` | A moody colour grade | `grade` (`moody`, `bw`, `warm`, `cool`, `pop`) |
| 10 | `swipe` | A before and after slider sweeps across you | `grade` (the "after" look) |
| 11 | `todo` | A checklist card beside your head ticks off as you talk | `text` (items with `\|`), `ticks` (video seconds with `\|`), `title` |
| 12 | `comment-box` | An Instagram comment bar types a word and posts it | `text` (default EFFECTS) |
| 13 | `tap` | A Follow button pops up and flips to Following | `at` (video second of the flip), `x`, `y` (0 to 1), `color` |
| 14 | `pause-point` | Freezes the frame and points at you with a hand-drawn arrow | `text` (label), `color`, `label_x` |
| 15 | `uninstall` | A glitchy uninstall bar breaks the frame apart | `text` |
| 16 | `reel-frame` | Your video shrinks into an Instagram reel card | `text` (handle) |
| 17 | `shortcut-rain` | Keyboard keys rain down behind you | `text` (keys with `\|`), `count` |
| 18 | `reject-stamp` | A big red stamp slams onto the screen | `text`, `color`, `angle`, `y` |
| 19 | `countdown-flip` | A 3, 2, 1 flip clock above your head | `from` |
| 20 | `rabbit-hole` | The frame tunnels into itself, spinning | `ratio`, `speed`, `spin` |
| 21 | `cover-star` | You become a magazine cover, title behind your head | `text` (title), `lines` (with `\|`), `issue`, `color` |
| 22 | `scribble` | Marker doodles draw themselves around you | `text` (label), `color` |
| 23 | `glass-widgets` | Frosted glass widgets and mini artifacts float around your head, plus an Edited by Claude pill | `text` (big number), `name`, `handle`, `look` (`simple` for the 3-widget version) |
| 24 | `red-collage` | Black and white you, a giant red word behind, three lines slam in | `text` (red word), `lines` (with `\|`), `tag` |
| 25 | `split-headline` | A headline card slides down and pushes you to the bottom half | `text` (lines with `\|`), `hl` (highlighted word), `pill` |
| 26 | `pastel-word` | Lavender room, giant word behind you, a profile card gets followed | `text`, `name`, `handle` |
| 27 | `check-pills` | Grid-paper room, reel boards behind you, a cursor clicks blue pills | `text` (pills with `\|`), `images` |
| 28 | `timeline` | A dark red film grade with an editing timeline, a REC timecode and a glowing playhead | `text` (title), `sub`, `tc` |
| 29 | `headline-box` | A punch-in with a two-line headline, the second line in a white box | `text` (lines with `\|`), `zoom` |
| 30 | `profile-wall` | Your reels grid fills the wall behind you while a counter ticks up | `images`, `count`, `label` |
| 31 | `tier-list` | A tier list drops in and Claude flies into S tier | `title`, `item`, `others` |
| 32 | `broll-split` | B-roll on top with a price-tag sticker, you below | `images`, `text` (tag) |
| 33 | `phone-fan` | Your reels fan out like a hand of phones under a headline | `images`, `text` (lines with `\|`) |
| 34 | `dot-reveal` | Your shot builds out of glowing dots, then snaps to the full picture | `color`, `cell` |
| 35 | `headline-wall` | Your own headlines pile up behind your head, then a total pops in front | `text` (`headline::meta\|...`), `total`, `label` |
| 36 | `checklist` | A Claude task list under your chin: each step spins, then ticks green | `text` (`step::meta\|...`), `title` |
| 37 | `liquid-glass-graph` | A liquid glass card under your chin: a green graph climbs while the number counts up | `text` (label), `from`, `to` (e.g. `197K`, `59%`), `color` |
| 38 | `carousel-spin` | Your reels spin around you in a 3D carousel, then slow to a stop | `images`, `count`, `size`, `turns` |
| 39 | `match-cut` | News pages cut on one word, locked in a red box behind your head | `text` (the word, default Claude), `color` |
| 40 | `apple-toggles` | An iPhone settings card under your chin flips its switches on, one line at a time | `text` (rows with `\|`), `ticks` (seconds with `\|`), `color` |
| 41 | `led-sign` | The lights drop and a glowing LED sign types itself out behind you | `text` (lines with `\|`), `color`, `push` |
| 42 | `slow-push` | A slow cinematic push-in to your face while the room melts out of focus | `zoom` (default 1.6), `blur` |
| 43 | `over-the-shoulder-zoom` | The camera pushes into one top corner and a see-through liquid glass graph pops beside your head (line climbs, number counts up), pulls back, then the other corner with a second, related bar graph. Your head stays in front | `text` (two labels with `\|`), `to` (two numbers with `\|`, e.g. `197K\|672K`), `zoom` (default 2.0) |
| 44 | `messages` | iMessage notifications pop in one after another, creamy glass with a soft glow, stacking up above the bottom of the frame | `text` (messages with `\|`), `title` (default Messages), `y` |
| 45 | `place-in-grid` | You shrink into the centre tile of your 3x3 profile grid on frosted glass, then 8 reels pop in around you, one per frame, with Instagram view counts on every tile | `images` (folder of your reels or covers), `views` (9 counts with `\|`, the 9th is yours) |
| 46 | `tape-label` | A level strip of yellow tape with your line lands on your chest, kept off your face | `text` |
| 47 | `select-resize` | A blue selection box with handles grabs your number above your head and a cursor drags it bigger | `text` (default 2X) |
| 48 | `wave-trim` | A dark panel above your head shows your voice; the red dotted silence on both ends collapses until only your words are left | none |
| 49 | `huge-strike` | One huge serif word wipes in behind your head, then a red line crosses it out | `text`, `at` (seconds into the effect when the strike lands, default 0.6) |
| 50 | `crayon-write` | A red crayon writes your word behind your head, then underlines it and flies off | `text` |
| 51 | `fan-build` | Your reel covers deal into a fan behind your head, one card at a time | `images` (folder of your covers), `count` (default 13) |
| 52 | `outline-glow` | A glowing purple outline draws itself around you and pulses | `color` |
| 53 | `lower-third` | Your name and title wipe in at the bottom corner | `text` (name), `role`, `y` (0 to 1) |
| 54 | `big-stat` | A huge number counts up with a label and a hand-drawn underline | `to` (the number, e.g. `3.2M`), `text` (label) |
| 55 | `step-tracker` | A step card: "Step 2 of 4", the step title and a progress bar that fills | `step`, `of`, `text` (title) |
| 56 | `search-type` | A search bar types your question, then the cursor clicks it | `text` (the query) |
| 57 | `quote-card` | A pull-quote card: big quote mark, your line typed word by word, your name | `text` (the quote), `by` |
| 58 | `chapter-title` | A chapter card: a big purple number, a line that wipes in and the chapter title | `n` (number), `text` (title), `label` |
| 59 | `versus` | Two cards face off either side of a VS badge, then the winner lights up | `text` (A\|B), `win` (1 or 2) |
| 60 | `pros-cons` | A two-column card: green ticks for the pros, red crosses for the cons, one row at a time | `pros`, `cons` (items joined with `\|`) |
| 61 | `roadmap` | A timeline of steps: the line fills left to right and each stop lights up with its label | `text` (stops joined with `\|`) |
| 62 | `price-drop` | The old price gets struck out in red and the new price slams in | `from`, `to`, `text` (label) |
| 63 | `bar-compare` | Two bars race: the long grey before against the short purple after | `text` (rows of `label::value::length`, joined with `\|`) |
| 64 | `prompt-box` | An AI chat box types your prompt, then the send button fires | `text` (prompt), `model` |
| 65 | `terminal` | A terminal window types your command and prints green ticks as each step finishes | `text` (command), `lines` (joined with `\|`), `title` |
| 66 | `comment-cta` | A call to action: Comment the keyword and I'll send it, with a bouncing arrow | `text` (keyword), `pre`, `post` |
| 67 | `myth-fact` | A MYTH card in red flips over to become the FACT in green | `myth`, `fact` |
| 68 | `ticker` | 16:9 only. A news ticker slides up from the bottom and scrolls your headlines non-stop | `text` (headlines joined with `\|`), `tag` (default LIVE), `y` |
| 69 | `reactions` | 9:16 only. Live-stream reactions: hearts and emojis bubble up the side of the frame, swaying as they rise | `emoji` (joined with `\|`), `count` (default 18) |
| 70 | `stat-row` | Three numbers count up side by side on one card, each with its label | `text` (`value::label`, up to three, joined with `\|`) |
| 71 | `chat-reply` | Your prompt goes up as a chat bubble, the AI thinks for a beat, then its answer streams in underneath | `text` (prompt), `reply`, `model` |
| 72 | `numbered-list` | A titled list that reveals one numbered point at a time, the current one lit and the earlier ones dimmed | `title`, `text` (points joined with `\|`) |
| 73 | `post-card` | A social post card with your face, name and handle: the post writes itself, then the likes count up | `text`, `likes`, `name`, `handle` |
| 74 | `bar-chart` | A bar chart: your bars grow one after another, each with its value, the last one in purple | `title`, `text` (`label::value`, up to six, joined with `\|`) |
| 75 | `do-dont` | Two stacked cards: the DON'T with a red cross, then the DO with a green tick, and the DON'T fades back | `dont`, `do`, `at` (seconds until the DO appears) |
| 76 | `rating-stars` | A review card: five stars light up one after another as the score counts up, with the number of reviews underneath | `to` (score out of 5), `text` (label) |
| 77 | `plan-card` | A pricing card: the plan name, the price, what is included ticking in line by line, and a button | `name`, `price`, `per`, `text` (features joined with `\|`), `cta` |
| 78 | `zoom-stat` | The camera pushes in and moves you to one side, and a stat badge counts up in the space it opened | `to`, `text` (label) |
| 79 | `zoom-bullets` | The camera pushes in and moves you aside, then a headline and three points appear one by one in the space | `title`, `text` (points joined with `\|`) |
| 80 | `chest-number` | One giant number counts up across your chest in front of you, with a big label under it | `to`, `text` (label) |
| 81 | `behind-icons-path` | Two thick 3D emoji tiles sit behind your shoulders and a dotted path draws over your head from one to the other | `emoji` (two, joined with `\|`), `text` (two labels) |
| 82 | `behind-chart` | A tilted purple graph panel hangs in 3D behind your shoulder while a smooth curve draws upward and its value counts | `title`, `text` (`label::value`, joined with `\|`) |
| 83 | `icon-cluster` | Seven different emoji tiles drift in behind you from one side at different sizes, with your line on a pill | `emoji` (up to seven, joined with `\|`), `text` |
| 84 | `perspective-wall` | A wall of your keywords on tiles runs off into the distance behind you and slides slowly past | `text` (words joined with `\|`) |
| 85 | `card-stack` | Your points on a stack of cards tilted in 3D: the top card slides away to show the next | `text` (points joined with `\|`) |
| 86 | `cube-points` | A 3D block turns a quarter turn for each of your points, one face per point | `text` (points joined with `\|`) |
| 87 | `carousel-cards` | Your keywords on cards circle your head in 3D: across your chest in front, behind your head at the back | `text` (words joined with `\|`) |
| 88 | `tilt-screen` | A screen tilted in 3D shows your own dashboard: three numbers counting up over a row of rising bars | `title`, `text` (`label::value`, three, joined with `\|`) |
| 89 | `three-pillars` | A dark full-screen hook: a glowing number, a headline, and three numbered pillars that rise and light up one by one | `to` (number), `text` (headline), `pillars` (joined with `\|`) |
| 90 | `glass-notes-split` | You shrink into a rounded frame while a notes panel opens beside you and ticks off your points | `title`, `text` (points joined with `\|`) |

**Named looks** (same effect, a fancier look; they don't add to the count):
- `glitter-spotlight` = `spotlight` with `look=sparkle`: the room goes dark, golden rays burst from behind your head, a big gold word with a shine sweep, twinkling sparkles and a glow around you. `text` (the word), `color`, `push`.
- `cover-star` with `look=editorial`: a soft warm film look, a classic serif masthead behind your head, an issue line and elegant cover lines. `text` (masthead), `issue`, `lines` (3 lines with `\|`), `right` (lines with `\|`), `color`, `accent`, `lines_y`, `right_y`.
- `liquid-glass-graph` with `look=bento`: the climbing graph moves to a smoked glass screen behind your head, with glass bento tiles in front of you (a donut, a KPI, bars). `text`, `from`, `to`, `donut` (`29%::label`), `kpi` (`672K::label`), `bars` (`197\|140\|124::label`).
- `apple-toggles` now sits above you, tucked behind your head, with a gentle zoom (`pos=below` for the old under-the-chin card; `overlap`, `zoom`).

Aliases work too: `bill`, `to-do`, `follow`, `stamp`, `countdown`, `cover`, `rain`, `pause`.

## Rules
- Never cover the face. Everything either goes behind the person or avoids the face by itself; if a check frame still shows text over the face, move it (`x`, `y`) or shorten the text.
- Effects run in the order listed. Put camera effects (`locked-on`, `lean-in`, `spotlight`) first when they overlap others.
- Zoom never goes past 2x, so the video stays sharp.
- This skill adds visuals only. Sound effects and captions are up to the user (CapCut works well).
- These are starter versions. Be honest about that if the user compares them to a reel they saw.
