import * as Icons from "lucide-react";
import { Easing, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { Graphic, Style } from "./types";

// Hero scenes: realistic product UI that plays out in sync with the voice.
// `marks` are seconds from the beat start at which each phase happens (taken from transcript-cut.json word times).
//   repo:    [list, highlight, star]                         GitHub-style repo page (`repo`, `items` = files, `subtitle` = commit)
//   editor:  [silences, bad take, graphics, sfx, music, done] video editor timeline being cut (`src` = preview video, `from`)
//   desktop: [drag, drop, type start, type end, enter, reply] drag a file into Claude, type, send, steps tick (`label` = file, `text`, `items`)
//   comment: [type start, type end, post, arrow]               social comment composer (`text`)
//   badge:   app-icon badge (`icon`, `title`, `subtitle`)

//   aiedit:  fast montage of an AI cutting a timeline: razor cuts ripple out, graphics/sfx/music drop in, cut counter climbs
//   code:     [typing end]                                     code editor the AI writes at speed (`items` = code lines, `title` = file, `label` = agent)
//   role:     [stamp, flip row 1, flip row 2, ...]             job card whose tasks flip Human -> AI, then `stamp` slams on (`tone` = stamp colour)
//   queue:    [row 1 done, focus moves to row 2]               "who's next" list; only the first of `items` is shown, the rest stay redacted
//   timeline: [cursor lands, cut 1, cut 2, ...]                NLE timeline the AI cursor flies into and razor-cuts (`clips` = stills, `src` = monitor video)

export const SCENE_TYPES = new Set(["repo", "editor", "desktop", "comment", "badge", "aiedit", "code", "role", "queue", "timeline"]);

type IconC = React.FC<{ size: number; color: string; strokeWidth?: number; fill?: string }>;
const icon = (name?: string): IconC => ((Icons as unknown as Record<string, IconC>)[name ?? "Sparkles"] ?? Icons.Sparkles);
const cl = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const out = Easing.bezier(0.22, 1, 0.36, 1);
const inOut = Easing.bezier(0.65, 0, 0.35, 1);

type Ctx = { style: Style; lf: number; dur: number; fps: number; g: Graphic };

const useCtx = (g: Graphic, style: Style, lf: number, dur: number): Ctx & {
  t: number; sp: (atS: number, damping?: number) => number; at: (i: number, fallback: number) => number;
  ramp: (aS: number, bS: number, from?: number, to?: number, e?: (x: number) => number) => number;
  ink: string; muted: string; shadow: string; font: string; body: string; mono: string; accent: string; send: string; ok: string; palette: string[];
} => {
  const { fps } = useVideoConfig();
  const ui = style.ui ?? {};
  return {
    g, style, lf, dur, fps, t: lf / fps,
    sp: (atS, damping = 14) => spring({ frame: lf - Math.round(atS * fps), fps, config: { damping }, durationInFrames: 16 }),
    at: (i, fallback) => g.marks?.[i] ?? fallback,
    ramp: (aS, bS, from = 0, to = 1, e = inOut) => interpolate(lf / fps, [aS, Math.max(aS + 0.001, bS)], [from, to], { ...cl, easing: e }),
    ink: ui.ink ?? style.colors.text, muted: ui.muted ?? style.colors.muted ?? "#6B7280",
    shadow: ui.shadow ?? style.cards.shadow, font: style.fonts.heading.family, body: style.fonts.label.family,
    mono: style.fonts.mono?.family ?? style.fonts.label.family, accent: ui.accent ?? style.colors.primary, send: ui.send ?? style.colors.accent,
    ok: ui.success ?? "#22C55E", palette: ui.icon_colors ?? ["#FF5A5F", "#FF9F0A", "#34C759", "#0A84FF", "#AF52DE", "#FF2D55", "#5856D6", "#FFB800"],
  };
};

const Dots: React.FC<{ s?: number }> = ({ s = 1 }) => (
  <div style={{ display: "flex", gap: 8 * s }}>
    {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 13 * s, height: 13 * s, borderRadius: "50%", background: c, boxShadow: "inset 0 0 0 0.5px rgba(0,0,0,0.12)" }} />)}
  </div>
);

const Cursor: React.FC<{ x: number; y: number; down?: number; opacity?: number; scale?: number }> = ({ x, y, down = 0, opacity = 1, scale = 1 }) => (
  <svg viewBox="0 0 24 34" style={{ position: "absolute", left: x - 3 * scale, top: y - 2 * scale, width: 30 * scale, height: 42 * scale, opacity, transform: `scale(${1 - 0.14 * down})`, transformOrigin: "10% 5%", filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.28))", zIndex: 50 }}>
    <path d="M2 2 L2 27 L8.2 21.2 L12.4 31 L16.6 29.2 L12.5 19.8 L20.8 19.8 Z" fill="#111" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
  </svg>
);

const Shine: React.FC<{ p: number; radius?: number }> = ({ p, radius = 0 }) => (
  <div style={{ position: "absolute", inset: 0, borderRadius: radius, overflow: "hidden", pointerEvents: "none" }}>
    <div style={{ position: "absolute", top: "-50%", bottom: "-50%", width: "35%", left: `${-40 + p * 160}%`, transform: "rotate(18deg)", background: "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0) 100%)", opacity: p > 0 && p < 1 ? 1 : 0 }} />
  </div>
);

export const SceneView: React.FC<{ g: Graphic; style: Style; lf: number; dur: number; w: number; h: number }> = (p) => {
  switch (p.g.type) {
    case "repo": return <Repo {...p} />;
    case "editor": return <Editor {...p} />;
    case "desktop": return <Desktop {...p} />;
    case "comment": return <Comment {...p} />;
    case "badge": return <Badge {...p} />;
    case "aiedit": return <AIEdit {...p} />;
    case "code": return <Code {...p} />;
    case "role": return <Role {...p} />;
    case "queue": return <Queue {...p} />;
    case "timeline": return <Timeline {...p} />;
  }
  return null;
};

type SP = { g: Graphic; style: Style; lf: number; dur: number; w: number; h: number };

