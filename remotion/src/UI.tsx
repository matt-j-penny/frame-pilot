import * as Icons from "lucide-react";
import { Img, interpolate, spring, staticFile, useVideoConfig } from "remotion";
import type { Graphic, Style, UICard } from "./types";

// iOS-style mockups: notifications, checklist, chat box, chips, phone, title card.
// u = UI scale for the variant (1 = full-screen, ~800px wide content).

const ICON_COLORS = ["#FF5A5F", "#FF9F0A", "#34C759", "#0A84FF", "#AF52DE", "#FF2D55", "#5856D6", "#FFB800"];
type IconC = React.FC<{ size: number; color: string; strokeWidth: number }>;
const icon = (name?: string): IconC => ((Icons as unknown as Record<string, IconC>)[name ?? "Sparkles"] ?? Icons.Sparkles);


const stagger = (n: number, dur: number, min = 4) => Math.max(min, Math.floor((dur * 0.55) / Math.max(1, n)));

export const AppIcon: React.FC<{ name?: string; color: string; size: number }> = ({ name, color, size }) => {
  const I = icon(name);
  return (
    <div style={{ flex: "none", width: size, height: size, borderRadius: size * 0.26, background: `linear-gradient(160deg, ${color}, ${color}CC)`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 ${size * 0.08}px ${size * 0.2}px ${color}55` }}>
      <I size={size * 0.52} color="#FFFFFF" strokeWidth={2.4} />
    </div>
  );
};

export const UIGraphic: React.FC<{ g: Graphic; style: Style; lf: number; dur: number; u: number }> = ({ g, style, lf, dur, u }) => {
  const { fps } = useVideoConfig();
  const sp = (delay: number, damping = 14) => spring({ frame: lf - delay, fps, config: { damping }, durationInFrames: 14 });
  const ui = style.ui ?? {};
  const font = style.fonts.heading.family;
  const body = style.fonts.label.family;
  const ink = ui.ink ?? "#111827";
  const muted = ui.muted ?? "#6B7280";
  const card: React.CSSProperties = {
    background: "#FFFFFF", borderRadius: 22 * u, boxShadow: ui.shadow ?? "0 14px 40px rgba(30,40,80,0.14), 0 2px 6px rgba(30,40,80,0.06)",
    border: "1px solid rgba(17,24,39,0.06)",
  };
  const colors = ui.icon_colors ?? ICON_COLORS;

  switch (g.type) {
    case "notifications": {
      const list = g.cards ?? [];
      const step = stagger(list.length, dur);
      // enter: false (hook) draws the first card settled on frame 0
      const t0 = g.enter === false ? -16 : 2;
      const shown = list.filter((_, i) => lf >= t0 + i * step);
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 * u, width: 820 * u }}>
          {shown.slice().reverse().map((c, idx) => {
            const i = shown.length - 1 - idx;
            const p = sp(t0 + i * step);
            return <NotificationRow key={i} c={c} u={u} card={card} color={c.color ?? colors[i % colors.length]} p={p} font={font} body={body} ink={ink} muted={muted} />;
          })}
        </div>
      );
    }
    case "checklist": {
      const items = g.items ?? [];
      const step = stagger(items.length, dur, 6);
      const start = Math.round(fps * 0.3);
      return (
        <div style={{ ...card, width: 620 * u, padding: `${26 * u}px ${30 * u}px`, transform: `scale(${0.9 + 0.1 * sp(0)})` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 * u, marginBottom: 14 * u }}>
            <Icons.Search size={26 * u} color={ui.accent ?? "#5B5BD6"} strokeWidth={2.6} />
            <span style={{ fontFamily: body, fontWeight: 700, fontSize: 22 * u, letterSpacing: 2 * u, color: muted }}>{(g.title ?? "Test run").toUpperCase()}</span>
          </div>
          {items.map((it, i) => {
            const done = sp(start + (i + 1) * step, 12);
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 18 * u, padding: `${14 * u}px 0`, borderTop: i ? "1px solid rgba(17,24,39,0.07)" : undefined }}>
                <div style={{ position: "relative", width: 36 * u, height: 36 * u, flex: "none" }}>
                  <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: `${3 * u}px solid #D1D5DB` }} />
                  <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: ui.success ?? "#22C55E", transform: `scale(${done})`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icons.Check size={24 * u} color="#FFFFFF" strokeWidth={3.5} />
                  </div>
                </div>
                <span style={{ fontFamily: font, fontWeight: 600, fontSize: 32 * u, color: ink }}>{it}</span>
              </div>
            );
          })}
        </div>
      );
    }
    case "chat": {
      const text = g.text ?? "";
      const typeEnd = Math.max(6, Math.round(dur * (g.items?.length ? 0.4 : 0.7)));
      const n = Math.round(interpolate(lf, [4, typeEnd], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
      const caret = Math.floor(lf / 8) % 2 === 0 && n < text.length;
      const panel = sp(typeEnd + 4);
      const chips = g.items ?? [];
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 * u, width: 820 * u }}>
          <div style={{ ...card, padding: `${28 * u}px ${30 * u}px ${22 * u}px`, transform: `scale(${0.92 + 0.08 * sp(0)})` }}>
            <div style={{ fontFamily: body, fontSize: 34 * u, color: n ? ink : "#9CA3AF", minHeight: 48 * u, fontWeight: 500 }}>
              {n ? text.slice(0, n) : g.subtitle ?? "Reply to Claude..."}
              {caret && <span style={{ color: ui.accent ?? "#D97757" }}>|</span>}
            </div>
            <div style={{ display: "flex", alignItems: "center", marginTop: 26 * u, gap: 14 * u }}>
              <div style={{ width: 40 * u, height: 40 * u, borderRadius: 10 * u, border: "1px solid #E5E7EB", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icons.Plus size={22 * u} color={muted} strokeWidth={2.4} />
              </div>
              <div style={{ flex: 1 }} />
              <span style={{ fontFamily: body, fontSize: 22 * u, color: muted }}>{g.label ?? "Opus 5.5"} ⌄</span>
              <div style={{ width: 46 * u, height: 46 * u, borderRadius: 12 * u, background: ui.send ?? "#D97757", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icons.ArrowUp size={26 * u} color="#FFFFFF" strokeWidth={3} />
              </div>
            </div>
          </div>
          {chips.length > 0 && (
            <div style={{ ...card, padding: `${22 * u}px ${26 * u}px`, opacity: panel, transform: `translateY(${(1 - panel) * 30 * u}px)` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 * u, marginBottom: 16 * u }}>
                <Icons.Asterisk size={30 * u} color={ui.send ?? "#D97757"} strokeWidth={3} />
                <span style={{ fontFamily: font, fontWeight: 700, fontSize: 30 * u, color: ink, flex: 1 }}>{g.title ?? "Done"}</span>
                <div style={{ width: 34 * u, height: 34 * u, borderRadius: "50%", background: ui.success ?? "#22C55E", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${sp(typeEnd + 4 + chips.length * 3)})` }}>
                  <Icons.Check size={22 * u} color="#FFFFFF" strokeWidth={3.5} />
                </div>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 * u }}>
                {chips.map((c, i) => (
                  <span key={i} style={{ fontFamily: style.fonts.mono?.family ?? body, fontSize: 21 * u, color: "#9A4A2F", background: "#FBEFE9", borderRadius: 8 * u, padding: `${6 * u}px ${12 * u}px`, opacity: interpolate(lf, [typeEnd + 6 + i * 3, typeEnd + 9 + i * 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{c}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }
    case "chips": {
      const items = g.items ?? [];
      const step = stagger(items.length, dur, 5);
      const pill = ui.pill_colors ?? ["#F0524A", "#F0524A", "#F0524A"];
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 * u, width: 860 * u }}>
          {g.title && <div style={{ fontFamily: font, fontWeight: 700, fontSize: 46 * u, color: ink, textAlign: "center" }}>{g.title}</div>}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 16 * u }}>
            {items.map((it, i) => {
              const p = sp(3 + i * step, 11);
              const I = icon(g.icons?.[i] ?? "Flame");
              return (
                <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 10 * u, fontFamily: font, fontWeight: 700, fontSize: 32 * u, color: "#FFFFFF", background: pill[i % pill.length], borderRadius: 999, padding: `${14 * u}px ${26 * u}px`, boxShadow: `0 8px 22px ${pill[i % pill.length]}55`, transform: `scale(${0.4 + 0.6 * p})`, opacity: Math.min(1, p * 1.5) }}>
                  <I size={30 * u} color="#FFFFFF" strokeWidth={2.6} />
                  {it}
                </span>
              );
            })}
          </div>
        </div>
      );
    }
    case "phone": {
      const p = sp(0, 15);
      const W = 400 * u, H = 820 * u;
      const items = g.items ?? [];
      const step = stagger(items.length, dur, 2);
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 * u, transform: `translateY(${(1 - p) * 120 * u}px) scale(${0.9 + 0.1 * p})`, opacity: Math.min(1, p * 1.5) }}>
          <div style={{ width: W, height: H, borderRadius: 64 * u, background: "#111", padding: 12 * u, boxShadow: "0 30px 80px rgba(30,40,80,0.30)" }}>
            <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 54 * u, overflow: "hidden", background: g.src ? "#FFF" : ui.phone_bg ?? "linear-gradient(170deg, #7B6CF6 0%, #B07CF0 100%)" }}>
              {g.src ? (
                <Img src={staticFile(g.src)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
              ) : (
                <div style={{ position: "absolute", top: 120 * u, left: 26 * u, right: 26 * u, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", rowGap: 30 * u, justifyItems: "center" }}>
                  {items.map((name, i) => (
                    <div key={i} style={{ transform: `scale(${sp(4 + i * step, 12)})` }}>
                      <AppIcon name={name} color={colors[i % colors.length]} size={70 * u} />
                    </div>
                  ))}
                </div>
              )}
              <div style={{ position: "absolute", top: 14 * u, left: "50%", width: 120 * u, height: 34 * u, marginLeft: -60 * u, borderRadius: 20 * u, background: "#111" }} />
              {!g.src && <div style={{ position: "absolute", top: 58 * u, width: "100%", textAlign: "center", fontFamily: font, fontWeight: 600, fontSize: 26 * u, color: "#FFF" }}>9:41</div>}
            </div>
          </div>
          {g.title && <div style={{ fontFamily: font, fontWeight: 700, fontSize: 40 * u, color: ink }}>{g.title}</div>}
        </div>
      );
    }
    case "title": {
      const p = sp(0, 12);
      const c = g.color ?? "#FFFFFF";
      const size = Math.min(190, 1150 / Math.max(1, (g.title ?? "").length)) * u;
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${0.8 + 0.2 * p})`, opacity: Math.min(1, p * 1.5) }}>
          <div style={{ fontFamily: font, fontWeight: 900, fontSize: size, letterSpacing: -size / 32, lineHeight: 1, color: c, textShadow: "0 12px 40px rgba(0,0,0,0.25)" }}>{g.title}</div>
          {g.echo && <div style={{ fontFamily: font, fontWeight: 900, fontSize: size, letterSpacing: -size / 32, lineHeight: 1, color: "transparent", WebkitTextStroke: `${3 * u}px ${c}AA`, opacity: interpolate(lf, [6, 14], [0, 0.8], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{g.title}</div>}
          {g.subtitle && <div style={{ fontFamily: body, fontWeight: 600, fontSize: 40 * u, color: c, opacity: 0.85, marginTop: 20 * u }}>{g.subtitle}</div>}
        </div>
      );
    }
  }
  return null;
};

const NotificationRow: React.FC<{ c: UICard; u: number; card: React.CSSProperties; color: string; p: number; font: string; body: string; ink: string; muted: string }> = ({ c, u, card, color, p, font, body, ink, muted }) => (
  <div style={{ ...card, display: "flex", alignItems: "center", gap: 20 * u, padding: `${18 * u}px ${22 * u}px`, transform: `translateY(${(1 - p) * -40 * u}px) scale(${0.94 + 0.06 * p})`, opacity: Math.min(1, p * 1.5) }}>
    <AppIcon name={c.icon} color={color} size={62 * u} />
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontFamily: font, fontWeight: 700, fontSize: 30 * u, color: ink }}>{c.title}</div>
      <div style={{ fontFamily: body, fontSize: 25 * u, color: muted, marginTop: 2 * u }}>
        {c.subtitle}
        {c.value && <span style={{ color: "#E5484D", fontWeight: 700 }}>{c.subtitle ? " · " : ""}{c.value}</span>}
      </div>
    </div>
    <span style={{ alignSelf: "flex-start", fontFamily: body, fontSize: 20 * u, color: "#9CA3AF" }}>{c.meta ?? "now"}</span>
  </div>
);
