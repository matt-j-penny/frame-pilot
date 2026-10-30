# Reference analysis checklist

Answer every question below for **each** reference video, then once more for the set as a whole (what's consistent, what varies). Write the answers to `styles/<name>/references/analysis.md`, one section per reference plus a "Across all references" section. Every answer needs evidence (timestamps or a measurement), not an impression. Write "not present" rather than skipping a question.

## 1. Composition
1. **Shot types**: which appear, with % of runtime each: talking head, motion graphics, still images, B-roll video, screenshots, screen recordings.
2. **Arrangement**: how they're laid out on screen: full frame, split (which half is the speaker, ratio), picture-in-picture, overlay card, collage.
3. **Does the layout change** through the video? (yes/no)
4. **When** does it change: list the timestamps and what triggers each change (new point, product name, number, list, the turn, the CTA).
5. **How often**: number of layout changes, average seconds between changes, longest stretch with no change.
6. **Talking head**: is a human on screen? How much of the frame do they fill (face width as % of frame), and where does the face sit vertically?
7. **Framing**: how tight is the shot (head only, head and shoulders, chest up, waist up)? Is the speaker centred or offset? Does the framing change between full-frame and split layouts?

## 2. Editing rhythm
8. **Pauses between words**: inside a sentence, how much gap is left between words (measure from the word timestamps: typical and maximum, in seconds)? Are natural breaths kept or removed?
9. **Pauses between sentences**: how much gap is left between the end of one sentence and the start of the next (typical and maximum)? Is it tighter than natural speech, i.e. are silences cut hard?
10. **Punch-ins**: how often (per 10 seconds), and how big (scale, e.g. 1.1x, 1.25x)? Are they fast (hard cut, instant) or slow (gradual push over the shot)? Do they land on emphasis words, new sentences, or at random? Do they ever zoom back out?

## 3. Audio
11. **Music**: present? Genre, energy, tempo feel; does it change or drop out; how loud relative to the voice.
12. **Sound effects**: present? List each type (whoosh, pop, click, ding, riser…) with the event it marks and how many per 10 seconds.

## 4. Motion graphics
13. **Present?** Yes/no, and % of runtime they're on screen.
14. **Text density**: how text-heavy are they: mostly words (kinetic type, titles), mixed, or mostly visual (UI, icons, illustrations)? Typical words per graphic.
15. **Code-drawn vs real assets**: are they purely drawn (shapes, type, UI built in code), or do they include icons, logos, photos, screenshots? Rough split.
16. **Flat vs depth**: flat 2D, soft depth (shadows, layering, blur), or strongly dimensional?
17. **3D**: is anything truly 3D (rotating objects, perspective cameras, three.js-style scenes)? Describe it.
18. **Detail level**: basic (single shapes, plain text) or premium (layered cards, gradients, glows, textures, micro-animation, cursor movement)? Give 2-3 concrete details that make it feel that way.
19. **Where in the video**: which moments get graphics: the hook, every point, numbers, product mentions, lists, the CTA? Which moments are deliberately left as plain talking head?
20. **How they animate**: entrance and exit (pop, slide, fade, scale, mask, typewriter), speed in frames, easing (springy vs smooth), stagger, and whether something keeps moving while on screen.
21. **What they focus on**: the subject matter they illustrate: products/UI, data and numbers, concepts, step-by-step processes, social proof, pain points.
22. **Icon style**: what icons look like: outline or filled, line weight, rounded or sharp, flat colour, gradient, emoji, 3D-rendered, or brand logos. Do they sit in shapes (circles, rounded squares)?
23. **Annotations**: are there arrows, circles, underlines, highlighter marks, boxes, or a moving cursor/pointer drawing attention to parts of a graphic or screenshot? How do they animate on (draw-on, pop, slide)?
24. **Durations**: how long each graphic stays on screen (typical, shortest, longest, in seconds), and how many graphics appear per 10 seconds.

## 5. Real-world media
25. **Screenshots**: used? Of what (websites, apps, reviews, tweets)? How framed (cards, device frames, shadows, cropping)?
26. **Screen recordings (video)**: used? Of what? How long, and how framed?

## 6. Look
27. **Primary colour**: hex, and where it's used.
28. **Accent colour**: hex, and where it's used (highlights, key words, buttons).
29. **Fonts**: family (or closest match), weight, and case for headings, captions and labels.
30. **Background**: what's behind graphics: flat colour, gradient, texture, grid, image, video. Does it change between scenes?

## 7. Subtitles
31. **Present?** Always, sometimes (when not), or never.
32. **Colour**: text colour, active-word colour, any box/pill colour and opacity, outline and shadow.
33. **Position**: vertical position per layout (as % of frame height), and whether it moves between layouts.
34. **Size**: cap height or font size relative to frame width; words per line; max lines.
35. **Animation and effects**: how lines/words appear (word-by-word, phrase, typewriter, pop), active-word highlight (colour, box, scale, underline), emphasis on key words, outline, shadow, blur or glow.
36. **Emoji and wording**: do captions include emoji? Do they show every word or only keywords? Is punctuation kept? How are lines broken (by phrase, by word count)?
37. **Captions with graphics**: when a graphic is on screen, are captions hidden, moved, or layered over it? Do captions ever repeat text the graphic already shows?

## Things the editor can't reproduce yet

Record these honestly in the style guide's "Gaps" section with the nearest fallback the editor *can* do:
- **3D motion graphics**: the renderer is 2D. Fallback: layered cards with shadows and parallax-style motion.
- **Screen recordings**: not captured automatically yet. Fallback: real screenshots in device/browser frames with cursor-style animation.
- **B-roll video**: no stock-footage source yet. Fallback: still images or a motion graphic for the beat.