// ---------- repo ----------
const Repo: React.FC<SP> = ({ g, style, lf, dur, w }) => {
  const c = useCtx(g, style, lf, dur);
  const enter = c.sp(0, 15);
  const [owner, name] = (g.repo ?? "you/repo").split("/");
  const files = g.items ?? [];
  const listAt = c.at(0, 0.25), hiAt = c.at(1, dur / c.fps * 0.6), starAt = c.at(2, dur / c.fps * 0.75);
  const star = c.sp(starAt, 10);
  const cur = { x: interpolate(c.t, [starAt - 1.1, starAt - 0.08], [w + 40, w - 168], { ...cl, easing: inOut }), y: interpolate(c.t, [starAt - 1.1, starAt - 0.08], [430, 44], { ...cl, easing: inOut }) };
  const down = c.ramp(starAt - 0.05, starAt) - c.ramp(starAt + 0.1, starAt + 0.18);
  const hi = c.sp(hiAt, 16);
  const btn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 8, height: 40, padding: "0 14px", borderRadius: 10, border: "1px solid rgba(17,24,39,0.12)", background: "#F6F8FA", fontFamily: c.body, fontWeight: 600, fontSize: 19, color: c.ink };
  const tabs: [string, string][] = [["Code2", "Code"], ["CircleDot", "Issues"], ["GitPullRequest", "Pull requests"], ["PlayCircle", "Actions"]];
  return (
    <div style={{ width: w, position: "relative", perspective: 1400 }}>
      <div style={{ position: "relative", background: "#FFFFFF", borderRadius: 24, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden",
        transform: `translateY(${(1 - enter) * 70}px) rotateX(${(1 - enter) * 14}deg) scale(${0.94 + 0.06 * enter + c.ramp(0, dur / c.fps, 0, 0.02, (x) => x)})`, opacity: Math.min(1, enter * 1.4), transformOrigin: "50% 100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "20px 24px 14px" }}>
          <Icons.Github size={34} color={c.ink} strokeWidth={2} />
          <div style={{ fontFamily: c.font, fontSize: 29, color: c.muted, fontWeight: 500, whiteSpace: "nowrap" }}>{owner} / <span style={{ color: c.ink, fontWeight: 800 }}>{name}</span></div>
          <div style={{ fontFamily: c.body, fontSize: 16, fontWeight: 600, color: c.muted, border: "1px solid rgba(17,24,39,0.16)", borderRadius: 999, padding: "3px 10px" }}>Public</div>
          <div style={{ flex: 1 }} />
          <div style={{ ...btn, position: "relative", background: star > 0.05 ? "#FFF8E6" : "#F6F8FA", borderColor: star > 0.05 ? "#FFB80088" : "rgba(17,24,39,0.12)" }}>
            <div style={{ transform: `scale(${1 + 0.45 * Math.sin(Math.min(1, star) * Math.PI)})` }}>
              <Icons.Star size={21} color={star > 0.05 ? "#FFB800" : c.muted} fill={star > 0.05 ? "#FFB800" : "none"} strokeWidth={2.4} />
            </div>
            {star > 0.05 ? "Starred" : "Star"}
            {[0, 1, 2, 3, 4, 5].map((i) => {
              const a = (i / 6) * Math.PI * 2, r = 10 + 34 * star;
              return <div key={i} style={{ position: "absolute", left: 24 + Math.cos(a) * r, top: 19 + Math.sin(a) * r, width: 7, height: 7, borderRadius: 4, background: c.palette[i % c.palette.length], opacity: star > 0.05 ? Math.max(0, 1 - star * 0.9) : 0 }} />;
            })}
          </div>
          <div style={{ ...btn, background: c.ok, borderColor: c.ok, color: "#FFF" }}><Icons.Code2 size={20} color="#FFF" strokeWidth={2.6} />Code</div>
        </div>
        <div style={{ display: "flex", gap: 26, padding: "0 24px", borderBottom: "1px solid rgba(17,24,39,0.08)" }}>
          {tabs.map(([ic, label], i) => {
            const I = icon(ic);
            return (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 2px 12px", fontFamily: c.body, fontSize: 19, fontWeight: i ? 500 : 700, color: i ? c.muted : c.ink, borderBottom: i ? "3px solid transparent" : `3px solid ${c.send}` }}>
                <I size={19} color={i ? c.muted : c.ink} strokeWidth={2.2} />{label}
              </div>
            );
          })}
        </div>
        <div style={{ margin: "16px 24px 0", border: "1px solid rgba(17,24,39,0.09)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: "#F6F8FA", borderBottom: "1px solid rgba(17,24,39,0.08)" }}>
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: `linear-gradient(135deg, ${c.accent}, ${style.colors.secondary})`, color: "#FFF", fontFamily: c.font, fontWeight: 800, fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center" }}>{owner.slice(0, 1).toUpperCase()}</div>
            <span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 18, color: c.ink }}>{owner}</span>
            <span style={{ fontFamily: c.body, fontSize: 18, color: c.muted, flex: 1 }}>{g.subtitle}</span>
            <Icons.Check size={20} color={c.ok} strokeWidth={3} />
            <span style={{ fontFamily: c.mono, fontSize: 16, color: c.muted }}>now</span>
          </div>
          {files.map((f, i) => {
            const p = c.sp(listAt + i * 0.13, 15);
            const dir = f.endsWith("/");
            const last = i === files.length - 1;
            const glow = last ? hi : 0;
            return (
              <div key={f} style={{ position: "relative", display: "flex", alignItems: "center", gap: 14, padding: "0 16px", height: 52, borderTop: i ? "1px solid rgba(17,24,39,0.06)" : undefined,
                background: `rgba(91,91,214,${0.09 * glow})`, opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * -36}px)` }}>
                {dir ? <Icons.Folder size={22} color="#0A84FF" fill="#0A84FF55" strokeWidth={2} /> : <Icons.FileText size={22} color={c.muted} strokeWidth={2} />}
                <span style={{ fontFamily: c.body, fontWeight: 600, fontSize: 20, color: c.ink, width: 210 }}>{dir ? f.slice(0, -1) : f}</span>
                <span style={{ fontFamily: c.body, fontSize: 18, color: c.muted, flex: 1 }}>{g.subtitle}</span>
                {last && <span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 14, color: "#FFF", background: c.accent, borderRadius: 999, padding: "3px 10px", transform: `scale(${glow})`, marginRight: 10 }}>NEW</span>}
                <span style={{ fontFamily: c.mono, fontSize: 15, color: "#9CA3AF" }}>now</span>
                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, background: c.accent, opacity: glow }} />
              </div>
            );
          })}
        </div>
        <div style={{ height: 22 }} />
        <Shine p={c.ramp(0.35, 1.1)} radius={24} />
      </div>
      <Cursor x={cur.x} y={cur.y} down={down} opacity={c.ramp(starAt - 1.1, starAt - 0.9)} />
    </div>
  );
};

// ---------- editor ----------
const wave = (seed: number, n: number) => Array.from({ length: n }, (_, i) => {
  const v = Math.abs(Math.sin(i * 1.7 + seed * 3.1) * 0.6 + Math.sin(i * 0.43 + seed) * 0.4);
  return 0.18 + 0.82 * v;
});

const Editor: React.FC<SP> = ({ g, style, lf, dur, w, h }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const m = [0, 1, 2, 3, 4, 5].map((i) => c.at(i, (T * (i + 1)) / 7));
  const enter = c.sp(0, 16);
  const steps = g.items ?? [];
  // lane model: [kind, width]; s = speech, g = silence, b = bad take
  const segs: [string, number][] = [["s", 0.17], ["g", 0.1], ["s", 0.15], ["b", 0.13], ["s", 0.13], ["g", 0.09], ["s", 0.23]];
  const gapK = 1 - c.ramp(m[0] + 0.15, m[0] + 0.6, 0, 1, inOut);
  const badK = 1 - c.ramp(m[1] + 0.45, m[1] + 0.9, 0, 1, inOut);
  const flagG = c.ramp(m[0] - 0.45, m[0] - 0.2);
  const flagB = c.ramp(m[1] - 0.3, m[1] - 0.05);
  const pad = 18, head = 46;
  const topH = Math.round((h - head - pad * 3) * 0.5);
  const tlH = h - head - pad * 3 - topH;
  const lanesX = 64, laneW = w - pad * 2 - lanesX - 20;
  const rows = ["V2", "V1", "A1", "A2", "A3"];
  const ruler = 30, laneH = Math.floor((tlH - ruler - 16) / rows.length) - 8;
  let x = 0;
  const placed = segs.map(([k, wd]) => {
    const scale = k === "g" ? gapK : k === "b" ? badK : 1;
    const item = { k, x, w: wd * scale * laneW };
    x += item.w;
    return item;
  });
  const done = c.sp(m[5], 12);
  const ph = interpolate(c.t, [0, T], [0.04, 0.96]) * Math.max(x, laneW * 0.55);
  const split = c.ramp(m[2] - 0.05, m[2] + 0.35);
  const vw = Math.round(topH * 9 / 16);
  const status = (i: number) => (c.t >= m[i] + 0.4 ? 2 : c.t >= m[i] - 0.35 ? 1 : 0);
  const laneY = (r: number) => ruler + 8 + r * (laneH + 8);
  const block = (k: string): React.CSSProperties => ({ position: "absolute", top: 0, bottom: 0, borderRadius: 9, overflow: "hidden" });
  const lbl = (text: string, color: string, op: number) => (
    <div style={{ position: "absolute", top: -26, left: "50%", transform: `translateX(-50%) scale(${0.7 + 0.3 * op})`, opacity: op, fontFamily: c.body, fontWeight: 700, fontSize: 15, color: "#FFF", background: color, borderRadius: 999, padding: "3px 10px", whiteSpace: "nowrap", boxShadow: `0 6px 14px ${color}55` }}>{text}</div>
  );
  return (
    <div style={{ width: w, height: h, position: "relative", opacity: Math.min(1, enter * 1.5), transform: `translateY(${(1 - enter) * 60}px) scale(${0.95 + 0.05 * enter})` }}>
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", borderRadius: 26, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
        <div style={{ height: head, display: "flex", alignItems: "center", padding: "0 18px", gap: 14, background: "linear-gradient(#FBFCFE, #F2F4F9)", borderBottom: "1px solid rgba(17,24,39,0.07)" }}>
          <Dots />
          <div style={{ flex: 1, textAlign: "center", fontFamily: c.body, fontWeight: 600, fontSize: 17, color: c.muted }}>{g.title ?? "Untitled edit"}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: c.body, fontWeight: 700, fontSize: 15, color: done > 0.1 ? "#FFF" : c.muted, background: done > 0.1 ? c.ok : "#EEF0F5", borderRadius: 999, padding: "4px 12px", transform: `scale(${1 + 0.15 * Math.sin(Math.min(1, done) * Math.PI)})` }}>
            {done > 0.1 ? <Icons.Check size={15} color="#FFF" strokeWidth={3.4} /> : <Icons.Loader2 size={15} color={c.muted} strokeWidth={2.6} style={{ transform: `rotate(${frame * 14}deg)` } as React.CSSProperties} />}
            {done > 0.1 ? "Edit complete" : "Editing"}
          </div>
        </div>
        {/* preview + steps */}
        <div style={{ position: "absolute", left: pad, top: head + pad, right: pad, height: topH, display: "flex", gap: pad }}>
          <div style={{ width: vw, height: topH, borderRadius: 16, background: "#0F1117", position: "relative", overflow: "hidden", boxShadow: "0 10px 24px rgba(15,17,23,0.25)" }}>
            <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, top: `${split * 50}%`, overflow: "hidden" }}>
              {g.src && (
                <Sequence from={frame - lf} layout="none">
                  <OffthreadVideo src={staticFile(g.src)} muted startFrom={Math.round((g.from ?? 0) * c.fps)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 30%" }} />
                </Sequence>
              )}
            </div>
            <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: `${split * 50}%`, background: style.background.css ?? style.background.color, backgroundColor: style.background.color, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
              <div style={{ width: vw * 0.72, background: "#FFF", borderRadius: 8, boxShadow: "0 6px 14px rgba(30,40,80,0.18)", padding: 8, opacity: split, transform: `translateY(${(1 - c.sp(m[2] + 0.12)) * 30}px)` }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 5, marginTop: i ? 6 : 0, opacity: c.sp(m[2] + 0.25 + i * 0.12) }}>
                    <div style={{ width: 14, height: 14, borderRadius: 4, background: c.palette[i + 2] }} />
                    <div style={{ flex: 1, height: 6, borderRadius: 3, background: "#E5E7EB" }} />
                  </div>
                ))}
              </div>
            </div>
            <div style={{ position: "absolute", left: "50%", top: `${split ? 50 : 70}%`, transform: "translate(-50%, -50%)", fontFamily: c.font, fontWeight: 700, fontSize: 13, color: "#FFF", background: "rgba(58,58,58,0.85)", borderRadius: 5, padding: "2px 6px", whiteSpace: "nowrap" }}>captions</div>
            <div style={{ position: "absolute", left: 8, top: 8, fontFamily: c.mono, fontSize: 11, color: "#FFF", background: "rgba(0,0,0,0.45)", borderRadius: 4, padding: "1px 5px" }}>9:16</div>
          </div>
          <div style={{ flex: 1, borderRadius: 16, border: "1px solid rgba(17,24,39,0.08)", background: "#FAFBFD", padding: "18px 20px", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <Icons.Asterisk size={30} color={c.send} strokeWidth={3} style={{ transform: `rotate(${frame * 3}deg)` } as React.CSSProperties} />
              <span style={{ fontFamily: c.font, fontWeight: 800, fontSize: 25, color: c.ink }}>Claude</span>
              <span style={{ fontFamily: c.mono, fontSize: 17, color: "#9A4A2F", background: "#FBEFE9", borderRadius: 7, padding: "3px 9px" }}>full-edit</span>
            </div>
            {steps.map((s, i) => {
              const st = status(i);
              const p = c.ramp(m[i] - 0.35, m[i] + 0.4);
              const pop = c.sp(m[i] + 0.4, 11);
              return (
                <div key={s} style={{ display: "flex", alignItems: "center", gap: 14, padding: "9px 0", borderTop: i ? "1px solid rgba(17,24,39,0.06)" : undefined }}>
                  <div style={{ position: "relative", width: 28, height: 28, flex: "none" }}>
                    <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: `3px solid ${st === 1 ? c.accent + "33" : "#D1D5DB"}` }} />
                    {st === 1 && <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "3px solid transparent", borderTopColor: c.accent, transform: `rotate(${frame * 22}deg)` }} />}
                    <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: c.ok, transform: `scale(${st === 2 ? pop : 0})`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icons.Check size={18} color="#FFF" strokeWidth={3.6} />
                    </div>
                  </div>
                  <span style={{ fontFamily: c.font, fontWeight: 650, fontSize: 22, color: st ? c.ink : "#9CA3AF", flex: 1, whiteSpace: "nowrap" }}>{s}</span>
                  <div style={{ width: 70, height: 6, borderRadius: 3, background: "#E5E7EB", overflow: "hidden" }}>
                    <div style={{ width: `${p * 100}%`, height: "100%", background: st === 2 ? c.ok : c.accent }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        {/* timeline */}
        <div style={{ position: "absolute", left: pad, right: pad, bottom: pad, height: tlH, borderRadius: 16, background: "#F5F7FB", border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: lanesX, right: 0, top: 0, height: ruler, borderBottom: "1px solid rgba(17,24,39,0.08)" }}>
            {Array.from({ length: 9 }, (_, i) => (
              <div key={i} style={{ position: "absolute", left: (i * laneW) / 8, top: 0, height: ruler, borderLeft: "1px solid rgba(17,24,39,0.15)", paddingLeft: 4, fontFamily: c.mono, fontSize: 12, color: "#9CA3AF", lineHeight: `${ruler}px` }}>{`00:${String(i * 8).padStart(2, "0")}`}</div>
            ))}
          </div>
          {rows.map((r, ri) => (
            <div key={r} style={{ position: "absolute", left: 10, top: laneY(ri), width: lanesX - 18, height: laneH, borderRadius: 8, background: "#FFF", border: "1px solid rgba(17,24,39,0.07)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: c.mono, fontWeight: 600, fontSize: 14, color: c.muted }}>{r}</div>
          ))}
          <div style={{ position: "absolute", left: lanesX, top: 0, right: 0, bottom: 0 }}>
            {/* V2 graphics */}
            <div style={{ position: "absolute", left: 0, right: 0, top: laneY(0), height: laneH }}>
              {[0.06, 0.3, 0.55].map((fx, i) => {
                const p = c.sp(m[2] + i * 0.12, 12);
                return (
                  <div key={i} style={{ ...block("v2"), left: fx * Math.max(x, laneW * 0.6), width: laneW * 0.16, background: "linear-gradient(135deg, #AF52DE, #5856D6)", opacity: Math.min(1, p * 1.6), transform: `translateY(${(1 - p) * -50}px)`, display: "flex", alignItems: "center", gap: 6, padding: "0 10px", boxShadow: "0 6px 14px rgba(88,86,214,0.35)" }}>
                    <Icons.Sparkles size={16} color="#FFF" strokeWidth={2.4} />
                    <span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 14, color: "#FFF" }}>graphic</span>
                  </div>
                );
              })}
            </div>
            {/* V1 video + A1 voice */}
            {[1, 2].map((ri) => (
              <div key={ri} style={{ position: "absolute", left: 0, right: 0, top: laneY(ri), height: laneH }}>
                {placed.map((s, i) => {
                  if (s.w < 0.5) return null;
                  const bad = s.k === "b", gap = s.k === "g";
                  const flag = bad ? flagB : gap ? flagG : 0;
                  const red = "#E5484D";
                  const base: React.CSSProperties = { ...block("v"), left: s.x + 1.5, width: Math.max(0, s.w - 3) };
                  if (ri === 1) {
                    return (
                      <div key={i} style={{ ...base, overflow: "visible", background: gap ? "#E9ECF3" : "linear-gradient(180deg, #3A3F4E, #232733)", outline: flag ? `3px solid ${red}` : undefined, outlineOffset: -1 }}>
                        <div style={{ position: "absolute", inset: 0, borderRadius: 9, overflow: "hidden", display: "flex" }}>
                          {!gap && ["still_1", "still_3", "still_6", "still_1"].map((f, j) => <Img key={j} src={staticFile(`assets/${f}.jpg`)} style={{ height: "100%", width: laneH * 0.62, objectFit: "cover", opacity: 0.9, flex: "none" }} />)}
                        </div>
                        {(bad || gap) && <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: `repeating-linear-gradient(135deg, ${red}${bad ? "55" : "33"} 0 8px, transparent 8px 16px)`, opacity: flag }} />}
                        {bad && <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: flag }}><Icons.X size={30} color="#FFF" strokeWidth={4} /></div>}
                        {bad && lbl("bad take", red, flag * Math.min(1, s.w / 30))}
                        {gap && i === 1 && lbl("silence", red, flag * Math.min(1, s.w / 30))}
                      </div>
                    );
                  }
                  const bars = wave(i + 1, Math.max(1, Math.floor(s.w / 7)));
                  return (
                    <div key={i} style={{ ...base, background: gap ? "#EEF1F6" : "#E3F7EA", border: `1px solid ${gap ? "rgba(17,24,39,0.06)" : "#34C75955"}`, display: "flex", alignItems: "center", gap: 3, padding: "0 4px" }}>
                      {gap ? <div style={{ flex: 1, height: 2, background: "#C9CED8" }} /> : bars.map((b, j) => <div key={j} style={{ flex: "none", width: 4, height: `${b * 80}%`, borderRadius: 2, background: "#34C759" }} />)}
                      {(bad || gap) && <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: `${red}22`, border: `2px solid ${red}`, opacity: flag }} />}
                    </div>
                  );
                })}
              </div>
            ))}
            {/* A2 sfx */}
            <div style={{ position: "absolute", left: 0, right: 0, top: laneY(3), height: laneH }}>
              {[0.08, 0.24, 0.41, 0.6, 0.78].map((fx, i) => {
                const p = c.sp(m[3] + i * 0.08, 10);
                return (
                  <div key={i} style={{ ...block("sfx"), left: fx * Math.max(x, laneW * 0.6), width: 46, background: "linear-gradient(135deg, #FF9F0A, #FF5A5F)", transform: `scale(${p})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 5px 12px rgba(255,90,95,0.35)" }}>
                    <Icons.Volume2 size={18} color="#FFF" strokeWidth={2.6} />
                  </div>
                );
              })}
            </div>
            {/* A3 music */}
            <div style={{ position: "absolute", left: 0, top: laneY(4), height: laneH, opacity: c.t > m[4] - 0.05 ? 1 : 0, width: Math.max(x, laneW * 0.6) * c.ramp(m[4] - 0.05, m[4] + 0.4, 0, 1, out), borderRadius: 9, overflow: "hidden", background: "linear-gradient(90deg, #0A84FF, #5856D6)", display: "flex", alignItems: "center", gap: 3, padding: "0 10px", boxShadow: "0 6px 14px rgba(10,132,255,0.3)" }}>
              <Icons.Music2 size={18} color="#FFF" strokeWidth={2.6} style={{ flex: "none" }} />
              {wave(9, 120).map((b, j) => <div key={j} style={{ flex: "none", width: 3, height: `${(0.35 + 0.4 * Math.abs(Math.sin(j * 0.31))) * 70}%`, borderRadius: 2, background: "rgba(255,255,255,0.75)" }} />)}
            </div>
            {/* playhead */}
            <div style={{ position: "absolute", top: 0, bottom: 0, left: ph, width: 2, background: c.send, boxShadow: `0 0 10px ${c.send}` }}>
              <div style={{ position: "absolute", top: 2, left: -8, width: 18, height: 18, borderRadius: "4px 4px 9px 9px", background: c.send }} />
            </div>
            {/* done sweep */}
            <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: Math.max(x, laneW * 0.6), background: `linear-gradient(90deg, transparent, ${c.ok}33, transparent)`, opacity: done > 0.05 ? 1 - done * 0.6 : 0, transform: `translateX(${(done - 0.5) * 400}px)` }} />
          </div>
        </div>
        <Shine p={c.ramp(m[5] + 0.05, m[5] + 0.7)} radius={26} />
      </div>
    </div>
  );
};

