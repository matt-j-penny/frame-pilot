import { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, Video, cancelRender, continueRender, delayRender,
  interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import { Captions, beatAt } from "./Captions";
import { GraphicView } from "./Graphic";
import { SCENE_TYPES, SceneView } from "./Scenes";
import { ShaderBg } from "./Shader";
import type { Beat, FontSpec, Layout, Props, Style } from "./types";

type Rect = { x: number; y: number; w: number; h: number };

const useFonts = (style: Style) => {
  const [handle] = useState(() => delayRender("fonts"));
  useEffect(() => {
    const seen = new Set<string>();
    const jobs = Object.values(style.fonts).filter((f): f is FontSpec => !!f)
      .filter((f) => !seen.has(f.family + f.file) && seen.add(f.family + f.file))
      .map((f) => loadFont({ family: f.family, url: staticFile(`style/${f.file}`), weight: f.weight_range ?? "100 900" }));
    Promise.all(jobs).then(() => continueRender(handle)).catch((e) => cancelRender(e));
  }, [handle, style]);
};

export const Background: React.FC<{ style: Style; variant?: string }> = ({ style, variant }) => {
  const bg = (variant && style.backgrounds?.[variant]) || style.background;
  const file = bg.file ? staticFile(`style/${bg.file}`) : null;
  const isVideo = !!bg.file && /\.(mp4|mov|webm)$/i.test(bg.file);
  return (
    <AbsoluteFill style={{ backgroundColor: bg.color, backgroundImage: bg.css ?? undefined, backgroundSize: bg.size ?? undefined }}>
      {file && isVideo && <Video src={file} loop muted style={{ width: "100%", height: "100%", objectFit: "cover", opacity: bg.opacity ?? 1 }} />}
      {file && !isVideo && <Img src={file} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: bg.opacity ?? 1 }} />}
      {bg.shader && <ShaderBg preset={bg.shader} colors={bg.shader_colors ?? [bg.color, style.colors.primary, style.colors.secondary, "#FFFFFF"]} grain={style.detail?.grain} />}
    </AbsoluteFill>
  );
};

const footageRect = (layout: Layout, style: Style, W: number, H: number): Rect => {
  if (layout !== "split") return { x: 0, y: 0, w: W, h: H };
  const h = Math.round(H * style.split.ratio);
  return { x: 0, y: style.split.speaker === "top" ? 0 : H - h, w: W, h };
};

const lerp = (a: Rect, b: Rect, k: number): Rect => ({
  x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, w: a.w + (b.w - a.w) * k, h: a.h + (b.h - a.h) * k,
});

