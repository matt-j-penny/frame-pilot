export type Layout = "talking_head" | "split" | "fullscreen" | "overlay";

export type FontSpec = { family: string; file: string; weight: number; size: number; weight_range?: string; letter_spacing?: number; uppercase?: boolean };

export type Bg = { color: string; file?: string | null; css?: string | null; size?: string | null; opacity?: number; shader?: "aurora" | "silk" | "glass"; shader_colors?: string[] };

export type Style = {
  name: string;
  canvas: { width: number; height: number; fps: number };
  fonts: { heading: FontSpec; caption: FontSpec; label: FontSpec; mono?: FontSpec; [k: string]: FontSpec | undefined };
  colors: { primary: string; secondary: string; accent: string; text: string; highlight: string; background: string; muted?: string };
  background: Bg;
  backgrounds?: Record<string, Bg>;
  ui?: { ink?: string; muted?: string; accent?: string; success?: string; send?: string; shadow?: string; icon_colors?: string[]; pill_colors?: string[]; phone_bg?: string };
  layouts: Record<Layout, number>;
  split: { speaker: "top" | "bottom"; ratio: number; face_y: number; divider?: string | null };
  pacing: { punch_in_scale: number; punch_style: "cut" | "ease"; anim_in_frames: number; anim_out_frames: number };
  motion: { entrance: "pop" | "slide-up" | "fade" | "scale"; exit: "fade" | "scale" | "slide-down"; stagger_frames: number; spring_damping: number };
  cards: { background: string; text: string; radius: number; shadow: string; border: string; padding: number };
  captions: {
    enabled: boolean;
    mode: "word" | "phrase";
    words_per_line: number;
    max_lines?: number;
    y: Record<Layout, number>;
    uppercase: boolean;
    color: string;
    highlight: { type: "none" | "color" | "box" | "scale" | "underline"; color: string; box_color?: string; scale?: number };
    box?: { color: string; radius: number; padding_x: number; padding_y: number } | null;
    emphasis_color: string;
    emphasis_scale?: number;
    stroke?: { width: number; color: string } | null;
    shadow?: string | null;
    pop_frames?: number;
    break_on_beats?: boolean;
  };
  transitions: { duration_frames: number; fade_frames?: number };
  audio: { music_volume: number; duck_volume: number; sfx_volume: number; lufs: number; music_fade_out_s?: number };
  safe_zone?: { top: number; bottom: number; right: number };
  detail?: { float_px?: number; grain?: number };
};

export type Graphic = {
  type: "text" | "stat" | "list" | "logo" | "image" | "screenshot" | "icon" | "quote" | "compare"
    | "notifications" | "checklist" | "chat" | "chips" | "phone" | "title" | "videogrid"
    | "repo" | "editor" | "desktop" | "comment" | "badge" | "aiedit" | "code" | "role" | "queue" | "timeline" | "template";
  marks?: number[];
  h?: number;
  y?: number;
  tracks?: number;
  full?: boolean;
  enter?: boolean;
  stamp?: string;
  tone?: string;
  repo?: string;
  cards?: UICard[];
  icons?: string[];
  color?: string;
  echo?: boolean;
  title?: string;
  subtitle?: string;
  value?: string;
  label?: string;
  items?: string[];
  src?: string;
  caption?: string;
  scroll?: [number, number];
  url?: string;
  from?: number;
  zoom?: [number, number];
  origin?: string;
  fill?: boolean;
  fit?: "width";
  clips?: { src: string; from: number }[];
  icon?: string;
  text?: string;
  author?: string;
  left?: { label: string; value?: string };
  right?: { label: string; value?: string };
  position?: "top" | "center";
  align?: "left" | "right";
  scale?: number;
};

export type UICard = { icon?: string; title: string; subtitle?: string; value?: string; meta?: string; color?: string };

export type Beat = {
  bg?: string;
  id: number;
  start: number;
  end: number;
  text: string;
  layout: Layout;
  zoom?: number;
  transition?: "cut" | "zoom" | "slide" | "whip";
  graphic?: Graphic;
  emphasis?: string[];
  captions?: boolean;
  emoji?: string;
  sfx?: { file: string; at: number; volume?: number; dur?: number }[];
};

export type Word = { i: number; word: string; start: number; end: number };

export type Props = {
  style: Style;
  beats: Beat[];
  words: Word[];
  music: { file: string; volume?: number; from?: number } | null;
  duration: number;
  layer?: "graphics";
};