// ---------- desktop ----------
const Desktop: React.FC<SP> = ({ g, style, lf, dur, w, h }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const [mDrag, mDrop, mType, mTypeEnd, mEnter, mReply] = [0, 1, 2, 3, 4, 5].map((i) => c.at(i, (T * (i + 1)) / 8));
  const enter = c.sp(0, 16);
  const file = g.label ?? "raw_video.mov";
  const text = g.text ?? "";
  const steps = g.items ?? [];
  // world layout (unscaled desktop = w x h)
  // tall (full-canvas) desktops cap the Claude window height and centre it so the camera moves don't land on empty space
  const claH = Math.min(h - 128 - 22, Math.round((w - 316) * 1.75));
  const claY = Math.max(128, Math.round((h - claH) / 2 + 30));
  const fin = { x: 26, y: claY - 66, w: 400, h: 330 };
  const cla = { x: 290, y: claY, w: w - 290 - 26, h: claH };
  const inputBox = { x: cla.x + 24, y: cla.y + cla.h - 24 - 156, w: cla.w - 48, h: 156 };
  const fileP = { x: fin.x + 40 + 75, y: fin.y + 100 + 48 };
  const dropP = { x: inputBox.x + inputBox.w * 0.5, y: inputBox.y + 60 };
  // cursor path
  const dragK = c.ramp(mDrag + 0.08, mDrop - 0.12, 0, 1, inOut);
  const approach = c.ramp(0.35, mDrag - 0.05, 0, 1, inOut);
  const cx0 = { x: w * 0.82, y: h * 0.86 };
  let cx = cx0.x + (fileP.x - cx0.x) * approach, cy = cx0.y + (fileP.y - cx0.y) * approach;
  if (c.t >= mDrag + 0.08) {
    const arc = Math.sin(dragK * Math.PI) * -90;
    cx = fileP.x + (dropP.x - fileP.x) * dragK;
    cy = fileP.y + (dropP.y - fileP.y) * dragK + arc;
  }
  const pressed = c.t >= mDrag && c.t < mDrop ? 1 : 0;
  const cursorOp = c.ramp(0.3, 0.45) * (1 - c.ramp(mDrop + 0.35, mDrop + 0.6));
  const dragging = c.t >= mDrag + 0.05 && c.t < mDrop;
  const overClaude = dragging && cx > cla.x && cy > cla.y;
  const dropped = c.t >= mDrop;
  const chip = c.sp(mDrop, 13);
  const sent = c.t >= mEnter + 0.12;
  const n = Math.round(interpolate(c.t, [mType, mTypeEnd], [0, text.length], cl));
  const caret = !sent && c.t > mDrop + 0.2 && Math.floor(lf / 8) % 2 === 0;
  // camera
  const zIn = c.ramp(mDrop - 0.2, mDrop + 0.55, 0, 1, inOut) * (1 - c.ramp(mEnter + 0.1, mEnter + 0.7, 0, 1, inOut));
  const zOut = c.ramp(mEnter + 0.1, mEnter + 0.7, 0, 1, inOut);
  const S = 1 + 0.68 * zIn + 0.22 * zOut;
  const focus = { x: w / 2 + (inputBox.x + inputBox.w / 2 - w / 2) * zIn + (cla.x + cla.w / 2 - w / 2) * zOut, y: h / 2 + (inputBox.y + inputBox.h / 2 - 170 - h / 2) * zIn + (cla.y + 330 - h / 2) * zOut };
  const camera = `translate(${w / 2}px, ${h / 2}px) scale(${S}) translate(${-focus.x}px, ${-focus.y}px)`;
  const keycap = c.sp(mEnter - 0.3, 13) * (1 - c.ramp(mEnter + 0.45, mEnter + 0.7));
  const keyDown = c.ramp(mEnter - 0.04, mEnter) - c.ramp(mEnter + 0.1, mEnter + 0.18);
  const stepDur = Math.max(0.25, (T - mReply - 1.3) / Math.max(1, steps.length));
  const reply = c.sp(mReply, 15);
  const allDone = mReply + 0.35 + steps.length * stepDur;
  const result = c.sp(allDone, 13);
  const bubble = c.sp(mEnter + 0.1, 15);
  const wall = "radial-gradient(circle at 20% 15%, rgba(160,190,255,0.9) 0%, rgba(160,190,255,0) 50%), radial-gradient(circle at 85% 80%, rgba(255,196,224,0.85) 0%, rgba(255,196,224,0) 50%), linear-gradient(160deg, #E9EEFB 0%, #F6E9F3 100%)";
  const thumb = (tw: number, th: number, r = 8) => (
    <div style={{ width: tw, height: th, borderRadius: r, overflow: "hidden", position: "relative", flex: "none", background: "#111" }}>
      {g.src && <Img src={staticFile(g.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: th * 0.36, height: th * 0.36, borderRadius: "50%", background: "rgba(255,255,255,0.85)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Icons.Play size={th * 0.18} color="#111" fill="#111" strokeWidth={2} />
        </div>
      </div>
    </div>
  );
  return (
    <div style={{ width: w, height: h, position: "relative", borderRadius: 30, overflow: "hidden", boxShadow: "0 40px 90px -20px rgba(30,40,80,0.35), 0 0 0 10px #FFFFFF, 0 0 0 11px rgba(17,24,39,0.08)", opacity: Math.min(1, enter * 1.5), transform: `scale(${0.94 + 0.06 * enter})`, background: wall }}>
      <div style={{ position: "absolute", inset: 0, transform: camera, transformOrigin: "0 0" }}>
        {/* menu bar */}
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 34, background: "rgba(255,255,255,0.55)", backdropFilter: "blur(10px)", display: "flex", alignItems: "center", gap: 22, padding: "0 20px", fontFamily: c.body, fontSize: 15, color: c.ink }}>
          <Icons.Asterisk size={18} color={c.send} strokeWidth={3} />
          <b>Claude</b><span>File</span><span>Edit</span><span>View</span><span>Window</span>
          <div style={{ flex: 1 }} />
          <Icons.Wifi size={16} color={c.ink} strokeWidth={2.4} /><Icons.BatteryFull size={20} color={c.ink} strokeWidth={2} /><span>9:41</span>
        </div>
        {/* finder */}
        <div style={{ position: "absolute", left: fin.x, top: fin.y, width: fin.w, height: fin.h, borderRadius: 16, background: "rgba(255,255,255,0.92)", boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.08)", overflow: "hidden" }}>
          <div style={{ height: 40, display: "flex", alignItems: "center", gap: 14, padding: "0 14px", borderBottom: "1px solid rgba(17,24,39,0.07)", background: "#F6F7FA" }}>
            <Dots s={0.9} /><Icons.ChevronLeft size={18} color={c.muted} /><span style={{ fontFamily: c.font, fontWeight: 700, fontSize: 16, color: c.ink }}>Recordings</span>
          </div>
          <div style={{ position: "absolute", left: 0, top: 40, bottom: 0, width: 92, background: "#F1F2F6", padding: "12px 10px", display: "flex", flexDirection: "column", gap: 10 }}>
            {[["Clock", "Recents"], ["Monitor", "Desktop"], ["Download", "Downloads"], ["Film", "Movies"]].map(([ic, lb], i) => {
              const I = icon(ic);
              return <div key={lb} style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: c.body, fontSize: 11.5, color: i === 3 ? c.ink : c.muted, fontWeight: i === 3 ? 700 : 500 }}><I size={13} color={i === 3 ? c.accent : c.muted} strokeWidth={2.2} />{lb}</div>;
            })}
          </div>
          <div style={{ position: "absolute", left: 116, top: 64, display: "flex", flexDirection: "column", alignItems: "center", gap: 8, opacity: dragging ? 0.45 : 1 }}>
            <div style={{ borderRadius: 10, outline: c.t >= mDrag - 0.02 && !dropped ? `3px solid ${c.accent}` : "none", outlineOffset: 3 }}>{thumb(150, 96)}</div>
            <span style={{ fontFamily: c.body, fontSize: 14, fontWeight: 600, color: c.t >= mDrag - 0.02 && !dropped ? "#FFF" : c.ink, background: c.t >= mDrag - 0.02 && !dropped ? c.accent : "transparent", borderRadius: 5, padding: "1px 6px" }}>{file}</span>
          </div>
          {[["FileText", "notes.txt", 290, 70], ["Image", "thumbnail.png", 290, 200], ["Music", "voice.wav", 140, 236]].map(([ic, nm, fx, fy]) => {
            const I = icon(ic as string);
            return (
              <div key={nm as string} style={{ position: "absolute", left: fx as number, top: fy as number, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, opacity: 0.55 }}>
                <div style={{ width: 54, height: 64, borderRadius: 8, background: "#FFF", border: "1px solid rgba(17,24,39,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}><I size={24} color={c.muted} strokeWidth={2} /></div>
                <span style={{ fontFamily: c.body, fontSize: 12, color: c.ink }}>{nm}</span>
              </div>
            );
          })}
        </div>
        {/* claude window */}
        <div style={{ position: "absolute", left: cla.x, top: cla.y, width: cla.w, height: cla.h, borderRadius: 18, background: "#FBFAF7", boxShadow: "0 30px 70px -18px rgba(30,40,80,0.35), 0 8px 18px rgba(30,40,80,0.08)", border: "1px solid rgba(17,24,39,0.08)", overflow: "hidden" }}>
          <div style={{ height: 42, display: "flex", alignItems: "center", gap: 14, padding: "0 16px", borderBottom: "1px solid rgba(17,24,39,0.06)", background: "#F5F3EE" }}>
            <Dots s={0.95} />
            <div style={{ flex: 1, textAlign: "center", fontFamily: c.body, fontWeight: 600, fontSize: 15, color: c.muted, marginRight: 60 }}>Claude</div>
          </div>
          {/* greeting */}
          <div style={{ position: "absolute", left: 0, right: 0, top: cla.h > 900 ? Math.round(cla.h * 0.3) : 150, display: "flex", flexDirection: "column", alignItems: "center", gap: 14, opacity: 1 - bubble }}>
            <Icons.Asterisk size={54} color={c.send} strokeWidth={2.6} style={{ transform: `rotate(${frame * 0.8}deg)` } as React.CSSProperties} />
            <div style={{ fontFamily: c.font, fontWeight: 600, fontSize: 32, color: c.ink, letterSpacing: -0.5 }}>How can I help you today?</div>
          </div>
          {/* conversation */}
          {sent && (
            <div style={{ position: "absolute", left: 24, right: 24, top: 64 }}>
              <div style={{ display: "flex", justifyContent: "flex-end", opacity: bubble, transform: `translateY(${(1 - bubble) * 140}px)` }}>
                <div style={{ background: "#EFECE5", borderRadius: 18, padding: 12, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, background: "#FFF", borderRadius: 12, padding: 8, border: "1px solid rgba(17,24,39,0.08)" }}>
                    {thumb(76, 48, 7)}
                    <div><div style={{ fontFamily: c.body, fontWeight: 700, fontSize: 15, color: c.ink }}>{file}</div><div style={{ fontFamily: c.body, fontSize: 13, color: c.muted }}>Video</div></div>
                  </div>
                  <div style={{ fontFamily: c.body, fontWeight: 500, fontSize: 24, color: c.ink, padding: "0 6px" }}>{text}</div>
                </div>
              </div>
              <div style={{ marginTop: 22, opacity: reply, transform: `translateY(${(1 - reply) * 30}px)` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  <Icons.Asterisk size={28} color={c.send} strokeWidth={3} style={{ transform: `rotate(${c.t < allDone ? frame * 9 : 0}deg)` } as React.CSSProperties} />
                  <span style={{ fontFamily: c.body, fontSize: 20, color: c.ink }}>Running the <span style={{ fontFamily: c.mono, color: "#9A4A2F", background: "#FBEFE9", borderRadius: 6, padding: "1px 7px" }}>full-edit</span> skill</span>
                </div>
                <div style={{ background: "#FFF", borderRadius: 14, border: "1px solid rgba(17,24,39,0.08)", padding: "6px 16px", boxShadow: "0 6px 16px rgba(30,40,80,0.06)" }}>
                  {steps.map((s, i) => {
                    const a = mReply + 0.35 + i * stepDur;
                    const on = c.t >= a - stepDur * 0.9, ok = c.t >= a;
                    const pop = c.sp(a, 11);
                    return (
                      <div key={s} style={{ display: "flex", alignItems: "center", gap: 12, height: 44, borderTop: i ? "1px solid rgba(17,24,39,0.05)" : undefined, opacity: on ? 1 : 0.35 }}>
                        <div style={{ position: "relative", width: 22, height: 22 }}>
                          <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "2.5px solid #E5E7EB", borderTopColor: on && !ok ? c.send : "#E5E7EB", transform: `rotate(${frame * 24}deg)` }} />
                          <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: c.ok, transform: `scale(${ok ? pop : 0})`, display: "flex", alignItems: "center", justifyContent: "center" }}><Icons.Check size={14} color="#FFF" strokeWidth={3.6} /></div>
                        </div>
                        <span style={{ fontFamily: c.body, fontWeight: 600, fontSize: 20, color: c.ink }}>{s}</span>
                      </div>
                    );
                  })}
                </div>
                <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 14, background: "#FFF", borderRadius: 14, border: `2px solid ${c.ok}`, padding: 10, opacity: Math.min(1, result * 1.5), transform: `scale(${0.85 + 0.15 * result})`, transformOrigin: "0 50%" }}>
                  {thumb(96, 60, 8)}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: c.font, fontWeight: 800, fontSize: 19, color: c.ink }}>final.mp4</div>
                    <div style={{ fontFamily: c.body, fontSize: 15, color: c.muted }}>Your edit is ready</div>
                  </div>
                  <div style={{ width: 34, height: 34, borderRadius: "50%", background: c.ok, display: "flex", alignItems: "center", justifyContent: "center" }}><Icons.Check size={20} color="#FFF" strokeWidth={3.4} /></div>
                </div>
              </div>
            </div>
          )}
          {/* input */}
          <div style={{ position: "absolute", left: inputBox.x - cla.x, top: inputBox.y - cla.y, width: inputBox.w, height: inputBox.h, borderRadius: 20, background: "#FFF", border: `1.5px solid ${overClaude ? c.send : "rgba(17,24,39,0.12)"}`, boxShadow: "0 10px 30px rgba(30,40,80,0.10)", padding: "16px 18px", display: "flex", flexDirection: "column" }}>
            {dropped && !sent && (
              <div style={{ display: "flex", alignItems: "center", gap: 10, alignSelf: "flex-start", background: "#F6F5F1", border: "1px solid rgba(17,24,39,0.08)", borderRadius: 12, padding: "6px 12px 6px 6px", marginBottom: 8, transform: `scale(${0.6 + 0.4 * chip})`, opacity: chip, transformOrigin: "0 50%" }}>
                {thumb(56, 36, 6)}
                <div><div style={{ fontFamily: c.body, fontWeight: 700, fontSize: 14, color: c.ink }}>{file}</div><div style={{ fontFamily: c.body, fontSize: 12, color: c.muted }}>Video</div></div>
              </div>
            )}
            <div style={{ fontFamily: c.body, fontWeight: 500, fontSize: 24, color: n && !sent ? c.ink : "#A8A29E", flex: 1 }}>
              {n && !sent ? text.slice(0, n) : "Reply to Claude..."}
              {caret && <span style={{ color: c.send, fontWeight: 300 }}>|</span>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 9, border: "1px solid #E5E7EB", display: "flex", alignItems: "center", justifyContent: "center" }}><Icons.Plus size={18} color={c.muted} strokeWidth={2.4} /></div>
              <div style={{ flex: 1 }} />
              <span style={{ fontFamily: c.body, fontSize: 15, color: c.muted }}>Opus 5.5</span>
              <div style={{ width: 38, height: 38, borderRadius: 10, background: c.send, opacity: n || sent ? 1 : 0.45, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${1 - 0.15 * keyDown})`, boxShadow: keyDown ? `0 0 0 6px ${c.send}33` : "none" }}>
                <Icons.ArrowUp size={22} color="#FFF" strokeWidth={3} />
              </div>
            </div>
          </div>
          {/* drop overlay */}
          <div style={{ position: "absolute", inset: 10, borderRadius: 14, border: `3px dashed ${c.send}`, background: "rgba(217,119,87,0.08)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, opacity: overClaude ? 1 : 0 }}>
            <Icons.FileVideo size={44} color={c.send} strokeWidth={2} />
            <div style={{ fontFamily: c.font, fontWeight: 700, fontSize: 22, color: "#9A4A2F" }}>Drop files here to add to chat</div>
          </div>
        </div>
        {/* drag ghost + cursor */}
        {dragging && (
          <div style={{ position: "absolute", left: cx - 60, top: cy - 30, transform: `rotate(-5deg) scale(${0.85 - 0.25 * c.ramp(mDrop - 0.25, mDrop)})`, opacity: 0.92, filter: "drop-shadow(0 14px 22px rgba(0,0,0,0.3))", zIndex: 40 }}>
            {thumb(150, 96, 10)}
            {overClaude && <div style={{ position: "absolute", right: -10, top: -10, width: 30, height: 30, borderRadius: "50%", background: c.ok, display: "flex", alignItems: "center", justifyContent: "center", border: "2px solid #FFF" }}><Icons.Plus size={18} color="#FFF" strokeWidth={3.4} /></div>}
          </div>
        )}
        <Cursor x={cx} y={cy} down={pressed} opacity={cursorOp} />
      </div>
      {/* return keycap */}
      <div style={{ position: "absolute", right: 40, bottom: 40, opacity: keycap, transform: `translateY(${(1 - keycap) * 30 + keyDown * 6}px)` }}>
        <div style={{ width: 230, height: 104, borderRadius: 20, background: "linear-gradient(180deg, #FFFFFF, #ECEFF5)", border: "1px solid rgba(17,24,39,0.12)", boxShadow: `0 ${10 - keyDown * 8}px 0 #C9CED8, 0 ${18 - keyDown * 10}px 30px rgba(30,40,80,0.25)`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 26px", fontFamily: c.body, fontWeight: 600, fontSize: 30, color: c.ink }}>
          return<Icons.CornerDownLeft size={34} color={c.ink} strokeWidth={2.4} />
        </div>
      </div>
    </div>
  );
};