export const Reel: React.FC<Props> = ({ style, beats, words, music, duration, layer }) => {
  useFonts(style);
  const frame = useCurrentFrame();
  const { fps, width: W, height: H, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const bi = beatAt(beats, t);
  const beat = beats[bi];
  const prev = bi > 0 ? beats[bi - 1] : null;
  const lf = frame - Math.round(beat.start * fps);
  const dur = Math.max(1, Math.round((beat.end - beat.start) * fps));
  const T = style.transitions.duration_frames;
  const ease = Easing.bezier(0.22, 1, 0.36, 1);

  const target = footageRect(beat.layout, style, W, H);
  const from = prev ? footageRect(prev.layout, style, W, H) : target;
  const k = beat.transition === "cut" ? 1 : interpolate(lf, [0, T], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const r = lerp(from, target, k);

  const zoom = beat.zoom ?? 1;
  let scale = style.pacing.punch_style === "ease"
    ? interpolate(lf, [0, dur], [prev?.zoom ?? 1, zoom], { extrapolateRight: "clamp" })
    : zoom;
  let shift = 0;
  let blur = 0;
  if (beat.transition === "zoom") scale *= interpolate(lf, [0, T], [1.12, 1], { extrapolateRight: "clamp", easing: ease });
  if (beat.transition === "whip") {
    shift = interpolate(lf, [0, T], [W * 0.35, 0], { extrapolateRight: "clamp", easing: ease });
    blur = interpolate(lf, [0, T], [18, 0], { extrapolateRight: "clamp" });
  }
  const faceY = `${style.split.face_y * 100}%`;

  const speech = useMemo(() => {
    const on = new Float32Array(durationInFrames);
    for (const w of words) {
      for (let f = Math.max(0, Math.floor((w.start - 0.15) * fps)); f < Math.min(durationInFrames, Math.ceil((w.end + 0.25) * fps)); f++) on[f] = 1;
    }
    const sm = new Float32Array(durationInFrames);
    const win = 6;
    for (let f = 0; f < durationInFrames; f++) {
      let s = 0, n = 0;
      for (let j = f - win; j <= f + win; j++) if (j >= 0 && j < durationInFrames) { s += on[j]; n++; }
      sm[f] = s / n;
    }
    return sm;
  }, [words, fps, durationInFrames]);

  const base = music?.volume ?? style.audio.music_volume;
  const fadeOut = (style.audio.music_fade_out_s ?? 1) * fps;
  const musicVolume = (f: number) =>
    (base + (style.audio.duck_volume - base) * (speech[f] ?? 0)) *
    interpolate(f, [durationInFrames - fadeOut, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const region: Rect = beat.layout === "split"
    ? { x: 0, y: style.split.speaker === "top" ? r.y + r.h : 0, w: W, h: H - r.h }
    : { x: 0, y: 0, w: W, h: H };

  if (layer === "graphics") {
    return (
      <AbsoluteFill>
        {beat.graphic && beat.layout !== "talking_head" && (
          <BeatLayer key={beat.id} beat={beat} style={style} region={region} lf={lf} dur={dur} prevLayout={prev?.layout} />
        )}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ backgroundColor: style.colors.background }}>
      <Background style={style} />
      <div style={{ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h, overflow: "hidden" }}>
        <OffthreadVideo
          src={staticFile("cut.mp4")}
          style={{
            width: "100%", height: "100%", objectFit: "cover", objectPosition: `50% ${faceY}`,
            transform: `translateX(${shift}px) scale(${scale})`, transformOrigin: `50% ${faceY}`,
            filter: blur ? `blur(${blur}px)` : undefined,
          }}
        />
      </div>
      {beat.layout === "split" && style.split.divider && (
        <div style={{ position: "absolute", left: 0, width: W, height: 6, top: (style.split.speaker === "top" ? r.y + r.h : r.y) - 3, background: style.split.divider }} />
      )}
      {beat.graphic && beat.layout !== "talking_head" && (
        <BeatLayer key={beat.id} beat={beat} style={style} region={region} lf={lf} dur={dur} prevLayout={prev?.layout} />
      )}
      <Captions words={words} beats={beats} style={style} />
      {music && <Audio src={staticFile(`music/${music.file}`)} loop startFrom={Math.round((music.from ?? 0) * fps)} volume={musicVolume} />}
      {beats.flatMap((b) => b.sfx ?? []).map((s, i) => {
        // `dur` trims a long hit/tail, with a 4-frame fade so it doesn't click
        const v = s.volume ?? style.audio.sfx_volume, end = s.dur ? Math.round(s.dur * fps) : 0;
        return (
          <Sequence key={i} from={Math.round(s.at * fps)} durationInFrames={end || undefined} layout="none">
            <Audio src={staticFile(`sfx/${s.file}`)} volume={end ? (f) => v * interpolate(f, [end - 4, end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : v} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const BeatLayer: React.FC<{ beat: Beat; style: Style; region: Rect; lf: number; dur: number; prevLayout?: Layout }> = ({ beat, style, region, lf, dur, prevLayout }) => {
  const { pacing } = style;
  const { width: W, height: H, fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const safe = style.safe_zone ?? { top: 220, bottom: 420, right: 130 };
  const g = beat.graphic!;
  // transitions.fade_frames: 0 = hard cut into fullscreen graphics (default: fade over anim_in_frames)
  const fade = style.transitions.fade_frames ?? pacing.anim_in_frames;
  const fadeIn = (keep: boolean) => (keep || fade === 0 ? 1 : interpolate(lf, [0, fade], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  if (g.type === "template" && g.src) {
    // pre-rendered HyperFrames template (reel.py template-render): full canvas, alpha kept, its own SFX
    return (
      <Sequence from={frame - lf} layout="none">
        <OffthreadVideo src={staticFile(g.src)} transparent volume={style.audio.sfx_volume} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      </Sequence>
    );
  }
  if (beat.layout === "fullscreen" && g.fill && g.src && g.fit === "width") {
    // landscape clip shown large: full canvas width (slightly overscanned), slow push-in, centred above the captions
    const z = interpolate(lf, [0, dur], g.zoom ?? [1.1, 1.2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const enter = fadeIn(false);
    return (
      <AbsoluteFill style={{ opacity: enter }}>
        <Background style={style} variant={beat.bg} />
        <div style={{ position: "absolute", left: 0, width: W, top: H * 0.42 - (W * 9) / 32, height: (W * 9) / 16, transform: `scale(${z})`, boxShadow: "0 40px 120px rgba(0,0,0,0.45)" }}>
          <Sequence from={frame - lf} layout="none">
            <OffthreadVideo src={staticFile(g.src)} muted startFrom={Math.round((g.from ?? 0) * fps)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </Sequence>
        </div>
      </AbsoluteFill>
    );
  }
  if (beat.layout === "fullscreen" && g.fill && g.src) {
    // full-bleed screen recording, no card or browser frame
    return (
      <Sequence from={frame - lf} layout="none">
        <OffthreadVideo src={staticFile(g.src)} muted startFrom={Math.round((g.from ?? 0) * fps)} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover" }} />
      </Sequence>
    );
  }
  if (beat.layout === "fullscreen" && SCENE_TYPES.has(g.type) && g.full) {
    // hero scene filling the whole canvas, drawn at 1/K and scaled up so UI text stays readable
    const K = 1.2, bw = W - 60, bh = H - 220;
    const enter = fadeIn(prevLayout === "fullscreen");
    return (
      <AbsoluteFill style={{ opacity: enter }}>
        <Background style={style} variant={beat.bg} />
        <div style={{ position: "absolute", left: 30, top: 110, width: bw / K, height: bh / K, transform: `scale(${K})`, transformOrigin: "0 0" }}>
          <SceneView g={g} style={style} lf={lf} dur={dur} w={Math.round(bw / K)} h={Math.round(bh / K)} />
        </div>
      </AbsoluteFill>
    );
  }
  if (beat.layout === "fullscreen" && SCENE_TYPES.has(g.type)) {
    // hero scene: wider box than regular graphics, stops above the caption line
    const top = safe.top + 10, bottom = style.captions.y.fullscreen * H - 80;
    const enter = fadeIn(prevLayout === "fullscreen");
    return (
      <AbsoluteFill style={{ opacity: enter }}>
        <Background style={style} variant={beat.bg} />
        <div style={{ position: "absolute", left: 50, width: W - 100, top, height: bottom - top, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <SceneView g={g} style={style} lf={lf} dur={dur} w={W - 100} h={Math.round(bottom - top)} />
        </div>
      </AbsoluteFill>
    );
  }
  if (beat.layout === "fullscreen") {
    const enter = fadeIn(prevLayout === "fullscreen");
    const slide = beat.transition === "slide" ? (1 - interpolate(lf, [0, pacing.anim_in_frames], [0, 1], { extrapolateRight: "clamp" })) * W : 0;
    return (
      <AbsoluteFill style={{ opacity: beat.transition === "slide" ? 1 : enter, transform: `translateX(${slide}px)` }}>
        <Background style={style} variant={beat.bg} />
        <div style={{ position: "absolute", left: 70, right: safe.right, top: safe.top + 40, bottom: Math.max(safe.bottom + 140, (1 - style.captions.y.fullscreen) * H + 70), display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ zoom: g.scale ?? 1 }}><GraphicView g={g} style={style} lf={lf} dur={dur} variant="full" /></div>
        </div>
      </AbsoluteFill>
    );
  }
  if (beat.layout === "split") {
    const top = Math.max(region.y, safe.top) + 30;
    const bottom = Math.min(region.y + region.h - (style.split.speaker === "bottom" ? 60 : 0), H - safe.bottom) - 30;
    return (
      <>
        <div style={{ position: "absolute", left: region.x, top: region.y, width: region.w, height: region.h, overflow: "hidden" }}>
          <Background style={style} variant={beat.bg} />
        </div>
        <div style={{ position: "absolute", left: 60, right: safe.right, top, height: Math.max(0, bottom - top), display: "flex", alignItems: "center", justifyContent: "center" }}>
          <GraphicView g={g} style={style} lf={lf} dur={dur} variant="split" />
        </div>
      </>
    );
  }
  const center = g.position === "center";
  return (
    <div style={{ position: "absolute", left: 70, right: safe.right, top: g.y != null ? H * g.y : g.position === "bottom" ? H * 0.5 : center ? H * 0.365 : safe.top + 50, display: "flex", justifyContent: g.align === "left" ? "flex-start" : g.align === "right" ? "flex-end" : "center" }}>
      <div style={{ zoom: g.scale ?? 1 }}><GraphicView g={g} style={style} lf={lf} dur={dur} variant="overlay" /></div>
    </div>
  );
};
