import { useMemo } from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Beat, Style, Word } from "./types";

export const beatAt = (beats: Beat[], t: number) => {
  let i = beats.findIndex((b) => t >= b.start && t < b.end);
  if (i < 0) i = t < beats[0].start ? 0 : beats.length - 1;
  return i;
};

const norm = (w: string) => w.toLowerCase().replace(/[^a-z0-9']/g, "");

type Group = { words: Word[]; start: number; until: number };

const groupWords = (words: Word[], perLine: number, cuts: number[] = []): Group[] => {
  const groups: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    const prev = words[i - 1];
    const onCut = cuts.some((t) => Math.abs(w.start - t) < 0.03);
    if (cur.length && (cur.length >= perLine || onCut || /[.?!,]$/.test(prev.word) || w.start - prev.end > 0.6)) {
      groups.push(cur);
      cur = [];
    }
    cur.push(w);
  });
  if (cur.length) groups.push(cur);
  return groups.map((g, i) => ({
    words: g, start: g[0].start,
    until: Math.min(groups[i + 1]?.[0].start ?? Infinity, g[g.length - 1].end + 0.5),
  }));
};

export const Captions: React.FC<{ words: Word[]; beats: Beat[]; style: Style }> = ({ words, beats, style }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const c = style.captions;
  const groups = useMemo(() => groupWords(words, c.words_per_line, c.break_on_beats ? beats.map((b) => b.start) : []), [words, beats, c.words_per_line, c.break_on_beats]);
  if (!c.enabled || !words.length) return null;
  const t = frame / fps;
  const beat = beats[beatAt(beats, t)];
  if (beat.captions === false) return null;
  const g = groups.find((x) => t >= x.start && t < x.until);
  if (!g) return null;
  const emphasis = new Set((beat.emphasis ?? []).map(norm));
  const activeIdx = g.words.reduce((acc, w, i) => (w.start <= t ? i : acc), -1);
  const pop = c.pop_frames === 0 ? 1 : spring({ frame: frame - Math.round(g.start * fps), fps, config: { damping: 14 }, durationInFrames: c.pop_frames ?? 6 });
  const f = style.fonts.caption;
  const safe = style.safe_zone ?? { top: 220, bottom: 420, right: 130 };

  const box = c.box;
  return (
    <div style={{
      position: "absolute", left: 80, width: W - 80 - safe.right, top: c.y[beat.layout] * H,
      transform: `translateY(-50%) scale(${0.85 + 0.15 * pop})`, display: "flex", justifyContent: "center",
    }}>
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
    {beat.emoji && (
      <div style={{ fontSize: f.size * 1.5, lineHeight: 1, padding: f.size * 0.3, marginBottom: f.size * 0.35, borderRadius: f.size * 0.5,
        background: "rgba(255,255,255,0.92)", boxShadow: "0 10px 30px rgba(0,0,0,0.35)", fontFamily: "Apple Color Emoji, Noto Color Emoji, sans-serif",
        transform: `scale(${0.4 + 0.6 * pop})`, opacity: pop }}>{beat.emoji}</div>
    )}
    <div style={{
      display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: f.size * 0.28, rowGap: f.size * 0.1,
      background: box?.color, borderRadius: box?.radius, padding: box ? `${box.padding_y}px ${box.padding_x}px` : undefined,
    }}>
      {g.words.map((w, i) => {
        const active = i === activeIdx;
        const emph = emphasis.has(norm(w.word));
        const hl = c.highlight;
        const text = (c.uppercase ? w.word.toUpperCase() : w.word).replace(/[,.]$/, "");
        let color = emph ? c.emphasis_color : c.color;
        let scale = emph ? c.emphasis_scale ?? 1 : 1;
        let bg: string | undefined;
        if (active && hl.type === "color") color = hl.color;
        if (active && hl.type === "scale") { color = hl.color; scale = hl.scale ?? 1.12; }
        if (active && hl.type === "box") { bg = hl.box_color; color = hl.color; }
        return (
          <span key={w.i} style={{
            fontFamily: f.family, fontWeight: f.weight, fontSize: f.size, letterSpacing: f.letter_spacing ?? 0, lineHeight: 1.1,
            color, background: bg, borderRadius: bg ? f.size * 0.18 : 0, padding: bg ? `0 ${f.size * 0.16}px` : 0,
            margin: bg ? `0 -${f.size * 0.16}px` : 0,
            transform: `scale(${scale})`, display: "inline-block",
            opacity: c.mode === "word" && w.start > t ? 0 : 1,
            WebkitTextStroke: c.stroke ? `${c.stroke.width}px ${c.stroke.color}` : undefined, paintOrder: "stroke fill",
            textShadow: c.shadow ?? undefined,
            borderBottom: active && hl.type === "underline" ? `${Math.round(f.size * 0.08)}px solid ${hl.color}` : undefined,
          }}>
            {text}
          </span>
        );
      })}
    </div>
    </div>
    </div>
  );
};