// ---------- comment ----------
const Comment: React.FC<SP> = ({ g, style, lf, dur, w }) => {
  const c = useCtx(g, style, lf, dur);
  const T = dur / c.fps;
  const [mType, mTypeEnd, mPost, mArrow] = [0, 1, 2, 3].map((i) => c.at(i, (T * (i + 1)) / 5));
  const enter = c.sp(0, 15);
  const text = g.text ?? "";
  const n = Math.round(interpolate(c.t, [mType, mTypeEnd], [0, text.length], cl));
  const posted = c.t >= mPost + 0.08;
  const post = c.sp(mPost + 0.08, 13);
  const heart = c.sp(mPost + 0.45, 9);
  const press = c.ramp(mPost - 0.06, mPost) - c.ramp(mPost + 0.06, mPost + 0.14);
  const arrow = c.sp(mArrow, 12);
  const av = (s: number, a: string, b: string, letter: string) => (
    <div style={{ width: s, height: s, borderRadius: "50%", flex: "none", background: `linear-gradient(135deg, ${a}, ${b})`, display: "flex", alignItems: "center", justifyContent: "center", color: "#FFF", fontFamily: c.font, fontWeight: 800, fontSize: s * 0.42 }}>{letter}</div>
  );
  const W = Math.min(w, 760);
  return (
    <div style={{ width: W, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
      <div style={{ width: W, background: "#FFF", borderRadius: 28, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden", opacity: Math.min(1, enter * 1.5), transform: `translateY(${(1 - enter) * 80}px)` }}>
        <div style={{ display: "flex", justifyContent: "center", paddingTop: 12 }}><div style={{ width: 54, height: 6, borderRadius: 3, background: "#D1D5DB" }} /></div>
        <div style={{ textAlign: "center", fontFamily: c.font, fontWeight: 800, fontSize: 26, color: c.ink, padding: "12px 0 14px", borderBottom: "1px solid rgba(17,24,39,0.07)" }}>Comments</div>
        <div style={{ height: posted ? 96 * post : 0, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 26px", opacity: post, transform: `translateY(${(1 - post) * 40}px)`, background: `rgba(91,91,214,${0.06 * post})` }}>
            {av(52, c.accent, style.colors.secondary, "Y")}
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: c.body, fontSize: 18, color: c.muted }}><b style={{ color: c.ink }}>you</b> · now</div>
              <div style={{ fontFamily: c.font, fontWeight: 700, fontSize: 30, color: c.ink }}>{text}</div>
            </div>
            <div style={{ transform: `scale(${heart > 0.02 ? 0.8 + 0.5 * Math.sin(Math.min(1, heart) * Math.PI) + 0.2 * heart : 1})` }}>
              <Icons.Heart size={32} color={heart > 0.02 ? "#FF2D55" : c.muted} fill={heart > 0.02 ? "#FF2D55" : "none"} strokeWidth={2.2} />
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 22px 20px", borderTop: posted ? "1px solid rgba(17,24,39,0.07)" : undefined }}>
          {av(46, "#FF9F0A", "#FF2D55", "Y")}
          <div style={{ flex: 1, height: 58, borderRadius: 999, border: `2px solid ${n && !posted ? c.accent : "rgba(17,24,39,0.12)"}`, display: "flex", alignItems: "center", padding: "0 22px", fontFamily: c.body, fontWeight: 500, fontSize: 26, color: n && !posted ? c.ink : "#9CA3AF" }}>
            {n && !posted ? text.slice(0, n) : "Add a comment..."}
            {!posted && n > 0 && Math.floor(lf / 7) % 2 === 0 && <span style={{ color: c.accent }}>|</span>}
          </div>
          <div style={{ fontFamily: c.font, fontWeight: 800, fontSize: 24, color: n && !posted ? "#FFF" : "#9CA3AF", background: n && !posted ? c.accent : "#F3F4F6", borderRadius: 999, padding: "12px 22px", transform: `scale(${1 - 0.12 * press})` }}>Post</div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: arrow, transform: `translateY(${(1 - arrow) * -20 + Math.sin(c.t * 9) * 6}px)` }}>
        <Icons.ChevronsDown size={56} color={c.accent} strokeWidth={3} />
      </div>
    </div>
  );
};

// ---------- aiedit ----------
const AIEdit: React.FC<SP> = ({ g, style, lf, dur, w, h }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const enter = c.sp(0, 15);
  const red = "#E5484D";
  const pad = 16, head = 48;
  const prevH = Math.round((h - head - pad * 3) * 0.42);
  const tlH = h - head - pad * 3 - prevH;
  const lanesX = 58, laneW = w - pad * 2 - lanesX - 14;
  const rows = ["V2", "V1", "A1", "A2"];
  const ruler = 26, laneH = Math.floor((tlH - ruler - 12) / rows.length) - 7;
  const laneY = (r: number) => ruler + 6 + r * (laneH + 7);
  // V1/A1 segments: [width, cut-at seconds or null]
  const cutTimes = [0.42, 0.7, 0.98, 1.24, 1.5];
  const segs: [number, number | null][] = [[0.1, null], [0.07, cutTimes[0]], [0.12, null], [0.06, cutTimes[1]], [0.1, null], [0.08, cutTimes[2]], [0.11, null], [0.05, cutTimes[3]], [0.12, null], [0.07, cutTimes[4]], [0.12, null]];
  let x = 0;
  const placed = segs.map(([wd, cut]) => {
    const flag = cut === null ? 0 : c.ramp(cut - 0.14, cut - 0.04);
    const k = cut === null ? 1 : 1 - c.ramp(cut, cut + 0.16, 0, 1, inOut);
    const item = { x, w: wd * laneW * k, cut, flag };
    x += item.w;
    return item;
  });
  const end = x;
  const ph = interpolate(c.t, [0.15, T - 0.15], [0.02, 0.98], { ...cl, easing: (v) => v }) * end;
  const cutsDone = cutTimes.filter((t) => c.t >= t).length;
  const counter = Math.round(interpolate(c.t, [0.3, T - 0.3], [0, 37], cl));
  const done = c.sp(T - 0.32, 12);
  const stills = ["still_1", "still_3", "still_6"];
  const still = stills[Math.floor(lf / 5) % stills.length];
  const flash = cutTimes.reduce((m, t) => Math.max(m, 1 - Math.min(1, Math.abs(c.t - t) / 0.07)), 0);
  const logs = ["Cut silence", "Removed bad take", "Punch-in zoom", "Added graphic", "SFX: whoosh", "Music + ducking", "Captions synced"];
  const logAt = (i: number) => 0.3 + i * ((T - 0.75) / logs.length);
  const shown = logs.filter((_, i) => c.t >= logAt(i)).length;
  const logH = 38;
  const camera = 1 + c.ramp(0.2, T, 0, 0.035, (v) => v);
  const shake = flash * 3;
  return (
    <div style={{ width: w, height: h, position: "relative", opacity: Math.min(1, enter * 1.5), transform: `translateY(${(1 - enter) * 60}px) scale(${(0.94 + 0.06 * enter) * camera}) translateX(${Math.sin(frame * 2.3) * shake}px)` }}>
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", borderRadius: 26, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
        <div style={{ height: head, display: "flex", alignItems: "center", padding: "0 16px", gap: 12, background: "linear-gradient(#FBFCFE, #F2F4F9)", borderBottom: "1px solid rgba(17,24,39,0.07)" }}>
          <Dots />
          <div style={{ flex: 1, fontFamily: c.body, fontWeight: 600, fontSize: 17, color: c.muted, textAlign: "center" }}>raw_video.mov</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: c.mono, fontWeight: 700, fontSize: 15, color: c.ink, background: "#F1F2F6", borderRadius: 999, padding: "4px 10px" }}>
            <Icons.Scissors size={15} color={red} strokeWidth={2.6} />{counter} cuts
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: c.body, fontWeight: 700, fontSize: 15, color: "#FFF", background: done > 0.1 ? c.ok : c.send, borderRadius: 999, padding: "4px 12px", transform: `scale(${1 + 0.15 * Math.sin(Math.min(1, done) * Math.PI)})` }}>
            {done > 0.1 ? <Icons.Check size={15} color="#FFF" strokeWidth={3.4} /> : <Icons.Asterisk size={15} color="#FFF" strokeWidth={3} style={{ transform: `rotate(${frame * 18}deg)` } as React.CSSProperties} />}
            {done > 0.1 ? "Done" : "AI editing"}
          </div>
        </div>
        <div style={{ position: "absolute", left: pad, right: pad, top: head + pad, height: prevH, display: "flex", gap: pad }}>
          <div style={{ width: Math.round(prevH * 16 / 9 * 0.62), height: prevH, borderRadius: 14, overflow: "hidden", position: "relative", background: "#0F1117", flex: "none" }}>
            <Img src={staticFile(`assets/${still}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${1.05 + 0.08 * ((lf % 5) / 5)})` }} />
            <div style={{ position: "absolute", inset: 0, background: "#FFF", opacity: flash * 0.55 }} />
            <div style={{ position: "absolute", left: 8, top: 8, display: "flex", alignItems: "center", gap: 5, fontFamily: c.mono, fontSize: 12, fontWeight: 700, color: "#FFF", background: red, borderRadius: 5, padding: "2px 7px" }}>
              <div style={{ width: 7, height: 7, borderRadius: 4, background: "#FFF", opacity: Math.floor(lf / 6) % 2 ? 1 : 0.3 }} />LIVE
            </div>
            <div style={{ position: "absolute", left: 8, bottom: 8, fontFamily: c.mono, fontSize: 13, color: "#FFF", background: "rgba(0,0,0,0.5)", borderRadius: 4, padding: "1px 6px" }}>{`00:${String(Math.floor(ph / end * 32)).padStart(2, "0")}:${String(lf % 30).padStart(2, "0")}`}</div>
          </div>
          <div style={{ flex: 1, borderRadius: 14, background: "#FAFBFD", border: "1px solid rgba(17,24,39,0.08)", padding: "12px 14px", overflow: "hidden", position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Icons.Asterisk size={24} color={c.send} strokeWidth={3} style={{ transform: `rotate(${frame * 6}deg)` } as React.CSSProperties} />
              <span style={{ fontFamily: c.font, fontWeight: 800, fontSize: 21, color: c.ink }}>Claude</span>
            </div>
            <div style={{ position: "relative", height: prevH - 60, overflow: "hidden" }}>
              <div style={{ position: "absolute", left: 0, right: 0, top: 0, transform: `translateY(${-Math.max(0, shown - Math.floor((prevH - 60) / logH)) * logH}px)` }}>
                {logs.map((l, i) => {
                  const p = c.sp(logAt(i), 14);
                  return (
                    <div key={l} style={{ height: logH, display: "flex", alignItems: "center", gap: 10, opacity: Math.min(1, p * 1.6), transform: `translateX(${(1 - p) * 40}px)` }}>
                      <div style={{ width: 22, height: 22, borderRadius: "50%", background: c.ok, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${p})` }}><Icons.Check size={13} color="#FFF" strokeWidth={3.6} /></div>
                      <span style={{ fontFamily: c.body, fontWeight: 650, fontSize: 19, color: c.ink, whiteSpace: "nowrap" }}>{l}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
        <div style={{ position: "absolute", left: pad, right: pad, bottom: pad, height: tlH, borderRadius: 14, background: "#F5F7FB", border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: lanesX, right: 0, top: 0, height: ruler, borderBottom: "1px solid rgba(17,24,39,0.08)" }}>
            {Array.from({ length: 9 }, (_, i) => (
              <div key={i} style={{ position: "absolute", left: (i * laneW) / 8, height: ruler, borderLeft: "1px solid rgba(17,24,39,0.15)", paddingLeft: 4, fontFamily: c.mono, fontSize: 11, color: "#9CA3AF", lineHeight: `${ruler}px` }}>{`00:${String(i * 4).padStart(2, "0")}`}</div>
            ))}
          </div>
          {rows.map((r, ri) => (
            <div key={r} style={{ position: "absolute", left: 8, top: laneY(ri), width: lanesX - 14, height: laneH, borderRadius: 7, background: "#FFF", border: "1px solid rgba(17,24,39,0.07)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: c.mono, fontWeight: 600, fontSize: 13, color: c.muted }}>{r}</div>
          ))}
          <div style={{ position: "absolute", left: lanesX, top: 0, right: 0, bottom: 0 }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: laneY(0), height: laneH }}>
              {[[0.05, 0.62], [0.33, 0.9], [0.62, 1.18], [0.82, 1.46]].map(([fx, at], i) => {
                const p = c.sp(at, 11);
                return (
                  <div key={i} style={{ position: "absolute", top: 0, bottom: 0, left: fx * end, width: laneW * 0.13, borderRadius: 8, background: `linear-gradient(135deg, ${["#AF52DE", "#5856D6", "#0A84FF", "#FF2D55"][i]}, #5856D6)`, opacity: Math.min(1, p * 1.6), transform: `translateY(${(1 - p) * -40}px) scale(${0.8 + 0.2 * p})`, display: "flex", alignItems: "center", gap: 5, padding: "0 8px", boxShadow: "0 5px 12px rgba(88,86,214,0.35)" }}>
                    <Icons.Sparkles size={14} color="#FFF" strokeWidth={2.4} />
                    <span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 12, color: "#FFF" }}>{["title", "zoom", "graphic", "callout"][i]}</span>
                  </div>
                );
              })}
            </div>
            {[1, 2].map((ri) => (
              <div key={ri} style={{ position: "absolute", left: 0, right: 0, top: laneY(ri), height: laneH }}>
                {placed.map((s, i) => {
                  if (s.w < 0.5) return null;
                  const bad = s.cut !== null;
                  const base: React.CSSProperties = { position: "absolute", top: 0, bottom: 0, left: s.x + 1.5, width: Math.max(0, s.w - 3), borderRadius: 8, overflow: "hidden" };
                  if (ri === 1) {
                    return (
                      <div key={i} style={{ ...base, background: "linear-gradient(180deg, #3A3F4E, #232733)", display: "flex", outline: bad && s.flag ? `3px solid ${red}` : undefined, outlineOffset: -1 }}>
                        {stills.map((f, j) => <Img key={j} src={staticFile(`assets/${f}.jpg`)} style={{ height: "100%", width: laneH * 0.62, objectFit: "cover", opacity: 0.9, flex: "none" }} />)}
                        {bad && <div style={{ position: "absolute", inset: 0, background: `repeating-linear-gradient(135deg, ${red}66 0 7px, transparent 7px 14px)`, opacity: s.flag }} />}
                      </div>
                    );
                  }
                  const bars = wave(i + 3, Math.max(1, Math.floor(s.w / 6)));
                  return (
                    <div key={i} style={{ ...base, background: bad ? `rgba(229,72,77,${0.12 + 0.2 * s.flag})` : "#E3F7EA", border: `1px solid ${bad && s.flag ? red : "#34C75955"}`, display: "flex", alignItems: "center", gap: 2, padding: "0 3px" }}>
                      {bars.map((b, j) => <div key={j} style={{ flex: "none", width: 3, height: `${(bad ? 0.25 : b) * 80}%`, borderRadius: 2, background: bad ? red : "#34C759" }} />)}
                    </div>
                  );
                })}
              </div>
            ))}
            <div style={{ position: "absolute", left: 0, right: 0, top: laneY(3), height: laneH }}>
              <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: end * c.ramp(1.2, T - 0.35, 0, 1, out), borderRadius: 8, overflow: "hidden", background: "linear-gradient(90deg, #0A84FF, #5856D6)", opacity: c.t > 1.18 ? 1 : 0 }}>
                {wave(9, 80).map((b, j) => <div key={j} style={{ position: "absolute", left: 30 + j * 6, top: "50%", width: 3, height: `${(0.3 + 0.4 * Math.abs(Math.sin(j * 0.37))) * 70}%`, transform: "translateY(-50%)", borderRadius: 2, background: "rgba(255,255,255,0.75)" }} />)}
                <Icons.Music2 size={16} color="#FFF" strokeWidth={2.6} style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)" } as React.CSSProperties} />
              </div>
              {[0.12, 0.3, 0.5, 0.72].map((fx, i) => {
                const p = c.sp(0.8 + i * 0.16, 9);
                return (
                  <div key={i} style={{ position: "absolute", top: 4, bottom: 4, left: fx * end, width: 34, borderRadius: 7, background: "linear-gradient(135deg, #FF9F0A, #FF5A5F)", transform: `scale(${p})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 10px rgba(255,90,95,0.4)" }}>
                    <Icons.Volume2 size={15} color="#FFF" strokeWidth={2.6} />
                  </div>
                );
              })}
            </div>
            {cutTimes.map((t, i) => {
              const seg = placed[i * 2 + 1];
              const p = c.ramp(t - 0.06, t) * (1 - c.ramp(t + 0.12, t + 0.28));
              return (
                <div key={i} style={{ position: "absolute", top: laneY(1) - 6, height: laneH * 2 + 19, left: seg.x, width: 3, background: red, opacity: p, boxShadow: `0 0 12px ${red}` }}>
                  <div style={{ position: "absolute", top: -22, left: -11, width: 25, height: 25, borderRadius: "50%", background: red, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.6 + 0.4 * p}) rotate(${p * 90}deg)` }}>
                    <Icons.Scissors size={14} color="#FFF" strokeWidth={2.8} />
                  </div>
                </div>
              );
            })}
            <div style={{ position: "absolute", top: 0, bottom: 0, left: ph, width: 2, background: c.send, boxShadow: `0 0 10px ${c.send}` }}>
              <div style={{ position: "absolute", top: 2, left: -8, width: 18, height: 18, borderRadius: "4px 4px 9px 9px", background: c.send }} />
              <div style={{ position: "absolute", top: laneY(2) + laneH * 0.4, left: 10, display: "flex", alignItems: "center", gap: 4, fontFamily: c.body, fontWeight: 700, fontSize: 13, color: "#FFF", background: c.send, borderRadius: "4px 10px 10px 10px", padding: "3px 9px", whiteSpace: "nowrap", boxShadow: "0 6px 14px rgba(217,119,87,0.4)" }}>
                <Icons.Asterisk size={13} color="#FFF" strokeWidth={3} />Claude
              </div>
            </div>
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: head, height: 4, background: "#EEF0F5" }}>
          <div style={{ width: `${(cutsDone / cutTimes.length) * 70 + c.ramp(0, T) * 30}%`, height: "100%", background: `linear-gradient(90deg, ${c.send}, ${c.accent})` }} />
        </div>
        <Shine p={c.ramp(T - 0.3, T + 0.2)} radius={26} />
      </div>
    </div>
  );
};

