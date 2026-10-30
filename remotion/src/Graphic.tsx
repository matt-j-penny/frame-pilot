import * as Icons from "lucide-react";
import { Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { Graphic, Style } from "./types";
import { UIGraphic } from "./UI";
import { SCENE_TYPES, SceneView } from "./Scenes";

const UI_TYPES = new Set(["notifications", "checklist", "chat", "chips", "phone", "title"]);
const UI_SCALE: Record<Variant, number> = { full: 1.15, split: 1.0, overlay: 0.6 };

type Variant = "full" | "split" | "overlay";
const SCALE: Record<Variant, number> = { full: 1.3, split: 1.05, overlay: 0.62 };

const useMotion = (style: Style, lf: number, dur: number, delay = 0, skipIn = false) => {
  const { fps } = useVideoConfig();
  const m = style.motion;
  const p = skipIn ? 1 : spring({ frame: lf - delay, fps, config: { damping: m.spring_damping }, durationInFrames: style.pacing.anim_in_frames + 6 });
  const out = interpolate(lf, [dur - style.pacing.anim_out_frames, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  let transform = "";
  let opacity = Math.min(1, p * 1.4);
  if (m.entrance === "pop") transform = `scale(${0.55 + 0.45 * p})`;
  if (m.entrance === "slide-up") transform = `translateY(${(1 - p) * 90}px)`;
  if (m.entrance === "scale") transform = `scale(${0.88 + 0.12 * p})`;
  if (m.exit === "scale") transform += ` scale(${1 - 0.15 * out})`;
  if (m.exit === "slide-down") transform += ` translateY(${out * 90}px)`;
  opacity *= 1 - out;
  return { transform, opacity };
};

// *word* in a title renders in the accent colour
const Accent: React.FC<{ text: string; color: string }> = ({ text, color }) => (
  <>{text.split(/(\*[^*]+\*)/).map((part, i) => (part.startsWith("*") ? <span key={i} style={{ color }}>{part.slice(1, -1)}</span> : part))}</>
);

const countUp = (value: string, p: number) => {
  const m = value.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
  if (!m) return value;
  const n = parseFloat(m[2].replace(/,/g, ""));
  const decimals = (m[2].split(".")[1] ?? "").length;
  const cur = (n * p).toFixed(decimals);
  return m[1] + (m[2].includes(",") ? Number(cur).toLocaleString("en-US", { minimumFractionDigits: decimals }) : cur) + m[3];
};

export const GraphicView: React.FC<{ g: Graphic; style: Style; lf: number; dur: number; variant: Variant }> = ({ g, style, lf, dur, variant }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const isVideo = /\.(mp4|mov|webm)$/i.test(g.src ?? "");
  const s = SCALE[variant];
  const { fonts, colors, cards } = style;
  const carded = variant === "overlay";
  const fg = carded ? cards.text : colors.text;
  // scenes animate their own entrance; on hard cuts the wrapper must not fade them in from invisible
  const motion = useMotion(style, lf, dur, 0, g.enter === false || (SCENE_TYPES.has(g.type) && style.transitions.fade_frames === 0));
  const head =(size = 1): React.CSSProperties => ({
    fontFamily: fonts.heading.family, fontWeight: fonts.heading.weight, fontSize: fonts.heading.size * s * size,
    letterSpacing: fonts.heading.letter_spacing ?? 0, textTransform: fonts.heading.uppercase ? "uppercase" : "none",
    lineHeight: 1.05, color: fg, textAlign: "center", margin: 0,
  });
  const label = (size = 1): React.CSSProperties => ({
    fontFamily: fonts.label.family, fontWeight: fonts.label.weight, fontSize: fonts.label.size * s * size,
    letterSpacing: fonts.label.letter_spacing ?? 0, textTransform: fonts.label.uppercase ? "uppercase" : "none",
    color: carded ? cards.text : colors.muted ?? colors.text, opacity: 0.85, textAlign: "center", margin: 0, lineHeight: 1.2,
  });
  const card: React.CSSProperties = {
    background: cards.background, borderRadius: cards.radius, boxShadow: cards.shadow, border: cards.border, padding: cards.padding * s,
  };
  const media = (src: string, maxW: number, maxH: number, fit: "contain" | "cover") => (
    <div style={{ ...card, padding: g.type === "logo" ? cards.padding * s : 0, overflow: "hidden", lineHeight: 0, maxWidth: "100%" }}>
      <Img src={staticFile(src)} style={{ maxWidth: "100%", maxHeight: maxH * s, objectFit: fit, objectPosition: "top", display: "block", width: fit === "cover" ? maxW * s : undefined }} />
    </div>
  );

  let body: React.ReactNode = null;
  if (UI_TYPES.has(g.type)) body = <UIGraphic g={g} style={style} lf={lf} dur={dur} u={g.type === "phone" && variant === "split" ? 0.7 : UI_SCALE[variant]} />;
  if (SCENE_TYPES.has(g.type)) body = <SceneView g={g} style={style} lf={lf} dur={dur} w={variant === "split" ? 880 : 980} h={g.h ?? (variant === "split" ? 600 : 930)} />;
  switch (g.type) {
    case "videogrid": {
      // 2-column grid of playing clips; each tile pops in on a stagger and plays its own `from` offset
      const tiles = g.clips ?? [];
      const tw = variant === "split" ? 430 : 440;
      body = (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(2, ${tw}px)`, gap: 22 }}>
          {tiles.map((c, i) => {
            const p = spring({ frame: lf - 2 - i * style.motion.stagger_frames, fps, config: { damping: style.motion.spring_damping } });
            return (
              <div key={i} style={{ width: tw, height: (tw * 9) / 16, borderRadius: cards.radius, overflow: "hidden", boxShadow: cards.shadow, transform: `scale(${0.7 + 0.3 * p})`, opacity: Math.min(1, p * 1.5), background: "#111" }}>
                <Sequence from={frame - lf} layout="none">
                  <OffthreadVideo src={staticFile(c.src)} muted startFrom={Math.round(c.from * fps)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </Sequence>
              </div>
            );
          })}
        </div>
      );
      break;
    }
    case "text":
      body = (
        <>
          {g.title && <h1 style={head()}><Accent text={g.title} color={colors.accent} /></h1>}
          {g.subtitle && <p style={label()}>{g.subtitle}</p>}
        </>
      );
      break;
    case "stat": {
      const p = interpolate(lf, [2, 2 + fps * 0.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (x) => 1 - Math.pow(1 - x, 3) });
      body = (
        <>
          <div style={{ ...head(1.9), color: colors.accent, fontVariantNumeric: "tabular-nums" }}>{countUp(g.value ?? "", p)}</div>
          {g.label && <p style={label(1.1)}>{g.label}</p>}
        </>
      );
      break;
    }
    case "list": {
      const items = g.items ?? [];
      const step = Math.max(style.motion.stagger_frames, Math.floor((dur * 0.6) / Math.max(1, items.length)));
      body = (
        <>
          {g.title && <h2 style={{ ...head(0.75), marginBottom: 24 * s }}><Accent text={g.title} color={colors.accent} /></h2>}
          <div style={{ display: "flex", flexDirection: "column", gap: 22 * s, alignItems: "stretch", width: "100%" }}>
            {items.map((it, i) => (
              <ListItem key={i} i={i} text={it} style={style} lf={lf} dur={dur} delay={4 + i * step} s={s} fg={fg} />
            ))}
          </div>
        </>
      );
      break;
    }
    case "logo":
      body = (
        <>
          {g.src && media(g.src, 520, variant === "split" ? 240 : variant === "overlay" ? 220 : 360, "contain")}
          {g.label && <p style={{ ...label(1.1), marginTop: 28 * s, color: fg }}>{g.label}</p>}
        </>
      );
      break;
    case "image":
    case "screenshot":
      if ((g.scroll || isVideo) && g.src) {
        // browser window: pans a tall full-page capture from scroll[0] to scroll[1] (0 = top, 1 = bottom),
        // or plays a screen recording from `from` seconds; `zoom: [a, b]` scales the content around `origin` over the beat
        const w = variant === "split" ? 880 : 900;
        const h = variant === "split" ? 580 : 900;
        const ease = (x: number) => x * x * (3 - 2 * x);
        const y = g.scroll ? interpolate(lf, [6, dur - 4], g.scroll, { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease }) : 0;
        const z = g.zoom ? interpolate(lf, [0, dur], g.zoom, { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease }) : 1;
        const content: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover", objectPosition: `50% ${y * 100}%`, transform: `scale(${z})`, transformOrigin: g.origin ?? "50% 0%" };
        body = (
          <div style={{ ...card, padding: 0, overflow: "hidden", width: w, height: h, display: "flex", flexDirection: "column" }}>
            <div style={{ flex: "none", height: 54, display: "flex", alignItems: "center", gap: 10, padding: "0 20px", background: "#F3F4F6", borderBottom: cards.border }}>
              {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c }} />)}
              <div style={{ flex: 1, marginLeft: 14, height: 34, borderRadius: 10, background: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fonts.label.family, fontWeight: 500, fontSize: 20, color: colors.muted ?? colors.text }}>{g.url}</div>
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
              {isVideo ? (
                <Sequence from={frame - lf} layout="none">
                  <OffthreadVideo src={staticFile(g.src)} muted startFrom={Math.round((g.from ?? 0) * fps)} style={content} />
                </Sequence>
              ) : <Img src={staticFile(g.src)} style={content} />}
            </div>
          </div>
        );
        break;
      }
      body = (
        <>
          {g.src && media(g.src, g.type === "screenshot" ? 900 : 880, variant === "split" ? 640 : 1000, g.type === "screenshot" ? "cover" : "contain")}
          {g.caption && <p style={{ ...label(), marginTop: 24 * s, color: fg }}>{g.caption}</p>}
        </>
      );
      break;
    case "icon": {
      const Icon = (Icons as unknown as Record<string, React.FC<{ size: number; color: string; strokeWidth: number }>>)[g.icon ?? "Sparkles"] ?? Icons.Sparkles;
      body = (
        <>
          <div style={{ width: 260 * s, height: 260 * s, borderRadius: "50%", background: colors.primary, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 36 * s }}>
            <Icon size={140 * s} color={colors.background} strokeWidth={2.2} />
          </div>
          {g.title && <h2 style={head(0.8)}><Accent text={g.title} color={colors.accent} /></h2>}
          {g.subtitle && <p style={{ ...label(), marginTop: 14 * s }}>{g.subtitle}</p>}
        </>
      );
      break;
    }
    case "quote":
      body = (
        <>
          <div style={{ ...head(2.4), color: colors.accent, lineHeight: 0.6, height: fonts.heading.size * s * 1.1 }}>“</div>
          <p style={{ ...head(0.72), lineHeight: 1.2 }}><Accent text={g.text ?? ""} color={colors.accent} /></p>
          {g.author && <p style={{ ...label(), marginTop: 26 * s }}>— {g.author}</p>}
        </>
      );
      break;
    case "compare":
      body = (
        <div style={{ display: "flex", gap: 28 * s, alignItems: "stretch", width: "100%" }}>
          {[g.left, g.right].map((side, i) => (
            <div key={i} style={{ ...card, flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14 * s, ...useMotion(style, lf, dur, 4 + i * 8) }}>
              {side?.value && <div style={{ ...head(0.95), color: i ? colors.accent : cards.text }}>{side.value}</div>}
              <div style={{ ...label(), color: cards.text }}>{side?.label}</div>
            </div>
          ))}
        </div>
      );
      break;
  }

  return (
    <div style={{ maxWidth: "100%", transform: `translateY(${Math.sin((lf / fps) * Math.PI * 0.5) * (style.detail?.float_px ?? 0)}px)` }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", maxWidth: "100%", ...(carded && !UI_TYPES.has(g.type) && !SCENE_TYPES.has(g.type) ? card : {}), ...(UI_TYPES.has(g.type) || SCENE_TYPES.has(g.type) ? { opacity: motion.opacity } : motion) }}>
        {body}
      </div>
    </div>
  );
};

const ListItem: React.FC<{ i: number; text: string; style: Style; lf: number; dur: number; delay: number; s: number; fg: string }> = ({ i, text, style, lf, dur, delay, s, fg }) => {
  const m = useMotion(style, lf, dur, delay);
  const { fonts, colors } = style;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 26 * s, ...m }}>
      <div style={{ flex: "none", width: 84 * s, height: 84 * s, borderRadius: 22 * s, background: colors.primary, color: colors.background, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fonts.heading.family, fontWeight: fonts.heading.weight, fontSize: 46 * s }}>
        {i + 1}
      </div>
      <div style={{ fontFamily: fonts.heading.family, fontWeight: 600, fontSize: fonts.heading.size * 0.6 * s, color: fg, lineHeight: 1.15 }}>{text}</div>
    </div>
  );
};