// ---------- badge ----------
const Badge: React.FC<SP> = ({ g, style, lf, dur }) => {
  const c = useCtx(g, style, lf, dur);
  const I = icon(g.icon ?? "Clapperboard");
  const p = c.sp(0, 12);
  const ic = c.sp(0.1, 10);
  const txt = c.sp(0.18, 15);
  const sparks = [[-36, -18], [-24, 104], [118, -22], [98, 112]];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 24, background: "rgba(255,255,255,0.96)", borderRadius: 34, padding: "18px 36px 18px 18px", boxShadow: "0 30px 70px -14px rgba(20,24,60,0.45), 0 6px 16px rgba(20,24,60,0.18), inset 0 1px 0 #FFF", border: "1px solid rgba(17,24,39,0.06)", transform: `scale(${0.6 + 0.4 * p}) translateY(${(1 - p) * -40}px)`, opacity: Math.min(1, p * 1.6) }}>
      <div style={{ position: "relative", width: 104, height: 104 }}>
        <div style={{ position: "absolute", inset: 0, borderRadius: 28, background: `linear-gradient(150deg, ${c.accent} 0%, ${style.colors.secondary} 100%)`, boxShadow: `0 12px 26px ${c.accent}66, inset 0 2px 0 rgba(255,255,255,0.35)`, display: "flex", alignItems: "center", justifyContent: "center", transform: `rotate(${(1 - ic) * -18}deg) scale(${0.7 + 0.3 * ic})`, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "50%", background: "linear-gradient(180deg, rgba(255,255,255,0.28), rgba(255,255,255,0))" }} />
          <I size={56} color="#FFFFFF" strokeWidth={2.3} />
          <Shine p={c.ramp(0.35, 0.95)} radius={28} />
        </div>
        {sparks.map(([sx, sy], i) => {
          const s = c.sp(0.25 + i * 0.06, 9);
          return <div key={i} style={{ position: "absolute", left: sx, top: sy, transform: `scale(${s}) rotate(${c.t * 90}deg)`, opacity: Math.max(0, 1 - c.ramp(0.9, 1.4)) }}><Icons.Sparkle size={22} color={i % 2 ? c.send : "#FFB800"} fill={i % 2 ? c.send : "#FFB800"} strokeWidth={1.5} /></div>;
        })}
      </div>
      <div style={{ opacity: txt, transform: `translateX(${(1 - txt) * -20}px)` }}>
        <div style={{ fontFamily: c.font, fontWeight: 800, fontSize: 56, color: c.ink, letterSpacing: -1.5, lineHeight: 1 }}>{g.title}</div>
        {g.subtitle && <div style={{ fontFamily: c.mono, fontWeight: 500, fontSize: 22, color: "#9A4A2F", background: "#FBEFE9", borderRadius: 8, padding: "4px 10px", marginTop: 10, display: "inline-block" }}>{g.subtitle}</div>}
      </div>
    </div>
  );
};

// ---------- code ----------
const KW = new Set(["import", "from", "export", "async", "await", "function", "const", "let", "return", "new", "if", "else", "for", "of", "type"]);
const tokenize = (line: string): [string, string][] => {
  const res: [string, string][] = [];
  const re = /("[^"]*"?|'[^']*'?|\/\/.*|[A-Za-z_$][\w$]*|\d+|\s+|[^\sA-Za-z_$\d"']+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line))) {
    const t = m[0], word = /^[A-Za-z_$]/.test(t);
    res.push([t, /^["']/.test(t) ? "str" : t.startsWith("//") ? "com" : KW.has(t) ? "kw" : /^\d/.test(t) ? "num" : word && line[re.lastIndex] === "(" ? "fn" : word ? "id" : "p"]);
  }
  return res;
};

const AgentTag: React.FC<{ c: ReturnType<typeof useCtx>; label: string; size?: number; spin?: number }> = ({ c, label, size = 18, spin = 0 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.35, fontFamily: c.body, fontWeight: 700, fontSize: size, color: "#FFF", background: c.send, borderRadius: `${size * 0.25}px ${size * 0.6}px ${size * 0.6}px ${size * 0.6}px`, padding: `${size * 0.22}px ${size * 0.6}px`, whiteSpace: "nowrap", boxShadow: `0 6px 16px ${c.send}66` }}>
    <Icons.Asterisk size={size * 0.95} color="#FFF" strokeWidth={3} style={{ transform: `rotate(${spin}deg)` } as React.CSSProperties} />{label}
  </div>
);

const Code: React.FC<SP> = ({ g, style, lf, dur, w, h }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const lines = g.items ?? [];
  const instant = g.enter === false;
  const enter = instant ? 1 : c.sp(0, 15);
  const head = 58, foot = 42, gut = 58, mini = 70, pad = 18;
  const LH = Math.min(40, Math.floor((h - head - foot - pad * 2) / Math.max(10, lines.length)));
  const F = Math.round(LH * 0.6), cw = F * 0.6;
  const total = lines.reduce((s, l) => s + l.length + 1, 0);
  const pre = instant ? lines.slice(0, 3).reduce((s, l) => s + l.length + 1, 0) : 0;
  const n = Math.round(pre + (total - pre) * c.ramp(instant ? 0 : 0.15, c.at(0, T * 0.9), 0, 1, (x) => x));
  let left = n, row = 0;
  while (row < lines.length && left > lines[row].length) { left -= lines[row].length + 1; row++; }
  const done = row >= lines.length;
  const caretRow = done ? lines.length - 1 : row;
  const col = done ? (lines.at(-1)?.length ?? 0) : left;
  const colors: Record<string, string> = { kw: c.accent, str: "#0F8A5F", com: "#9CA3AF", num: c.send, fn: style.colors.secondary, id: c.ink, p: c.muted };
  const bodyW = w - mini;
  const codeX = gut + 22;
  const cx = codeX + col * cw, cy = pad + caretRow * LH;
  const file = g.title ?? "app.ts";
  return (
    <div style={{ width: w, height: h, position: "relative", opacity: Math.min(1, enter * 1.5), transform: `translateY(${(1 - enter) * 60}px) scale(${(0.95 + 0.05 * enter) * c.ramp(0, T, 1, 1.03, (x) => x)})` }}>
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", borderRadius: 26, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
        <div style={{ height: head, display: "flex", alignItems: "flex-end", padding: "0 16px", background: "linear-gradient(#FBFCFE, #F1F3F8)", borderBottom: "1px solid rgba(17,24,39,0.07)" }}>
          <div style={{ alignSelf: "center", marginRight: 18 }}><Dots /></div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, height: 44, padding: "0 18px", background: "#FFF", borderRadius: "12px 12px 0 0", border: "1px solid rgba(17,24,39,0.07)", borderBottom: "none", fontFamily: c.body, fontWeight: 600, fontSize: 19, color: c.ink }}>
            <Icons.FileCode2 size={20} color={style.colors.secondary} strokeWidth={2.2} />{file}
            <div style={{ width: 9, height: 9, borderRadius: 5, background: c.send, marginLeft: 4 }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, height: 44, padding: "0 18px", fontFamily: c.body, fontWeight: 500, fontSize: 19, color: "#9CA3AF" }}>
            <Icons.FileCode2 size={20} color="#B6BBC6" strokeWidth={2.2} />db.ts
          </div>
          <div style={{ flex: 1 }} />
          <div style={{ alignSelf: "center", display: "flex", alignItems: "center", gap: 8, fontFamily: c.body, fontWeight: 700, fontSize: 17, color: "#9A4A2F", background: "#FBEFE9", borderRadius: 999, padding: "6px 14px" }}>
            <Icons.Asterisk size={18} color={c.send} strokeWidth={3} style={{ transform: `rotate(${frame * 12}deg)` } as React.CSSProperties} />
            {done ? "Done" : `Writing${".".repeat(1 + (Math.floor(lf / 4) % 3))}`}
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, top: head, width: bodyW, bottom: foot, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: gut + 10, background: "#FAFBFD", borderRight: "1px solid rgba(17,24,39,0.05)" }} />
          {lines.map((l, i) => {
            const typed = i < row ? l : i === row ? l.slice(0, left) : "";
            const ghost = i === row ? l.slice(left) : i > row && i <= row + 2 ? l : "";
            const written = i < row || (i === row && left > 0);
            return (
              <div key={i} style={{ position: "absolute", left: 0, right: 0, top: pad + i * LH, height: LH, display: "flex", alignItems: "center", background: i === caretRow && !done ? `${c.send}14` : undefined }}>
                <div style={{ width: gut, textAlign: "right", fontFamily: c.mono, fontSize: F * 0.82, color: i === caretRow ? c.ink : "#B6BBC6" }}>{i + 1}</div>
                <div style={{ width: 4, height: LH - 10, marginLeft: 6, borderRadius: 2, background: c.ok, opacity: written ? 1 : 0 }} />
                <div style={{ marginLeft: codeX - gut - 10, fontFamily: c.mono, fontSize: F, whiteSpace: "pre", fontWeight: 500 }}>
                  {tokenize(typed).map(([t, k], j) => <span key={j} style={{ color: colors[k], fontWeight: k === "kw" ? 700 : 500, fontStyle: k === "com" ? "italic" : undefined }}>{t}</span>)}
                  <span style={{ color: "#BCC1CB" }}>{ghost}</span>
                </div>
              </div>
            );
          })}
          <div style={{ position: "absolute", left: cx, top: cy + 5, width: 3, height: LH - 10, borderRadius: 2, background: c.send, opacity: done && Math.floor(lf / 8) % 2 ? 0 : 1, boxShadow: `0 0 10px ${c.send}` }} />
          <div style={{ position: "absolute", left: Math.min(cx + 4, bodyW - 160), top: cy + LH - 4 }}><AgentTag c={c} label={g.label ?? "Claude"} size={19} spin={frame * 6} /></div>
        </div>
        <div style={{ position: "absolute", right: 0, top: head, width: mini, bottom: foot, borderLeft: "1px solid rgba(17,24,39,0.05)", padding: "16px 12px" }}>
          {lines.map((l, i) => {
            const k = tokenize(l).find(([, kind]) => kind === "kw" || kind === "str" || kind === "fn")?.[1] ?? "id";
            return <div key={i} style={{ height: 4, width: Math.min(46, l.length * 1.15), marginLeft: (l.length - l.trimStart().length) * 1.15, marginBottom: 4, borderRadius: 2, background: i < row || done ? colors[k] : "#E5E7EB", opacity: 0.75 }} />;
          })}
          <div style={{ position: "absolute", left: 6, right: 6, top: 10, height: 70, borderRadius: 6, background: "rgba(17,24,39,0.05)" }} />
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: foot, display: "flex", alignItems: "center", gap: 10, padding: "0 18px", background: "#F6F7FA", borderTop: "1px solid rgba(17,24,39,0.06)", fontFamily: c.body, fontSize: 16, color: c.muted }}>
          <div style={{ width: 9, height: 9, borderRadius: 5, background: done ? c.ok : c.send, opacity: done ? 1 : 0.55 + 0.45 * Math.abs(Math.sin(frame * 0.35)) }} />
          <span style={{ fontWeight: 600, color: c.ink }}>{g.label ?? "Claude"}</span>{done ? "finished" : "is writing"} {file}
          <div style={{ flex: 1 }} />
          <Icons.GitBranch size={16} color={c.muted} strokeWidth={2.2} />main<span style={{ marginLeft: 14 }}>TypeScript</span>
        </div>
      </div>
    </div>
  );
};

// ---------- role ----------
const Role: React.FC<SP> = ({ g, style, lf, dur, w }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const tasks = g.items ?? [];
  const tone = g.tone ?? "#E5484D";
  const stampAt = c.at(0, T * 0.7);
  const land = c.sp(-0.07, 12);
  const stamp = c.t >= stampAt ? c.sp(stampAt, 9) : 0;
  const hit = (at: number, len = 0.3) => { const k = c.t - at; return k < 0 || k > len ? 0 : Math.pow(1 - k / len, 2); };
  const shakeK = Math.max(hit(0.12, 0.22) * 0.5, hit(stampAt, 0.32));
  const sx = Math.sin(frame * 2.1) * 16 * shakeK, sy = Math.cos(frame * 2.7) * 10 * shakeK;
  const W = Math.min(w, 880), rowH = 112;
  const I = icon(g.icon ?? "Code2");
  const tile = g.color ?? c.accent;
  const stampText = g.stamp ?? "";
  const fs = Math.min(176, 640 / Math.max(1, stampText.length * 0.77));
  const fid = `ink-${stampText.replace(/\W/g, "")}`;
  const face: React.CSSProperties = { position: "absolute", inset: 0, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", gap: 9, fontFamily: c.body, fontWeight: 700, fontSize: 25, backfaceVisibility: "hidden" };
  return (
    <div style={{ width: W, position: "relative", transform: `translate(${sx}px, ${sy}px)` }}>
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <filter id={fid} x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.04 0.07" numOctaves="3" seed="7" result="warp" />
          <feDisplacementMap in="SourceGraphic" in2="warp" scale="7" xChannelSelector="R" yChannelSelector="G" result="rough" />
          <feTurbulence type="fractalNoise" baseFrequency="1.3" numOctaves="1" seed="3" result="grain" />
          <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -4 3.1" result="holes" />
          <feComposite in="rough" in2="holes" operator="in" />
        </filter>
      </svg>
      <div style={{ position: "absolute", left: 40, right: 40, top: 30, bottom: -26, borderRadius: 34, background: "rgba(255,255,255,0.6)", boxShadow: "0 20px 50px -20px rgba(30,40,80,0.25)", opacity: land }} />
      <div style={{ position: "relative", background: "#FFFFFF", borderRadius: 34, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", padding: "38px 40px 22px", overflow: "hidden",
        opacity: Math.min(1, 0.4 + land * 2), transform: `translateY(${(1 - land) * -260}px) scale(${1.08 - 0.08 * land}) rotate(${(1 - land) * -3}deg)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28, paddingBottom: 26 }}>
          <div style={{ position: "relative", width: 136, height: 136, flex: "none", borderRadius: 36, background: `linear-gradient(150deg, ${tile} 0%, ${style.colors.secondary} 100%)`, boxShadow: `0 14px 30px ${tile}55, inset 0 2px 0 rgba(255,255,255,0.35)`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "50%", background: "linear-gradient(180deg, rgba(255,255,255,0.3), rgba(255,255,255,0))" }} />
            <I size={72} color="#FFFFFF" strokeWidth={2.2} />
            <Shine p={c.ramp(0.15, 0.7)} radius={36} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            {g.subtitle && <div style={{ fontFamily: c.body, fontWeight: 700, fontSize: 22, letterSpacing: 3, color: c.muted, textTransform: "uppercase", marginBottom: 6 }}>{g.subtitle}</div>}
            <div style={{ fontFamily: c.font, fontWeight: 800, fontSize: 68, letterSpacing: -2, color: c.ink, lineHeight: 1.02 }}>{g.title}</div>
          </div>
        </div>
        {tasks.map((t, i) => {
          const at = g.marks?.[i + 1];
          const TI = icon(g.icons?.[i] ?? "Check");
          const f = at === undefined ? 0 : c.sp(at, 13);
          const check = at === undefined ? 0 : c.sp(at + 0.07, 10);
          const glow = at === undefined ? 0 : hit(at, 0.45);
          return (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 22, height: rowH, padding: "0 12px", margin: "0 -12px", borderTop: "1px solid rgba(17,24,39,0.07)", background: `rgba(217,119,87,${0.13 * glow})` }}>
              <div style={{ width: 62, height: 62, flex: "none", borderRadius: 18, background: "#F3F4F6", display: "flex", alignItems: "center", justifyContent: "center" }}><TI size={32} color={c.muted} strokeWidth={2.2} /></div>
              <div style={{ flex: 1, fontFamily: c.font, fontWeight: 650, fontSize: 41, color: c.ink, whiteSpace: "nowrap" }}>{t}</div>
              <div style={{ width: 44, height: 44, flex: "none", borderRadius: "50%", background: c.ok, transform: `scale(${check})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 6px 14px ${c.ok}55` }}><Icons.Check size={26} color="#FFF" strokeWidth={3.6} /></div>
              <div style={{ position: "relative", width: 172, height: 60, flex: "none", perspective: 520 }}>
                {at === undefined ? (
                  <div style={{ ...face, border: `2.5px solid ${c.send}`, color: c.send, background: "#FFF8F4" }}>
                    <Icons.Asterisk size={24} color={c.send} strokeWidth={3} style={{ transform: `rotate(${frame * 14}deg)` } as React.CSSProperties} />Working
                  </div>
                ) : (
                  <>
                    <div style={{ ...face, background: "#F3F4F6", border: "1px solid rgba(17,24,39,0.08)", color: c.muted, transform: `rotateX(${180 * f}deg)` }}><Icons.User size={24} color={c.muted} strokeWidth={2.4} />Human</div>
                    <div style={{ ...face, background: `linear-gradient(135deg, #E8906C, ${c.send})`, color: "#FFF", transform: `rotateX(${180 * f - 180}deg)`, boxShadow: `0 8px 18px ${c.send}55` }}><Icons.Asterisk size={24} color="#FFF" strokeWidth={3} />AI</div>
                  </>
                )}
              </div>
            </div>
          );
        })}
        <div style={{ position: "absolute", inset: 0, background: "#FFF", opacity: hit(stampAt, 0.16) * 0.55, pointerEvents: "none" }} />
      </div>
      {stamp > 0 && Array.from({ length: 14 }, (_, i) => {
        const a = (i / 14) * Math.PI * 2 + 0.4;
        const k = c.ramp(stampAt, stampAt + 0.5, 0, 1, out);
        return <div key={i} style={{ position: "absolute", left: W / 2 + Math.cos(a) * (fs * 0.4 * stampText.length + 170 * k) - 7, top: `calc(60% + ${Math.sin(a) * (fs * 0.75 + 120 * k)}px)`, width: 14 - (i % 3) * 3, height: 6 + (i % 2) * 5, borderRadius: 2, background: tone, opacity: (1 - k) * 0.9, transform: `rotate(${a * 57 + k * 140}deg)` }} />;
      })}
      {stamp > 0 && (
        <div style={{ position: "absolute", left: W / 2, top: "60%", transform: `translate(-50%, -50%) rotate(${-15 + 7 * stamp}deg) scale(${1.85 - 0.85 * stamp})`, opacity: Math.min(1, stamp * 3) }}>
          <div style={{ filter: `url(#${fid})`, border: `${Math.round(fs * 0.1)}px solid ${tone}`, borderRadius: fs * 0.2, padding: `${fs * 0.02}px ${fs * 0.28}px`, color: tone, fontFamily: c.font, fontWeight: 900, fontSize: fs, letterSpacing: fs * 0.05, lineHeight: 1.08, whiteSpace: "nowrap", mixBlendMode: "multiply" }}>{stampText}</div>
        </div>
      )}
    </div>
  );
};

// ---------- queue ----------
const Queue: React.FC<SP> = ({ g, style, lf, dur, w }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const items = g.items ?? [];
  const doneAt = c.at(0, T * 0.25), focusAt = c.at(1, T * 0.6);
  const enter = c.sp(-0.07, 14);
  const done = c.t >= doneAt ? c.sp(doneAt, 10) : 0;
  const focus = c.ramp(focusAt, focusAt + 0.24, 0, 1, out);
  const W = Math.min(w, 860), head = 72, rowH = 148;
  const I = icon(g.icon ?? "Code2");
  const pill = (bg: string, fg: string, text: string, el?: React.ReactNode, extra?: React.CSSProperties) => (
    <div style={{ display: "flex", alignItems: "center", gap: 9, height: 60, padding: "0 24px", borderRadius: 999, background: bg, color: fg, fontFamily: c.body, fontWeight: 700, fontSize: 28, whiteSpace: "nowrap", ...extra }}>{el}{text}</div>
  );
  const shimmer = (frame * 3.2) % 200;
  return (
    <div style={{ width: W, position: "relative", opacity: Math.min(1, 0.45 + enter), transform: `translateY(${(1 - enter) * 70}px) scale(${0.95 + 0.05 * enter})` }}>
      <div style={{ position: "relative", background: "#FFFFFF", borderRadius: 30, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", padding: "0 30px 12px", overflow: "hidden" }}>
        <div style={{ height: head, display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid rgba(17,24,39,0.07)", margin: "0 -30px", padding: "0 30px" }}>
          <Icons.Asterisk size={32} color={c.send} strokeWidth={3} style={{ transform: `rotate(${frame * 4}deg)` } as React.CSSProperties} />
          <span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 24, letterSpacing: 3, color: c.muted, textTransform: "uppercase" }}>{g.title ?? "Automation queue"}</span>
          <div style={{ flex: 1 }} />
          <div style={{ width: 10, height: 10, borderRadius: 5, background: c.ok, boxShadow: `0 0 0 ${4 + 3 * Math.sin(frame * 0.4)}px ${c.ok}33` }} />
          <span style={{ fontFamily: c.mono, fontSize: 19, color: c.muted }}>live</span>
        </div>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: -14, right: -14, top: 10 + focus * rowH, height: rowH - 20, borderRadius: 24, border: `3px solid ${c.send}`, boxShadow: `0 0 0 6px ${c.send}22, 0 10px 30px ${c.send}33`, opacity: c.ramp(doneAt + 0.05, doneAt + 0.15) }} />
          {items.map((it, i) => {
            const rp = c.sp(-0.06 + i * 0.05, 15);
            const first = i === 0;
            const strike = c.ramp(doneAt + 0.04, doneAt + 0.26, 0, 1, out);
            const jiggle = i === 1 ? Math.sin(c.t * 38) * 7 * c.ramp(focusAt + 0.1, focusAt + 0.2) * (1 - c.ramp(focusAt + 0.35, focusAt + 0.5)) : 0;
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, height: rowH, borderTop: i ? "1px solid rgba(17,24,39,0.06)" : undefined, opacity: Math.min(1, rp * 1.6), transform: `translateX(${(1 - rp) * -40}px)` }}>
                <span style={{ width: 44, fontFamily: c.mono, fontWeight: 600, fontSize: 26, color: "#B6BBC6" }}>{String(i + 1).padStart(2, "0")}</span>
                <div style={{ width: 92, height: 92, flex: "none", borderRadius: 26, display: "flex", alignItems: "center", justifyContent: "center", transform: `rotate(${jiggle}deg)`,
                  background: first ? `linear-gradient(150deg, ${g.color ?? "#0A84FF"} 0%, ${style.colors.secondary} 100%)` : "#EEF0F4", boxShadow: first ? `0 10px 22px ${(g.color ?? "#0A84FF")}44` : "inset 0 0 0 1px rgba(17,24,39,0.06)" }}>
                  {first ? <I size={48} color="#FFF" strokeWidth={2.3} /> : <Icons.Lock size={40} color={i === 1 && focus > 0.5 ? c.send : "#9CA3AF"} strokeWidth={2.4} />}
                </div>
                <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center", gap: 12 }}>
                  {first ? (
                    <div style={{ position: "relative", fontFamily: c.font, fontWeight: 700, fontSize: 44, color: done > 0.5 ? c.muted : c.ink, whiteSpace: "nowrap" }}>
                      {it}
                      <div style={{ position: "absolute", left: -4, top: "52%", height: 4, borderRadius: 2, width: `calc(${strike * 100}% + 8px)`, background: c.ink, opacity: 0.55 }} />
                    </div>
                  ) : it.split(" ").map((word, j) => (
                    <div key={j} style={{ width: word.length * 25, height: 40, borderRadius: 11, backgroundImage: "linear-gradient(90deg, #E3E6EB 0%, #F4F5F8 50%, #E3E6EB 100%)", backgroundSize: "200% 100%", backgroundPosition: `${200 - shimmer}% 0`, opacity: i === 1 ? 1 : 0.7 }} />
                  ))}
                </div>
                {first && (c.t < doneAt
                  ? pill("#FFF8F4", c.send, "Working", <Icons.Loader2 size={26} color={c.send} strokeWidth={2.8} style={{ transform: `rotate(${frame * 16}deg)` } as React.CSSProperties} />, { border: `2.5px solid ${c.send}` })
                  : pill(c.ok, "#FFF", "Done", <Icons.Check size={28} color="#FFF" strokeWidth={3.6} />, { transform: `scale(${0.6 + 0.4 * done})`, boxShadow: `0 8px 18px ${c.ok}55` }))}
                {i === 1 && pill(c.send, "#FFF", "Next", <div style={{ width: 10, height: 10, borderRadius: 5, background: "#FFF", opacity: 0.5 + 0.5 * Math.abs(Math.sin(frame * 0.3)) }} />, { boxShadow: `0 0 0 ${3 + 4 * Math.abs(Math.sin(frame * 0.3))}px ${c.send}2A` })}
                {i > 1 && pill("#F3F4F6", "#9CA3AF", "Queued")}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ---------- timeline ----------
const Timeline: React.FC<SP> = ({ g, style, lf, dur, w, h }) => {
  const c = useCtx(g, style, lf, dur);
  const frame = useCurrentFrame();
  const T = dur / c.fps;
  const enter = c.sp(-0.07, 15);
  const land = c.at(0, T * 0.35);
  const cuts = (g.marks ?? []).slice(1);
  const cutX = [0.38, 0.62, 0.84].slice(0, cuts.length);
  const stills = (g.clips ?? []).map((x) => x.src);
  const head = 54, pad = 16;
  const monH = Math.round((h - head) * 0.34);
  const tlTop = head + pad + monH + pad, tlH = h - tlTop - pad;
  const labW = 54, ruler = 28;
  const laneW = w - pad * 2 - labW - 14;
  const rows = ["V2", "V1", "A1", "A2"].slice(0, g.tracks ?? 4);
  const laneH = Math.floor((tlH - ruler - 10) / rows.length) - 6;
  const laneY = (r: number) => ruler + 6 + r * (laneH + 6);
  const gapK = (i: number) => (c.t >= cuts[i] ? c.sp(cuts[i], 12) : 0);
  const shift = (fx: number) => cutX.reduce((s, x, i) => s + (fx > x - 0.001 ? gapK(i) * 14 : 0), 0);
  const edges = [0, 0.27, 0.55, 0.79, 1, ...cutX.filter((_, i) => c.t >= cuts[i])].sort((a, b) => a - b);
  const segs = edges.slice(0, -1).map((a, i) => ({ a, b: edges[i + 1] })).filter((s) => s.b - s.a > 0.005);
  // cursor flies in from off the right edge, lands on the first cut, then hops to each next cut
  const tgt = (fx: number) => ({ x: pad + labW + 14 + fx * laneW + shift(fx), y: tlTop + laneY(1) + laneH * 0.55 });
  const fly = c.ramp(0, land, 0, 1, out);
  const p0 = { x: w + 80, y: head + 30 }, p1 = tgt(cutX[0] ?? 0.4);
  let cur = { x: p0.x + (p1.x - p0.x) * fly, y: p0.y + (p1.y - p0.y) * fly - Math.sin(fly * Math.PI) * 60 };
  cutX.forEach((fx, i) => {
    if (i === 0) return;
    const k = c.ramp(cuts[i - 1] + 0.05, cuts[i] - 0.03, 0, 1, inOut);
    if (k > 0) { const a = tgt(cutX[i - 1]), b = tgt(fx); cur = { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k }; }
  });
  const down = cuts.reduce((m, t) => Math.max(m, c.ramp(t - 0.05, t) - c.ramp(t + 0.04, t + 0.1)), 0);
  const flash = cuts.reduce((m, t) => Math.max(m, 1 - Math.min(1, Math.abs(c.t - t) / 0.08)), 0);
  const ai = c.t >= land ? c.sp(land, 12) : 0;
  const monW = Math.round(monH * 16 / 9);
  return (
    <div style={{ width: w, height: h, position: "relative", opacity: Math.min(1, 0.45 + enter), transform: `translateY(${(1 - enter) * 60}px) scale(${(0.95 + 0.05 * enter) * c.ramp(0, T, 1, 1.03, (x) => x)}) translateX(${Math.sin(frame * 2.3) * flash * 3}px)` }}>
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", borderRadius: 26, boxShadow: c.shadow, border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
        <div style={{ height: head, display: "flex", alignItems: "center", gap: 14, padding: "0 16px", background: "linear-gradient(#FBFCFE, #F1F3F8)", borderBottom: "1px solid rgba(17,24,39,0.07)" }}>
          <Dots />
          <Icons.Clapperboard size={20} color={c.muted} strokeWidth={2.2} />
          <span style={{ fontFamily: c.body, fontWeight: 600, fontSize: 18, color: c.ink }}>{g.title ?? "Timeline"}</span>
          <div style={{ flex: 1 }} />
          <div style={{ position: "relative", width: 232, height: 40, perspective: 400 }}>
            <div style={{ position: "absolute", inset: 0, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", gap: 7, fontFamily: c.body, fontWeight: 700, fontSize: 19, background: "#EEF0F5", color: c.muted, backfaceVisibility: "hidden", transform: `rotateX(${180 * ai}deg)` }}><Icons.User size={16} color={c.muted} strokeWidth={2.4} />Editing: you</div>
            <div style={{ position: "absolute", inset: 0, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", gap: 7, fontFamily: c.body, fontWeight: 700, fontSize: 19, background: c.send, color: "#FFF", backfaceVisibility: "hidden", transform: `rotateX(${180 * ai - 180}deg)`, boxShadow: `0 6px 14px ${c.send}55` }}><Icons.Asterisk size={16} color="#FFF" strokeWidth={3} style={{ transform: `rotate(${frame * 10}deg)` } as React.CSSProperties} />{g.label ?? "Claude"} is editing</div>
          </div>
        </div>
        <div style={{ position: "absolute", left: pad, top: head + pad, right: pad, height: monH, display: "flex", gap: pad }}>
          <div style={{ width: monW, height: monH, flex: "none", borderRadius: 14, overflow: "hidden", position: "relative", background: "#0F1117", boxShadow: "0 10px 24px rgba(15,17,23,0.22)" }}>
            {g.src && (
              <Sequence from={frame - lf} layout="none">
                <OffthreadVideo src={staticFile(g.src)} muted startFrom={Math.round((g.from ?? 0) * c.fps)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 22%" }} />
              </Sequence>
            )}
            <div style={{ position: "absolute", inset: 0, background: "#FFF", opacity: flash * 0.5 }} />
            <div style={{ position: "absolute", left: 10, top: 10, fontFamily: c.mono, fontWeight: 700, fontSize: 13, color: "#FFF", background: "rgba(0,0,0,0.5)", borderRadius: 5, padding: "2px 7px" }}>PROGRAM</div>
            <div style={{ position: "absolute", left: 10, bottom: 10, fontFamily: c.mono, fontSize: 14, color: "#FFF", background: "rgba(0,0,0,0.5)", borderRadius: 5, padding: "2px 7px" }}>{`00:00:${String(Math.floor((g.from ?? 0) + c.t)).padStart(2, "0")}:${String(Math.floor(((g.from ?? 0) + c.t) * 30) % 30).padStart(2, "0")}`}</div>
          </div>
          <div style={{ flex: 1, borderRadius: 14, border: "1px solid rgba(17,24,39,0.08)", background: "#FAFBFD", padding: "14px 18px", display: "flex", flexDirection: "column", justifyContent: "space-around" }}>
            {[["Scissors", "Cuts", 0.2, 0.78], ["ZoomIn", "Zoom", 0.35, 0.62], ["Captions", "Captions", 0.1, 0.9]].map(([ic, lb, a, b], i) => {
              const SI = icon(ic as string);
              const v = (a as number) + ((b as number) - (a as number)) * c.ramp(land + 0.05 + i * 0.06, land + 0.35 + i * 0.06, 0, 1, inOut);
              return (
                <div key={lb as string} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <SI size={18} color={c.muted} strokeWidth={2.3} />
                  <span style={{ width: 86, fontFamily: c.body, fontWeight: 600, fontSize: 17, color: c.ink }}>{lb}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: "#E5E7EB", position: "relative" }}>
                    <div style={{ width: `${v * 100}%`, height: "100%", borderRadius: 3, background: ai > 0.5 ? c.send : c.accent }} />
                    <div style={{ position: "absolute", left: `calc(${v * 100}% - 9px)`, top: -6, width: 18, height: 18, borderRadius: 9, background: "#FFF", boxShadow: "0 1px 4px rgba(0,0,0,0.25)", border: "1px solid rgba(17,24,39,0.1)" }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div style={{ position: "absolute", left: pad, right: pad, top: tlTop, height: tlH, borderRadius: 14, background: "#F5F7FB", border: "1px solid rgba(17,24,39,0.07)", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: labW + 14, right: 0, top: 0, height: ruler, borderBottom: "1px solid rgba(17,24,39,0.08)" }}>
            {Array.from({ length: 7 }, (_, i) => (
              <div key={i} style={{ position: "absolute", left: (i * laneW) / 6, height: ruler, borderLeft: "1px solid rgba(17,24,39,0.15)", paddingLeft: 4, fontFamily: c.mono, fontSize: 12, color: "#9CA3AF", lineHeight: `${ruler}px` }}>{`00:0${i}`}</div>
            ))}
          </div>
          {rows.map((r, ri) => (
            <div key={r} style={{ position: "absolute", left: 8, top: laneY(ri), width: labW, height: laneH, borderRadius: 8, background: "#FFF", border: "1px solid rgba(17,24,39,0.07)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: c.mono, fontWeight: 600, fontSize: 14, color: c.muted }}>{r}</div>
          ))}
          <div style={{ position: "absolute", left: labW + 14, top: 0, right: 0, bottom: 0 }}>
            {[[0.03, 0.2, "Title"], [0.58, 0.76, "Graphic"]].map(([a, b, lb]) => (
              <div key={lb as string} style={{ position: "absolute", top: laneY(0), height: laneH, left: (a as number) * laneW + shift(a as number), width: ((b as number) - (a as number)) * laneW, borderRadius: 8, background: "linear-gradient(135deg, #AF52DE, #5856D6)", display: "flex", alignItems: "center", gap: 6, padding: "0 10px", boxShadow: "0 5px 12px rgba(88,86,214,0.3)" }}>
                <Icons.Sparkles size={15} color="#FFF" strokeWidth={2.4} /><span style={{ fontFamily: c.body, fontWeight: 700, fontSize: 14, color: "#FFF" }}>{lb}</span>
              </div>
            ))}
            {segs.map((s, i) => {
              const x = s.a * laneW + shift(s.a), wd = (s.b - s.a) * laneW - 3;
              return (
                <div key={i}>
                  <div style={{ position: "absolute", top: laneY(1), height: laneH, left: x, width: wd, borderRadius: 8, overflow: "hidden", display: "flex", background: "#232733", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.08)" }}>
                    {Array.from({ length: Math.ceil(wd / (laneH * 0.56)) }, (_, j) => stills.length ? <Img key={j} src={staticFile(stills[(i + j) % stills.length])} style={{ height: "100%", width: laneH * 0.56, objectFit: "cover", flex: "none", opacity: 0.92 }} /> : null)}
                  </div>
                  <div style={{ position: "absolute", top: laneY(2), height: laneH, left: x, width: wd, borderRadius: 8, overflow: "hidden", background: "#E3F7EA", border: "1px solid #34C75955", display: "flex", alignItems: "center", gap: 2, padding: "0 4px" }}>
                    {wave(i + 2, Math.max(1, Math.floor(wd / 6))).map((b, j) => <div key={j} style={{ flex: "none", width: 3, height: `${b * 78}%`, borderRadius: 2, background: "#34C759" }} />)}
                  </div>
                </div>
              );
            })}
            {rows.length > 3 && <div style={{ position: "absolute", top: laneY(3), height: laneH, left: 0, width: laneW + shift(1), borderRadius: 8, overflow: "hidden", background: "linear-gradient(90deg, #0A84FF, #5856D6)", display: "flex", alignItems: "center", gap: 3, padding: "0 10px" }}>
              <Icons.Music2 size={16} color="#FFF" strokeWidth={2.6} style={{ flex: "none" }} />
              {wave(9, 110).map((b, j) => <div key={j} style={{ flex: "none", width: 3, height: `${(0.3 + 0.45 * Math.abs(Math.sin(j * 0.33))) * 70}%`, borderRadius: 2, background: "rgba(255,255,255,0.75)" }} />)}
            </div>}
            <div style={{ position: "absolute", top: 0, bottom: 0, left: laneW * 0.16 + c.t * 40, width: 2, background: "#9CA3AF" }}>
              <div style={{ position: "absolute", top: 2, left: -7, width: 16, height: 16, borderRadius: "4px 4px 8px 8px", background: "#9CA3AF" }} />
            </div>
            {cutX.map((fx, i) => {
              const t = cuts[i];
              const p = c.ramp(t - 0.05, t) * (1 - c.ramp(t + 0.2, t + 0.4));
              const sc = c.sp(t - 0.03, 9);
              return (
                <div key={i} style={{ position: "absolute", top: laneY(1) - 8, height: laneH * 2 + 22, left: fx * laneW + shift(fx) - 9, width: 3, background: c.send, opacity: p, boxShadow: `0 0 14px ${c.send}` }}>
                  <div style={{ position: "absolute", top: -30, left: -14, width: 31, height: 31, borderRadius: "50%", background: c.send, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.5 + 0.5 * sc}) rotate(${sc * 90}deg)`, boxShadow: `0 6px 14px ${c.send}66` }}>
                    <Icons.Scissors size={17} color="#FFF" strokeWidth={2.8} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <svg viewBox="0 0 24 34" style={{ position: "absolute", left: cur.x - 4, top: cur.y - 3, width: 34, height: 48, transform: `scale(${1 - 0.15 * down})`, transformOrigin: "10% 5%", filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.3))", zIndex: 50 }}>
        <path d="M2 2 L2 27 L8.2 21.2 L12.4 31 L16.6 29.2 L12.5 19.8 L20.8 19.8 Z" fill={c.send} stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div style={{ position: "absolute", left: cur.x + 24, top: cur.y + 30, zIndex: 51 }}><AgentTag c={c} label={g.label ?? "Claude"} size={22} spin={frame * 6} /></div>
    </div>
  );
};
