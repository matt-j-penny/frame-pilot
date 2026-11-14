#!/usr/bin/env python3
"""45 starter video effects for Claude, by @vibha.in.progress (rebranded for Applied AI Mastermind)

One effect:    python fx.py orbit in.mp4 out.mp4 --start 3.2 --end 6
Many effects:  python fx.py --plan plan.json in.mp4 out.mp4
Quick check:   python fx.py --plan plan.json in.mp4 check.png --still 4.5
List them:     python fx.py --list
"""
import argparse, json, math, os, random, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = {k: os.path.join(ROOT, 'fonts', v) for k, v in {  # brand: Cabinet Grotesk display, Satoshi body (Applied AI Mastermind)
    'bold': 'CabinetGrotesk-ExtraBold.otf', 'serif': 'CabinetGrotesk-Bold.otf', 'mono': 'SpaceMono-Bold.ttf',
    'hand': 'PermanentMarker-Regular.ttf', 'ui': 'Satoshi-Medium.otf', 'uim': 'Satoshi-Medium.otf', 'uib': 'Satoshi-Bold.otf',
    'anton': 'CabinetGrotesk-ExtraBold.otf', 'mont': 'CabinetGrotesk-Bold.otf', 'monts': 'CabinetGrotesk-Bold.otf', 'montb': 'CabinetGrotesk-ExtraBold.otf',
    'didone': 'CabinetGrotesk-Bold.otf', 'didoneb': 'CabinetGrotesk-ExtraBold.otf', 'didonei': 'CabinetGrotesk-Bold.otf'}.items()}
WGHT = {}
CREAM, INK, PEACH, YELLOW = (243, 240, 255), (26, 26, 46), (243, 240, 255), (167, 139, 250)
NAMES = ['The Noise', 'The Lineup', 'Locked On', 'Orbit', 'Lean-In', 'Backdrop Word', 'Spotlight', 'The Bill',
         'Moody', 'Swipe', 'The To-Do', 'Comment Box', 'The Tap', 'Pause & Point', 'Uninstall', 'Reel Frame',
         'Shortcut Rain', 'Reject Stamp', 'Countdown Flip', 'Rabbit Hole', 'Cover Star', 'Scribble']
EFFECTS = {}
ALIASES = {'the-noise': 'noise', 'the-lineup': 'lineup', 'bill': 'the-bill', 'to-do': 'todo', 'the-todo': 'todo', 'the-to-do': 'todo',
           'the-tap': 'tap', 'follow': 'tap', 'comment': 'comment-box', 'pause': 'pause-point', 'pause-and-point': 'pause-point',
           'backdrop': 'backdrop-word', 'stamp': 'reject-stamp', 'countdown': 'countdown-flip', 'cover': 'cover-star', 'rain': 'shortcut-rain',
           'glass': 'glass-widgets', 'widgets': 'glass-widgets', 'collage': 'red-collage', 'split': 'split-headline', 'pastel': 'pastel-word',
           'pills': 'check-pills', 'auto-edit': 'timeline', 'headline': 'headline-box', 'wall': 'profile-wall', 'tiers': 'tier-list',
           'tier': 'tier-list', 'broll': 'broll-split', 'b-roll': 'broll-split', 'fan': 'phone-fan', 'dots': 'dot-reveal',
           'headlines': 'headline-wall', 'tasks': 'checklist',
           'liquid-glass': 'liquid-glass-graph', 'glass-graph': 'liquid-glass-graph', 'carousel': 'carousel-spin', 'match': 'match-cut',
           'toggles': 'apple-toggles', 'led': 'led-sign', 'push': 'slow-push', 'push-in': 'slow-push',
           'ots': 'over-the-shoulder-zoom', 'shoulder-zoom': 'over-the-shoulder-zoom', 'corner-zoom': 'over-the-shoulder-zoom',
           'tape': 'tape-label', 'select': 'select-resize', 'resize': 'select-resize', 'trim': 'wave-trim', 'strike': 'huge-strike', 'crayon': 'crayon-write', 'deal': 'fan-build', 'imessage': 'messages', 'texts': 'messages', 'notifications': 'messages', 'grid': 'place-in-grid', 'profile-grid': 'place-in-grid'}
LOOK_NAMES = {'glitter-spotlight': ('spotlight', 'sparkle'), 'glitter': ('spotlight', 'sparkle')}  # a named look of another effect
CARD_FX = ('fan-build', 'noise', 'orbit', 'carousel-spin', 'place-in-grid', 'check-pills', 'profile-wall', 'phone-fan', 'broll-split', 'timeline')


def effect(name, desc):
    def deco(fn):
        EFFECTS[name] = (fn, desc)
        return fn
    return deco


# ---------- small helpers ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_inout(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def ease_back(x): x = clamp(x); s = 1.7; x -= 1; return x * x * ((s + 1) * x + s) + 1
def ramp(c, e, t_in=0.25, t_out=0.2): return clamp(c.lt / t_in) * clamp((e.d - c.lt) / t_out) if t_out else clamp(c.lt / t_in)
def rgb(v, default):
    if v is None: return default
    if isinstance(v, (list, tuple)): return tuple(int(x) for x in v[:3])
    v = str(v).lstrip('#'); return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


_fc = {}
def font(kind, size):
    k = (kind, int(size))
    if k not in _fc:
        f = ImageFont.truetype(FONT[kind], max(6, int(size)))
        if kind in WGHT:
            try: f.set_variation_by_axes(list(WGHT[kind]))
            except Exception: pass
        _fc[k] = f
    return _fc[k]


def text_img(s, size, kind='bold', fill=(255, 255, 255), stroke=0, stroke_fill=INK, shadow=0, glow=None):
    f = font(kind, size)
    bb = f.getbbox(s, stroke_width=stroke)
    pad = int(size * 0.2 + shadow * 2.5 + (glow[1] * 2.5 if glow else 0)) + 4
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    pos = (pad - bb[0], pad - bb[1])
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pos[0], pos[1] + shadow * 0.5), s, font=f, fill=(0, 0, 0, 160), stroke_width=stroke)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(shadow)))
    if glow:
        g = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text(pos, s, font=f, fill=tuple(glow[0]) + (255,), stroke_width=int(size * 0.04))
        g = g.filter(ImageFilter.GaussianBlur(glow[1]))
        im = Image.alpha_composite(Image.alpha_composite(im, g), g)
    ImageDraw.Draw(im).text(pos, s, font=f, fill=tuple(fill) + (255,), stroke_width=stroke, stroke_fill=tuple(stroke_fill) + (255,))
    return im


def fit_text(s, max_w, kind='bold', start=400, **kw):
    size = start
    while size > 10 and font(kind, size).getlength(s) > max_w: size = int(size * 0.92)
    return text_img(s, size, kind, **kw)


def rrect(w, h, r, fill, outline=None, width=0):
    im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], int(r), fill=fill, outline=outline, width=width)
    return im


def shadowed(im, blur=18, dy=10, alpha=120):
    pad = blur * 2 + abs(dy)
    out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.paste(sh, (pad, pad + dy), sh)
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def to_np(im): return np.asarray(im.convert('RGBA'), dtype=np.float32) / 255.0


def comp(c, layer, x, y, alpha=1.0, behind=False, guard=False):
    """Alpha-composite an RGBA layer with its top-left at (x, y).
    behind=True hides it wherever the person is (so it sits behind you).
    guard=True only hides it where it would cover your face."""
    L = to_np(layer) if isinstance(layer, Image.Image) else layer
    h, w = L.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(c.W, x + w), min(c.H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0: return
    L = L[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] * alpha
    m = c.m[y0:y1, x0:x1, None]
    if behind: a = a * (1 - m)
    elif guard:
        yy, xx = np.ogrid[y0:y1, x0:x1]
        e = ((xx - c.fx) / (c.fw * 0.95)) ** 2 + ((yy - c.fy) / (c.fw * 1.35)) ** 2
        a = a * (1 - np.clip((1.2 - e) / 0.3, 0, 1)[..., None] * m)
    dst = c.img[y0:y1, x0:x1]
    dst[:] = dst * (1 - a) + L[..., :3] * a


def place(c, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0, behind=False, guard=False, keep=False):
    """Draw a PIL image centred on (cx, cy), scaled and rotated (degrees, counter-clockwise).
    keep=True nudges it so it stays fully inside the frame."""
    if scale <= 0.01 or alpha <= 0: return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if keep:
        m = min(c.W, c.H) * 0.02
        cx = clamp(cx, m + im.width / 2, c.W - m - im.width / 2) if im.width < c.W - 2 * m else c.W / 2
        cy = clamp(cy, m + im.height / 2, c.H - m - im.height / 2) if im.height < c.H - 2 * m else c.H / 2
    comp(c, im, cx - im.width / 2, cy - im.height / 2, alpha, behind, guard)


def camera(c, zoom, cx, cy):
    """Zoom the whole frame (and the person mask) towards (cx, cy). Capped at 2x so it stays sharp."""
    zoom = min(zoom, 2.0)
    if zoom <= 1.002: return
    cw, ch = c.W / zoom, c.H / zoom
    x0 = clamp(cx - cw / 2, 0, c.W - cw); y0 = clamp(cy - ch / 2, 0, c.H - ch)
    M = np.float32([[zoom, 0, -x0 * zoom], [0, zoom, -y0 * zoom]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
    c.fx, c.fy, c.fw = (c.fx - x0) * zoom, (c.fy - y0) * zoom, c.fw * zoom


def face_cam(c, zoom, head_at=0.40):
    """Zoom on the face, keeping it at `head_at` of the frame height."""
    z = min(zoom, 2.0)
    camera(c, z, c.fx, c.fy + (c.H / z) * (0.5 - head_at))


def clear_spot(c, e, w, h, order=('above', 'side', 'below'), min_s=0.75, key='spot', floor=0.3):
    """Where a w x h panel fits without touching your head: (cx, cy, scale, slot).
    Tries each slot in `order` (above the head, beside it, under the chin) and takes the first where the panel
    fits at `min_s` or bigger, else the roomiest one. The slot is picked once per effect so it never jumps."""
    m = min(c.W, c.H) * 0.035
    x0, y0, x1, y1 = c.fx - c.fw * 1.05, c.fy - c.fw * 1.3, c.fx + c.fw * 1.05, c.fy + c.fw * 1.55  # just outside the face guard
    left, right = x0 - 2 * m, c.W - x1 - 2 * m
    room = {'above': min(1, (y0 - 2 * m) / h, (c.W - 2 * m) / w),
            'side': min(1, max(left, right) / w, (c.H - 2 * m) / h),
            'below': min(1, (c.H - y1 - 2 * m) / h, (c.W - 2 * m) / w)}
    if key not in e.state:
        slot = next((k for k in order if room[k] >= min_s), max(order, key=lambda k: room[k]))
        e.state[key] = (slot, left > right, float(clamp(room[slot], floor, 1)))
    slot, on_left, s = e.state[key]
    sw, sh = w * s, h * s
    if slot == 'above':
        return clamp(c.fx, m + sw / 2, c.W - m - sw / 2), max(m + sh / 2, y0 - m - sh / 2), s, slot
    if slot == 'side':
        cx = (x0 + m) / 2 if on_left else (x1 + c.W - m) / 2
        return clamp(cx, m + sw / 2, c.W - m - sw / 2), clamp(c.fy, m + sh / 2, c.H - m - sh / 2), s, slot
    return clamp(c.fx, m + sw / 2, c.W - m - sw / 2), min(c.H - m - sh / 2, y1 + m + sh / 2), s, slot


def grade(img, kind='moody'):
    lum = (img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    if kind == 'bw':
        g = np.clip((lum - 0.5) * 1.25 + 0.5, 0, 1); return np.repeat(g, 3, axis=2)
    if kind == 'warm': return np.clip(img * np.float32([1.08, 1.0, 0.86]) + 0.02, 0, 1)
    if kind == 'cool': return np.clip(img * np.float32([0.9, 1.0, 1.1]), 0, 1)
    if kind == 'pop':
        o = lum + (img - lum) * 1.35; return np.clip((o - 0.5) * 1.12 + 0.5, 0, 1)
    # moody: a little darker, softer colour, teal shadows, warm highlights, gentle contrast
    o = lum + (img - lum) * 0.6
    o = np.power(np.clip(o, 0, 1), 1.3) * 0.88
    o = o + (1 - lum) * np.float32([-0.03, 0.035, 0.065]) + lum * np.float32([0.05, 0.015, -0.04])
    o = np.clip((o - 0.42) * 1.12 + 0.42, 0, 1)
    return o


_vig = {}
def vignette(c, strength=0.35):
    k = (c.W, c.H)
    if k not in _vig:
        yy, xx = np.ogrid[0:c.H, 0:c.W]
        d = ((xx - c.W / 2) / (c.W * 0.75)) ** 2 + ((yy - c.H / 2) / (c.H * 0.7)) ** 2
        _vig[k] = np.clip(d, 0, 1).astype(np.float32)
    c.img *= (1 - strength * _vig[k])[..., None]


def card(im, w, radius=0.07):
    """A reel-shaped (9:16) rounded card with a soft shadow."""
    h = int(w * 16 / 9)
    src = im.convert('RGB'); sw, sh = src.size
    s = max(w / sw, h / sh)
    src = src.resize((max(w, int(sw * s)), max(h, int(sh * s))), Image.LANCZOS)
    l, t = (src.width - w) // 2, (src.height - h) // 2
    src = src.crop((l, t, l + w, t + h)).convert('RGBA')
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), fill=255)
    src.putalpha(m)
    ImageDraw.Draw(src).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), outline=(0, 0, 0, 70), width=2)
    return shadowed(src, blur=max(6, w // 16), dy=w // 22, alpha=150)


def vary(im, i):
    """Give each card its own look, so a pile of frames reads as different reels."""
    kind = ('pop', 'bw', 'warm', 'cool', 'moody')[i % 5]
    a = np.asarray(im.convert('RGB'), np.float32) / 255
    return Image.fromarray((grade(a, kind) * 255).astype(np.uint8))


def cached(e, key, fn):
    if key not in e.state: e.state[key] = fn()
    return e.state[key]


# ---------- the 22 effects ----------
@effect('noise', 'reels pile up behind your head, one every quarter second')
def fx_noise(c, e):
    cw = int(c.U * float(e.o.get('size', 0.34)))
    def setup():
        rnd = random.Random(7); n = min(16, max(4, int(e.d / 0.22)))
        return [(rnd.uniform(0.14, 0.86), rnd.uniform(0.12, 0.52), rnd.uniform(-7, 7)) for _ in range(n)]
    pos = cached(e, 'pos', setup)
    cards = cached(e, 'cards', lambda: [card(vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(pos):
        t0 = i * 0.22
        if c.lt < t0: break
        k = ease_back((c.lt - t0) / 0.25)
        place(c, cards[i % len(cards)], x * c.W, y * c.H, 0.6 + 0.4 * k, r, clamp((c.lt - t0) / 0.08) * out, behind=True, keep=True)


@effect('lineup', 'numbered tiles fan out in an arc above your head')
def fx_lineup(c, e):
    names = e.o.get('text', '|'.join(NAMES)).split('|')
    tw = int(c.U * 0.105)
    def tile(i, name):
        im = rrect(tw, int(tw * 1.25), tw * 0.16, (26, 26, 46, 225), (255, 255, 255, 60), 2)
        d = ImageDraw.Draw(im)
        num = text_img(f'{i + 1:02d}', tw * 0.42, 'serif', CREAM)
        im.alpha_composite(num, ((tw - num.width) // 2, int(tw * 0.04)))
        words = name.split(' ')
        lines = [' '.join(words[:len(words) // 2 or 1]), ' '.join(words[len(words) // 2 or 1:])] if len(name) > 10 else [name]
        f = font('ui', tw * 0.15)
        for j, ln in enumerate([l for l in lines if l]):
            d.text((tw / 2, tw * (0.78 + 0.19 * j)), ln, font=f, fill=(255, 255, 255, 235), anchor='mm')
        return shadowed(im, 8, 5, 90)
    tiles = cached(e, 'tiles', lambda: [tile(i, n) for i, n in enumerate(names)])
    n = len(tiles); outer = math.ceil(n / 2 + 0.5); inner = n - outer
    cx, cy = c.W / 2 * 0.6 + c.fx * 0.4, c.fy + c.fw * 0.3
    R0 = c.U * 0.47; th = tw * 1.25
    hf = clamp((min(cx, c.W - cx) - tw * 0.7) / R0, 0.55, c.W / c.U)  # wide frames spread the arc sideways
    vf = clamp((cy - th * 0.7 - c.H * 0.02) / (R0 * 1.05), 0.45, 1)  # and flatten it to stay under the top edge
    slots = []
    for row, cnt, R in ((0, outer, R0), (1, inner, c.U * 0.33)):
        for k in range(cnt):
            a = math.pi * (0.94 - 0.88 * k / max(1, cnt - 1))
            slots.append((cx + R * hf * math.cos(a), cy - R * vf * math.sin(a) * 1.05, math.degrees(a - math.pi / 2) * 0.3))
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(slots[:n]):
        t0 = 0.035 * i
        if c.lt < t0: continue
        k = ease_back((c.lt - t0) / 0.3)
        place(c, tiles[i], x, y + (1 - k) * 40, 0.5 + 0.5 * k, r, clamp((c.lt - t0) / 0.1) * out, behind=True, keep=True)


@effect('locked-on', 'corner brackets snap onto your face and the camera follows you')
def fx_locked_on(c, e):
    face_cam(c, 1 + (float(e.o.get('zoom', 1.35)) - 1) * ease_out(c.lt / 0.6))
    snap = ease_out(c.lt / 0.22); s = c.fw * 0.85 * (1 + 0.6 * (1 - snap))
    s = max(c.fw * 0.6, min(s, ((c.fy - c.H * 0.02) / 0.625 - 40) / 2))  # keep the top brackets on screen
    al = clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2)
    size = int(2 * s + 40); im = Image.new('RGBA', (size, int(size * 1.25)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 20, 20, size - 20, im.height - 20; L = int(s * 0.32); wd = max(4, int(c.W / 200))
    for (px, py, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(px, py + dy * L), (px, py), (px + dx * L, py)], fill=(255, 255, 255, 255), width=wd, joint='curve')
    place(c, shadowed(im, 6, 2, 120), c.fx, c.fy, alpha=al)
    tag = text_img(e.o.get('text', 'LOCKED ON').upper(), c.W * 0.022, 'mono', INK)
    pill = rrect(tag.width + 10, tag.height, tag.height / 2, (255, 255, 255, 235)); pill.alpha_composite(tag, (5, 0))
    place(c, pill, c.fx, c.fy + s * 1.25 + pill.height, alpha=clamp((c.lt - 0.15) / 0.15) * al, guard=True)


@effect('orbit', 'your reels circle your head: in front at the bottom, behind you at the top')
def fx_orbit(c, e):
    K = int(e.o.get('count', 6)); cw = int(c.U * float(e.o.get('size', 0.2)))
    cards = cached(e, 'cards', lambda: [card(vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    intro, out = ease_out(c.lt / 0.4), clamp((e.d - c.lt) / 0.25)
    rx, ry = max(c.fw * 1.3, min(c.W * 0.38, c.fx - cw * 0.6, c.W - c.fx - cw * 0.6)) * intro, max(c.fw * 1.5, c.H * 0.1)
    oy = c.fy + c.fw * 0.9
    items = []
    for i in range(K):
        th = i * 2 * math.pi / K + c.lt * float(e.o.get('speed', 1.9))
        items.append((math.sin(th), th, i))
    for depth, th, i in sorted(items):
        place(c, cards[i % len(cards)], c.fx + rx * math.cos(th), oy + ry * math.sin(th), (0.78 + 0.24 * (depth + 1) / 2) * (0.5 + 0.5 * intro),
              -6 * math.cos(th), out * clamp(c.lt / 0.15), behind=depth < 0, guard=depth >= 0, keep=True)


@effect('lean-in', 'a fast punch-in on one word')
def fx_lean_in(c, e):
    z = float(e.o.get('zoom', 1.45))
    face_cam(c, 1 + (z - 1) * ease_out(c.lt / float(e.o.get('speed', 0.18))), 0.42)


@effect('backdrop-word', 'a giant word drops in behind you')
def fx_backdrop_word(c, e):
    word = e.o.get('text', 'CLAUDE')
    im = cached(e, 'w', lambda: fit_text(word, c.W * 0.94, e.o.get('font', 'bold'), fill=rgb(e.o.get('color'), CREAM), shadow=10))
    k = ease_back(c.lt / 0.42)
    y_end = max(min(c.W, c.H) * 0.035 + im.height / 2, c.fy - c.fw * 1.05)
    y = -im.height + (y_end + im.height) * k
    place(c, im, c.W / 2 * 0.6 + c.fx * 0.4, y, alpha=clamp((e.d - c.lt) / 0.2), behind=True)


_grid = {}
def grid(c):
    if (c.W, c.H) not in _grid:
        yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32); _grid[(c.W, c.H)] = (xx, yy)
    return _grid[(c.W, c.H)]


@effect('spotlight', 'kill the lights, keep you lit')
def fx_spotlight(c, e):
    if e.o.get('look') == 'sparkle': return spotlight_sparkle(c, e)
    face_cam(c, 1 + (float(e.o.get('push', 1.1)) - 1) * ease_inout(c.lt / e.d))
    k = ramp(c, e, 0.3, 0.25)
    xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.5)) ** 2 + ((yy - (c.fy + c.H * 0.2)) / (c.H * 0.46)) ** 2
    pool = np.clip(1 - d, 0, 1) ** 1.6
    bright = 1 - k * (1 - (0.1 + 0.35 * pool))
    f = bright * (1 - c.m) + c.m * (1 + 0.04 * k)
    if e.o.get('text'):
        word = e.o['text']; col = rgb(e.o.get('color'), PEACH)
        im = cached(e, 'w', lambda: fit_text(word, c.W * 0.9, e.o.get('font', 'serif'), fill=col, glow=(col, 26)))
        c.img *= f[..., None]
        place(c, im, c.W / 2, c.fy - c.fw * 1.1, alpha=k, behind=True)
    else:
        c.img *= f[..., None]


@effect('the-bill', 'prints every instruction like a ticket, into the wall above your head')
def fx_bill(c, e):
    lines = e.o.get('text', 'ORDER #1021|1x orbit|1x spotlight|1x lean-in|cut the dead air|TOTAL: 1 prompt').split('|')
    def build():
        pw = int(c.W * 0.5); lh = int(pw * 0.085); pad = int(pw * 0.08)
        h = pad * 2 + lh * (len(lines) + 1)
        im = Image.new('RGBA', (pw, h), CREAM + (255,)); d = ImageDraw.Draw(im)
        f = font('mono', lh * 0.62)
        for i, ln in enumerate(lines):
            y = pad + lh * i + (lh if i == len(lines) - 1 else 0)
            if i == len(lines) - 1:
                for x in range(pad, pw - pad, 14): d.line([(x, y - lh * 0.45), (x + 7, y - lh * 0.45)], fill=INK + (140,), width=2)
            d.text((pad, y), ln, font=f, fill=INK + (255,))
        return im
    rec = cached(e, 'r', build)
    cx, cy, s, _ = clear_spot(c, e, rec.width * 1.24, rec.height + c.H * 0.03, ('above', 'side'), 0.6, floor=0.6)
    slot_y, sw = cy - (rec.height + c.H * 0.03) * s / 2 + c.H * 0.015, rec.width * 1.24 * s
    pr = ease_inout(c.lt / (e.d * 0.75)); L = int(rec.height * pr)
    al = clamp((e.d - c.lt) / 0.25)
    if L > 2:
        paper = rec.crop((0, 0, rec.width, L))
        z = 14; jag = Image.new('RGBA', (rec.width, L + z), (0, 0, 0, 0)); jag.paste(paper, (0, 0))
        ImageDraw.Draw(jag).polygon([(x, L) for x in range(0, rec.width + 1, 2 * z)] + [(rec.width, L)] +
                                    [(x + z, L + z) for x in range(rec.width - 2 * z, -1, -2 * z)], fill=CREAM + (255,))
        paper = shadowed(jag, 10, 6, 90)
        if s < 1: paper = paper.resize((int(paper.width * s), int(paper.height * s)), Image.BILINEAR)
        comp(c, paper, cx - paper.width / 2, slot_y - 10 * s, al, behind=True)
    slot = rrect(sw, c.H * 0.03 * max(s, 0.6), c.H * 0.015 * max(s, 0.6), (26, 26, 46, 255), (100, 100, 140, 255), 3)
    place(c, shadowed(slot, 10, 6, 140), cx, slot_y, alpha=al * clamp(c.lt / 0.15), behind=True)


@effect('moody', 'a moody colour grade: darker, softer, teal shadows')
def fx_moody(c, e):
    k = ramp(c, e, 0.35, 0)
    c.img = c.img * (1 - k) + grade(c.img, e.o.get('grade', 'moody')) * k
    vignette(c, 0.4 * k)


@effect('swipe', 'a before and after slider that sweeps across you')
def fx_swipe(c, e):
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    before = np.clip((c.img * 0.45 + lum * 0.55) * 0.8 + 0.12, 0, 1)  # flat, washed-out log look
    after = grade(c.img, e.o.get('grade', 'pop'))
    p = c.lt / e.d
    sp = 1.05 - 0.95 * ease_inout(p / 0.5) if p < 0.5 else 0.1 + 0.4 * ease_inout((p - 0.5) / 0.4)
    xx, yy = grid(c)
    line = sp * c.W + 0.22 * (yy - c.H / 2)
    a = np.clip((xx - line) / 3 + 0.5, 0, 1)[..., None]
    c.img = before * (1 - a) + after * a
    hy = c.H * 0.62; hx = sp * c.W + 0.22 * (hy - c.H / 2)
    edge = np.clip(1 - np.abs(xx - line) / 3.5, 0, 1)[..., None]
    c.img = c.img * (1 - edge) + edge
    r = int(c.U * 0.045); h = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(h)
    d.ellipse([2, 2, 2 * r + 2, 2 * r + 2], fill=(255, 255, 255, 255))
    d.text((r + 2, r + 2), '< >', font=font('mono', r * 0.7), fill=INK + (255,), anchor='mm')
    place(c, shadowed(h, 8, 4, 110), hx, hy)
    for lab, x in (('BEFORE', 0.14), ('AFTER', 0.86)):
        t = text_img(lab, c.U * 0.04, 'uib', INK); pw_ = t.width + c.U * 0.04; pill = rrect(pw_, t.height * 1.1, t.height * 0.55, (255, 255, 255, 235))
        pill.alpha_composite(t, (int(c.U * 0.02), int(t.height * 0.05))); place(c, shadowed(pill, 8, 3, 90), c.W * x, c.H * 0.9, keep=True)


@effect('todo', 'a checklist card beside your head that ticks off as you talk')
def fx_todo(c, e):
    items = e.o.get('text', 'drop your video into Claude|install the skill|type /effects').split('|')
    # ticks = video seconds when each item gets ticked (e.g. when you say it); default is evenly spaced
    ticks = [float(t) - e.start for t in str(e.o['ticks']).split('|')] if e.o.get('ticks') else [e.d * (i + 1) / (len(items) + 1) for i in range(len(items))]
    cw = int(c.W * 0.5); lh = int(cw * 0.13); pad = int(cw * 0.07)
    im = rrect(cw, pad * 2 + lh * (len(items) + 1), cw * 0.07, (250, 250, 250, 235)); d = ImageDraw.Draw(im)
    done = sum(c.lt >= t for t in ticks)
    d.text((pad, pad), e.o.get('title', 'TO DO').upper(), font=font('ui', lh * 0.42), fill=(124, 58, 237, 255))
    d.text((cw - pad, pad), f'{done} of {len(items)}', font=font('ui', lh * 0.36), fill=(100, 100, 140, 255), anchor='ra')
    f = font('ui', lh * 0.4)
    for i, it in enumerate(items):
        y = pad + lh * (i + 1); bx = lh * 0.42
        d.rounded_rectangle([pad, y + lh * 0.12, pad + bx, y + lh * 0.12 + bx], 6, outline=(148, 148, 184, 255), width=3)
        d.text((pad + bx * 1.5, y + lh * 0.1), it, font=f, fill=INK + (255,))
        if c.lt >= ticks[i]:
            k = ease_out((c.lt - ticks[i]) / 0.25)
            d.rounded_rectangle([pad, y + lh * 0.12, pad + bx, y + lh * 0.12 + bx], 6, fill=(16, 185, 129, 255))
            d.line([(pad + bx * .22, y + lh * .12 + bx * .52), (pad + bx * .42, y + lh * .12 + bx * .74), (pad + bx * .8, y + lh * .12 + bx * .28)], fill=(255, 255, 255, 255), width=4)
            tw = f.getlength(it) * k
            d.line([(pad + bx * 1.5, y + lh * 0.36), (pad + bx * 1.5 + tw, y + lh * 0.36)], fill=INK + (255,), width=3)
    x, y, s, slot = clear_spot(c, e, im.width, im.height, ('side', 'below'), 0.8)
    pop = ease_back(c.lt / 0.3)
    place(c, shadowed(im, 14, 8, 90), x, y, s * (0.8 + 0.2 * pop), 0, clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2), behind=slot == 'side', guard=slot != 'side')


def heart(size, color=(239, 68, 68)):
    s = int(size); im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(s / 2 + s * 0.48 * (16 * math.sin(t) ** 3) / 16, s * 0.46 - s * 0.46 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16)
           for t in np.linspace(0, 2 * math.pi, 60)]
    d.polygon(pts, fill=color + (255,)); return im


def comment_bar(c, e):
    word = e.o.get('text', 'EFFECTS')
    bw, bh = int(c.W * 0.9), int(c.W * 0.11)
    slide = ease_out(c.lt / 0.3); y = c.H * 0.8 + (1 - slide) * c.H * 0.25
    type_t, post_t = 0.35, 0.35 + 0.08 * len(word) + 0.25
    typed = word[:int(clamp((c.lt - type_t) / (0.08 * len(word))) * len(word) + 0.001)] if c.lt < post_t else ''
    im = rrect(bw, bh, bh / 2, (255, 255, 255, 245)); d = ImageDraw.Draw(im)
    r = bh * 0.32; d.ellipse([bh * 0.2, bh / 2 - r, bh * 0.2 + 2 * r, bh / 2 + r], fill=(124, 58, 237, 255))
    f = font('ui', bh * 0.3)
    if typed: d.text((bh * 0.95, bh / 2), typed + ('|' if int(c.lt * 4) % 2 else ''), font=f, fill=INK + (255,), anchor='lm')
    elif c.lt < post_t: d.text((bh * 0.95, bh / 2), 'Add a comment...', font=f, fill=(100, 100, 140, 255), anchor='lm')
    d.text((bw - bh * 0.4, bh / 2), 'Post', font=f, fill=((124, 58, 237, 255) if typed else (237, 233, 254, 255)), anchor='rm')
    al = clamp((e.d - c.lt) / 0.2)
    place(c, shadowed(im, 14, 6, 100), c.W / 2, y, alpha=al, guard=True)
    if c.lt >= post_t:
        k = ease_back((c.lt - post_t) / 0.3)
        b = rrect(int(c.W * 0.52), int(bh * 0.85), bh * 0.3, (255, 255, 255, 240)); bd = ImageDraw.Draw(b)
        bd.text((bh * 0.3, b.height * 0.32), 'you', font=font('ui', bh * 0.2), fill=(100, 100, 140, 255), anchor='lm')
        bd.text((bh * 0.3, b.height * 0.66), word, font=font('ui', bh * 0.3), fill=INK + (255,), anchor='lm')
        hk = ease_back((c.lt - post_t - 0.3) / 0.3)
        if hk > 0:
            hh = heart(bh * 0.4 * hk); b.alpha_composite(hh, (int(b.width - bh * 0.3 - hh.width), int(b.height / 2 - hh.height / 2)))
        place(c, shadowed(b, 12, 5, 90), c.W * 0.07 + b.width / 2, y - bh * 1.05, 0.7 + 0.3 * k, 0, al * clamp((c.lt - post_t) / 0.1), guard=True)


@effect('tap', 'a Follow button pops up and flips to Following')
def fx_tap(c, e):
    at = float(e.o['at']) - e.start if 'at' in e.o else e.d * 0.45  # 'at' = video second of the tap
    bw, bh = int(c.W * 0.3), int(c.W * 0.09)
    x = clamp(float(e.o['x']) * c.W if 'x' in e.o else c.fx + c.fw * 1.9, bw / 2 + 30, c.W - bw / 2 - 30)
    y = clamp(float(e.o['y']) * c.H if 'y' in e.o else c.fy + c.fw * 1.6, bh + 30, c.H - bh - 30)
    on = c.lt >= at
    col = rgb(e.o.get('color'), (167, 139, 250)) if on else (124, 58, 237)
    im = rrect(bw, bh, bh * 0.28, col + (255,)); d = ImageDraw.Draw(im)
    d.text((bw / 2, bh / 2), 'Following' if on else '+ Follow', font=font('ui', bh * 0.4), fill=(255, 255, 255, 255), anchor='mm')
    pop = ease_back(c.lt / 0.3)
    sq = 1.0
    if on: q = (c.lt - at) / 0.3; sq = 1 - 0.12 * math.sin(math.pi * clamp(q)) if q < 1 else 1
    place(c, shadowed(im, 12, 6, 110), x, y, (0.6 + 0.4 * pop) * sq, 0, clamp(c.lt / 0.1) * clamp((e.d - c.lt) / 0.2), guard=True)
    if on and c.lt - at < 0.4:
        q = (c.lt - at) / 0.4; r = int(bh * (0.3 + 0.9 * q)); ring = Image.new('RGBA', (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([4, 4, 2 * r + 4, 2 * r + 4], outline=(255, 255, 255, int(220 * (1 - q))), width=5)
        place(c, ring, x, y, guard=True)


def hand_path(d, pts, color, width, frac):
    n = max(2, int(len(pts) * clamp(frac)))
    if frac > 0: d.line(pts[:n], fill=color, width=width, joint='curve')
    return pts[n - 1]


def arrow_pts(x0, y0, x1, y1, bend=0.25, n=40):
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1) for t in np.linspace(0, 1, n)]


def arrow_head(d, pts, color, width, size):
    (xa, ya), (xb, yb) = pts[-4], pts[-1]; a = math.atan2(yb - ya, xb - xa)
    for s in (2.6, -2.6):
        d.line([(xb, yb), (xb + size * math.cos(a + s), yb + size * math.sin(a + s))], fill=color, width=width)


@effect('pause-point', 'freeze the frame and point at something with a hand-drawn arrow')
def fx_pause_point(c, e):
    if 'f' not in e.state: e.state['f'] = (c.img.copy(), c.m.copy(), c.fx, c.fy, c.fw)
    img, m, c.fx, c.fy, c.fw = e.state['f']; c.img, c.m = img.copy(), m
    face_cam(c, 1 + 0.06 * ease_out(c.lt / e.d), 0.4)
    c.img = c.img * 0.92 + grade(c.img, 'bw') * 0.08
    col = rgb(e.o.get('color'), YELLOW) + (255,)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([c.W * 0.05, c.H * 0.06, c.W * 0.05 + c.W * 0.1, c.H * 0.06 + c.W * 0.1], 16, fill=(0, 0, 0, 150))
    for bx in (0.075, 0.11): d.rectangle([c.W * bx, c.H * 0.06 + c.W * 0.025, c.W * (bx + 0.017), c.H * 0.06 + c.W * 0.075], fill=(255, 255, 255, 230))
    lab = cached(e, 'lab', lambda: text_img(e.o.get('text', 'look here'), c.W * 0.07, 'hand', col[:3], shadow=6))
    tx, ty, ls, _ = clear_spot(c, e, lab.width * 1.3, lab.height * 2.2, ('above', 'side', 'below'), 0.7, floor=0.6)
    if e.o.get('label_x'): tx = c.W * float(e.o['label_x'])
    sd = 1 if tx >= c.fx else -1
    pts = arrow_pts(tx - sd * c.W * 0.05, ty + c.W * 0.06 * ls, c.fx + sd * c.fw * 0.75, c.fy - c.fw * 0.35, 0.3 * sd)
    k = ease_out((c.lt - 0.15) / 0.4)
    hand_path(d, pts, col, max(6, c.W // 140), k)
    if k >= 0.99: arrow_head(d, pts, col, max(6, c.W // 140), c.W * 0.04)
    comp(c, to_np(lay), 0, 0)
    place(c, lab, tx, ty - lab.height * 0.5 * ls, ls * (0.7 + 0.3 * ease_back(c.lt / 0.3)), -6, clamp(c.lt / 0.1), guard=True)


@effect('uninstall', 'a glitchy uninstall bar that breaks the frame apart')
def fx_uninstall(c, e):
    p = clamp(c.lt / e.d); g = p ** 1.6
    rnd = np.random.default_rng(int(c.t * 30))
    sh = int(g * c.W * 0.025)
    if sh: c.img = np.stack([np.roll(c.img[..., 0], sh, 1), c.img[..., 1], np.roll(c.img[..., 2], -sh, 1)], -1)
    for _ in range(int(2 + g * 10)):
        y0 = int(rnd.uniform(0, c.H)); hh = int(rnd.uniform(8, 60)); off = int(rnd.uniform(-1, 1) * g * c.W * 0.08)
        c.img[y0:y0 + hh] = np.roll(c.img[y0:y0 + hh], off, 1)
    if p > 0.82:
        q = (p - 0.82) / 0.18; f = 1 + int(q * 40)
        small = cv2.resize(c.img, (max(1, c.W // f), max(1, c.H // f)), interpolation=cv2.INTER_AREA)
        c.img = cv2.resize(small, (c.W, c.H), interpolation=cv2.INTER_NEAREST) * (1 - 0.6 * q)
    bw, bh = int(c.U * 0.7), int(c.U * 0.2)
    im = rrect(bw, bh, bh * 0.14, (250, 250, 250, 240)); d = ImageDraw.Draw(im)
    d.text((bw * 0.06, bh * 0.28), e.o.get('text', 'Uninstalling...'), font=font('ui', bh * 0.18), fill=INK + (255,), anchor='lm')
    d.rounded_rectangle([bw * 0.06, bh * 0.56, bw * 0.94, bh * 0.7], 8, fill=(243, 240, 255, 255))
    d.rounded_rectangle([bw * 0.06, bh * 0.56, bw * 0.06 + bw * 0.88 * max(0.03, ease_inout(p)), bh * 0.7], 8, fill=(124, 58, 237, 255))
    d.text((bw * 0.94, bh * 0.85), f'{int(ease_inout(p) * 100)}%', font=font('ui', bh * 0.13), fill=(100, 100, 140, 255), anchor='rm')
    place(c, shadowed(im, 16, 8, 120), c.W / 2, min(c.H, c.W) * 0.06 + bh * 0.6, 0.8 + 0.2 * ease_back(c.lt / 0.3), 0, clamp(c.lt / 0.1))


def reel_icons(size):
    s = int(size); im = Image.new('RGBA', (s, int(s * 3.6)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = max(3, s // 12)
    h = heart(s * 0.8, (255, 255, 255)); im.alpha_composite(h, (int(s * 0.1), 0))
    d.text((s / 2, s * 0.95), '26.9K', font=font('ui', s * 0.24), fill=(255, 255, 255, 255), anchor='mm')
    d.ellipse([s * 0.15, s * 1.25, s * 0.85, s * 1.95], outline=(255, 255, 255, 255), width=w)
    d.text((s / 2, s * 2.15), '412', font=font('ui', s * 0.24), fill=(255, 255, 255, 255), anchor='mm')
    d.polygon([(s * 0.12, s * 2.75), (s * 0.9, s * 2.45), (s * 0.55, s * 3.25), (s * 0.45, s * 2.88)], outline=(255, 255, 255, 255), width=w)
    return im


@effect('reel-frame', 'your video shrinks into an Instagram reel card')
def fx_reel_frame(c, e):
    k = ease_out(c.lt / 0.35) * clamp((e.d - c.lt) / 0.3)
    if k <= 0: return
    s = 1 - 0.2 * k
    small = cv2.resize(c.img, (c.W // 16, c.H // 16), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(cv2.resize(small, (c.W, c.H), interpolation=cv2.INTER_LINEAR), (0, 0), 12) * (1 - 0.45 * k)
    iw, ih = int(c.W * s), int(c.H * s)
    inset = cv2.resize(c.img, (iw, ih), interpolation=cv2.INTER_AREA)
    m = to_np(rrect(iw, ih, c.W * 0.05 * k + 1, (255, 255, 255, 255)))[..., 3:4]
    x0, y0 = (c.W - iw) // 2, int((c.H - ih) * 0.42)
    out = bg.copy(); reg = out[y0:y0 + ih, x0:x0 + iw]; reg[:] = reg * (1 - m) + inset * m
    c.img = out
    mm = np.zeros_like(c.m); mm[y0:y0 + ih, x0:x0 + iw] = cv2.resize(c.m, (iw, ih)); c.m = mm
    c.fx, c.fy, c.fw = x0 + c.fx * s, y0 + c.fy * s, c.fw * s
    ic = cached(e, 'ic', lambda: shadowed(reel_icons(c.U * 0.075), 6, 2, 120))
    comp(c, ic, x0 + iw - ic.width - c.U * 0.02, y0 + ih * 0.88 - ic.height, k)
    hdl = text_img(e.o.get('text', '@matt_penny_applied_ai'), c.U * 0.034, 'ui', (255, 255, 255), shadow=4)
    comp(c, hdl, x0 + c.U * 0.04, y0 + ih - hdl.height - c.U * 0.05, k)


@effect('shortcut-rain', 'keyboard keys rain down behind you')
def fx_shortcut_rain(c, e):
    keys = e.o.get('text', 'cmd|/|C|V|Z|esc|tab|shift|enter|opt').split('|')
    ks = int(c.W * 0.1)
    def cap(k):
        w = max(ks, int(font('mono', ks * 0.36).getlength(k) + ks * 0.5))
        im = rrect(w, ks, ks * 0.18, (243, 240, 255, 255)); top = rrect(w - 8, ks - 14, ks * 0.16, (250, 250, 250, 255))
        im.alpha_composite(top, (4, 3)); ImageDraw.Draw(im).text((w / 2, ks * 0.44), k, font=font('mono', ks * 0.36), fill=INK + (255,), anchor='mm')
        return shadowed(im, 8, 6, 100)
    caps = cached(e, 'caps', lambda: [cap(k) for k in keys])
    parts = cached(e, 'p', lambda: [(random.Random(i).random(), random.Random(i + 99).random() * max(0.1, e.d - 0.8),
                                     0.45 + 0.4 * random.Random(i + 7).random(), random.Random(i + 3).uniform(-25, 25),
                                     random.Random(i + 5).uniform(-60, 60)) for i in range(int(e.o.get('count', 26)))])
    for i, (x, t0, v, r0, w) in enumerate(parts):
        if c.lt < t0: continue
        y = -ks + (c.lt - t0) * v * c.H
        place(c, caps[i % len(caps)], c.W * (0.04 + 0.92 * x), y, 0.75 + 0.35 * v, r0 + w * (c.lt - t0), clamp((e.d - c.lt) / 0.2), behind=True)


@effect('reject-stamp', 'a big red stamp slams onto the screen')
def fx_reject_stamp(c, e):
    word = e.o.get('text', 'REJECTED').upper(); col = rgb(e.o.get('color'), (239, 68, 68))
    def build():
        t = fit_text(word, c.U * 0.72, 'bold', 200, fill=col); pad = int(t.height * 0.12)
        im = Image.new('RGBA', (t.width + 4 * pad, t.height + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([3, 3, im.width - 4, im.height - 4], 18, outline=col + (255,), width=max(6, pad // 2))
        im.alpha_composite(t, (2 * pad, pad))
        a = np.asarray(im.split()[3], np.float32) * np.clip(np.random.default_rng(3).uniform(0.55, 1.6, (im.height, im.width)), 0, 1)
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        return im
    st = cached(e, 's', build)
    k = clamp(c.lt / 0.16); sc = 2.3 - 1.3 * k * k
    if 0.16 < c.lt < 0.45:
        a = (0.45 - c.lt) / 0.29 * c.W * 0.012; rnd = np.random.default_rng(int(c.t * 30))
        M = np.float32([[1, 0, rnd.uniform(-a, a)], [0, 1, rnd.uniform(-a, a)]])
        c.img = cv2.warpAffine(c.img, M, (c.W, c.H), borderMode=cv2.BORDER_REFLECT)
    y = clamp(float(e.o['y']) * c.H if 'y' in e.o else c.fy + c.fw * 2.7, 0, c.H * 0.85)
    place(c, st, c.W / 2 * 0.5 + c.fx * 0.5, y, sc, float(e.o.get('angle', 12)), k * clamp((e.d - c.lt) / 0.2), guard=True, keep=True)


@effect('countdown-flip', 'a 3, 2, 1 flip clock above your head')
def fx_countdown(c, e):
    n0 = int(e.o.get('from', 3)); seg = e.d / n0
    i = min(n0 - 1, int(c.lt / seg)); cur, prev = n0 - i, n0 - i + 1
    f = clamp((c.lt - i * seg) / 0.3) if i > 0 else 1.0
    tw, th = int(c.W * 0.3), int(c.W * 0.38)
    def half(num, top):
        im = rrect(tw, th, tw * 0.1, (26, 26, 46, 255)); d = ImageDraw.Draw(im)
        d.text((tw / 2, th / 2), str(num), font=font('bold', th * 0.62), fill=CREAM + (255,), anchor='mm')
        return im.crop((0, 0, tw, th // 2)) if top else im.crop((0, th // 2, tw, th))
    hv = cached(e, 'h', lambda: {(n, t): half(n, t) for n in range(0, n0 + 2) for t in (True, False)})
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    im.paste(hv[(cur, True)], (0, 0)); im.paste(hv[(prev if f < 1 else cur, False)], (0, th // 2))
    if f < 0.5:
        h = max(1, int(th / 2 * (1 - 2 * f))); fl = hv[(prev, True)].resize((tw, h)); im.paste(fl, (0, th // 2 - h))
    elif f < 1:
        h = max(1, int(th / 2 * (2 * f - 1))); fl = hv[(cur, False)].resize((tw, h)); im.paste(fl, (0, th // 2))
    ImageDraw.Draw(im).line([(0, th // 2), (tw, th // 2)], fill=(0, 0, 0, 255), width=4)
    cx, cy, s, _ = clear_spot(c, e, tw, th, ('above', 'side'), 0.6, floor=0.6)
    place(c, shadowed(im, 16, 10, 120), cx, cy, s * (0.7 + 0.3 * ease_back(c.lt / 0.3)), 0, clamp((e.d - c.lt) / 0.2), behind=True)


_rect = {}
@effect('rabbit-hole', 'the frame tunnels into itself, spinning')
def fx_rabbit_hole(c, e):
    k = ease_out(c.lt / 0.4) * clamp((e.d - c.lt) / 0.3)
    if k <= 0: return
    if (c.W, c.H) not in _rect:
        a = np.ones((c.H, c.W), np.float32); b = np.zeros((c.H, c.W), np.float32); t = max(4, c.W // 120)
        b[:t] = b[-t:] = 1; b[:, :t] = b[:, -t:] = 1; _rect[(c.W, c.H)] = (a, b)
    ones, border = _rect[(c.W, c.H)]
    r = float(e.o.get('ratio', 0.62)); z = (c.lt * float(e.o.get('speed', 0.8))) % 1.0
    src = c.img; cx, cy = c.fx, c.fy
    out = None
    for lev in range(0, 7):
        s = r ** (lev - z * k) if lev else 1.0
        ang = (lev - z) * float(e.o.get('spin', 10)) * k if lev else 0
        if lev and s < 0.03: break
        M = cv2.getRotationMatrix2D((cx, cy), ang, s)
        if lev == 0:
            out = src.copy(); continue
        L = cv2.warpAffine(src, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
        a = cv2.warpAffine(ones, M, (c.W, c.H))[..., None] * k
        bd = cv2.warpAffine(border, M, (c.W, c.H))[..., None] * k
        out = out * (1 - a) + L * a
        out = out * (1 - bd) + bd
    m = c.m[..., None] * k  # you stay in front while the room tunnels behind you
    c.img = out * (1 - m) + src * m


@effect('cover-star', 'you become a magazine cover, with the title behind your head')
def fx_cover_star(c, e):
    if e.o.get('look') == 'editorial': return cover_editorial(c, e)
    k = ease_out(c.lt / 0.35); al = clamp((e.d - c.lt) / 0.2); W, H = c.W, c.H
    c.img = c.img * (1 - 0.6 * k) + grade(c.img, 'pop') * 0.6 * k
    pw = c.U if W > c.U * 1.05 else W  # the cover page: the whole frame in 9:16, a 3:4 page around you in 16:9
    px = clamp(c.fx - pw / 2, 0, W - pw)
    title = e.o.get('text', 'VIBE').upper(); col = rgb(e.o.get('color'), (124, 58, 237))
    mast = cached(e, 'm', lambda: fit_text(title, pw * 0.92, 'bold', 600, fill=col))
    mast_h = min(mast.height, H * 0.2); ms = mast_h / mast.height; top = H * 0.045
    # make headroom: slide you down until the masthead sits above your head, hair overlapping its bottom edge
    dy = clamp(top + mast_h * 0.8 - (c.fy - c.fw * 1.25), 0, H * 0.22) * k
    if dy > 0.5:
        shift(c, dy); band = int(dy) + 2
        c.img[:band] = cv2.GaussianBlur(np.ascontiguousarray(c.img[:band]), (0, 0), 18)
    if pw < W - 2:
        xx = grid(c)[0]; inside = ((xx >= px) & (xx <= px + pw)).astype(np.float32)[..., None]
        dim = cv2.GaussianBlur(c.img, (0, 0), 14) * 0.35
        c.img = c.img * (1 - k * (1 - inside)) + dim * k * (1 - inside)
        edge = Image.new('RGBA', (int(pw), int(H)), (0, 0, 0, 0)); ImageDraw.Draw(edge).rectangle([0, 0, int(pw) - 1, int(H) - 1], outline=(255, 255, 255, 90), width=2)
        comp(c, edge, px, 0, al * k)
    place(c, mast, px + pw / 2, top + mast_h / 2 - (1 - k) * mast_h, ms, 0, al * k, behind=True)
    iss = cached(e, 'i', lambda: text_img(e.o.get('issue', 'THE AI ISSUE  ·  2026'), pw * 0.028, 'mono', (255, 255, 255), shadow=3))
    place(c, iss, px + pw / 2, top * 0.55, alpha=al * k, behind=True)
    lines = e.o.get('lines', '22 effects|you can steal|no editor|needed').split('|')
    y = H * 0.5
    for j, ln in enumerate(lines):
        big = j == 0
        im = cached(e, ('l', j), lambda: text_img(ln, pw * (0.085 if big else 0.045), 'serif' if big else 'bold', YELLOW if big else (255, 255, 255), shadow=5))
        kj = ease_out((c.lt - 0.15 - 0.08 * j) / 0.3)
        comp(c, im, px + pw * 0.05 - (1 - kj) * 60, y, al * kj, guard=True); y += im.height * 0.86
    def barcode():
        rnd = random.Random(1); bw, bh = int(pw * 0.16), int(pw * 0.09)
        im = Image.new('RGBA', (bw, bh), (255, 255, 255, 255)); d = ImageDraw.Draw(im); x = 8
        while x < bw - 8:
            w = rnd.choice((2, 2, 3, 5)); d.rectangle([x, 6, x + w - 1, bh - 18], fill=(0, 0, 0, 255)); x += w + rnd.choice((2, 3, 4))
        return im
    bc = cached(e, 'b', barcode)
    comp(c, bc, px + pw * 0.95 - bc.width, H * 0.95 - bc.height, al * k, guard=True)


@effect('scribble', 'marker doodles draw themselves around you')
def fx_scribble(c, e):
    col = rgb(e.o.get('color'), YELLOW) + (255,); wd = max(6, int(c.U) // 130)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rx, ry = c.fw * 1.0, c.fw * 1.3
    angs = np.linspace(-1.9, -1.9 + 2 * math.pi * 1.08, 70)
    ring = [(c.fx + rx * (1 + 0.04 * math.sin(3 * a)) * math.cos(a), c.fy + ry * (1 + 0.04 * math.cos(2 * a)) * math.sin(a)) for a in angs]
    hand_path(d, ring, col, wd, ease_inout(c.lt / 0.5))
    sd = 1 if c.fx < c.W * 0.6 else -1  # label on the side with more room
    lx = clamp(c.fx + sd * c.fw * 2.2, c.U * 0.12, c.W - c.U * 0.12); ly = clamp(c.fy - c.fw * 1.05, c.H * 0.1, c.H * 0.8)
    pts = arrow_pts(lx - sd * c.fw * 0.45, ly + c.fw * 0.3, c.fx + sd * rx * 1.04, c.fy - ry * 0.35, 0.25 * sd)
    k2 = ease_out((c.lt - 0.45) / 0.35)
    if k2 > 0: hand_path(d, pts, col, wd, k2)
    if k2 >= 0.99: arrow_head(d, pts, col, wd, c.U * 0.035)
    for j, (sx, sy) in enumerate(((c.fx - c.fw * 1.9, c.fy - c.fw * 1.2), (c.fx - c.fw * 1.5, c.fy + c.fw * 0.6), (c.fx + c.fw * 1.6, c.fy + c.fw * 0.3))):
        ks = ease_back((c.lt - 0.8 - 0.1 * j) / 0.25) * c.fw * 0.28
        if ks > 0:
            d.line([(sx - ks, sy), (sx + ks, sy)], fill=col, width=wd); d.line([(sx, sy - ks), (sx, sy + ks)], fill=col, width=wd)
    al = clamp((e.d - c.lt) / 0.2)
    comp(c, to_np(lay), 0, 0, al)
    if c.lt > 0.7:
        lab = text_img(e.o.get('text', 'me!'), c.U * 0.075, 'hand', col[:3], shadow=6)
        place(c, lab, lx + sd * lab.width * 0.15, ly - lab.height * 0.2, 0.7 + 0.3 * ease_back((c.lt - 0.7) / 0.3), 8 * sd, al, keep=True)


# ---------- pack 2: app-style effects (added 21 Oct 2026) ----------
def pop(c, t0, dur=0.3): return ease_back((c.lt - t0) / dur) if c.lt > t0 else 0.0
def fade(c, e, t=0.2): return clamp((e.d - c.lt) / t)
GREEN, BLUE, PURPLE, ORANGE, RED = (16, 185, 129), (124, 58, 237), (167, 139, 250), (124, 58, 237), (239, 68, 68)


def glass(c, w, h, r, cx, cy, amt=0.22, tint=(255, 255, 255), blur=None, alpha=240, dark=0.0, liquid=True):
    """A glass panel made from whatever sits behind it. liquid=True (default since 27 Oct 2026) is see-through liquid
    glass after liquid-glass-js (MIT, dashersw): light blur, refraction bending the room at the rim, a red/blue fringe
    (after React Bits' GlassSurface) and a specular edge lit from the top-left. liquid=False is the old frosted card."""
    w, h = int(w), int(h); blur = blur or max(8, c.W // 40); x0, y0 = int(cx - w / 2), int(cy - h / 2)
    if not liquid:
        pad = blur * 2
        xs = np.clip(np.arange(x0 - pad, x0 + w + pad), 0, c.W - 1); ys = np.clip(np.arange(y0 - pad, y0 + h + pad), 0, c.H - 1)
        reg = cv2.GaussianBlur(np.ascontiguousarray(c.img[np.ix_(ys, xs)]), (0, 0), blur)[pad:pad + h, pad:pad + w]
        reg = reg * (1 - dark) * (1 - amt) + np.float32(tint) / 255 * amt
        im = Image.fromarray((np.clip(reg, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(r), fill=alpha); im.putalpha(m)
        ImageDraw.Draw(im).rounded_rectangle([1, 1, w - 2, h - 2], int(r), outline=(255, 255, 255, 120), width=max(2, c.W // 540))
        return im
    u = c.W / 2160; pad = int(140 * u) + 4
    xs = np.clip(np.arange(x0 - pad, x0 + w + pad), 0, c.W - 1); ys = np.clip(np.arange(y0 - pad, y0 + h + pad), 0, c.H - 1)
    tex = cv2.GaussianBlur(np.ascontiguousarray(c.img[np.ix_(ys, xs)]), (0, 0), max(3.0, blur * 0.3))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); r = max(2.0, float(r))
    q = np.stack([np.abs(xx - w / 2) - (w / 2 - r), np.abs(yy - h / 2) - (h / 2 - r)], -1)
    sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.maximum(q[..., 0], q[..., 1]), 0) - r
    d = np.maximum(-sdf, 0) / u
    nx, ny = xx - w / 2, yy - h / 2; nl = np.sqrt(nx * nx + ny * ny) + 1e-3; nx, ny = nx / nl, ny / nl
    k = (70 * np.exp(-d / 14) + 34 * np.exp(-d / 70) + 10 * np.exp(-d / 260)) * u
    out = np.zeros((h, w, 3), np.float32)
    for ch, fr in enumerate((1.10, 1.0, 0.90)):
        out[..., ch] = cv2.remap(tex[..., ch], (xx + pad + nx * k * fr).astype(np.float32), (yy + pad + ny * k * fr).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * (1 - dark * 0.3) * 0.9 + np.float32(tint) / 255 * amt * 0.25 + 0.05 * (1.0 - 0.30 * (yy / h))[..., None] - 0.04
    spec = np.exp(-d / 5) * np.clip(0.55 - 0.45 * (nx * 0.6 + ny * 0.8), 0, 1)
    out = np.clip(out + (spec * 0.85 + np.exp(-d / 30) * 0.10)[..., None], 0, 1)
    a = (np.clip(0.5 - sdf, 0, 1) * alpha).astype(np.uint8)
    im = Image.fromarray((out * 255).astype(np.uint8)).convert('RGBA'); im.putalpha(Image.fromarray(a))
    return im


def face_chip(c, e, size):
    """A round avatar cut from your own face (grabbed once, at the start of the effect)."""
    def grab():
        r = c.fw * 0.9; x0, y0 = int(max(0, c.fx - r)), int(max(0, c.fy - r * 1.05))
        crop = c.img[y0:int(y0 + 2 * r), x0:int(x0 + 2 * r)]
        im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        return im
    src = cached(e, 'face', grab).resize((int(size), int(size)), Image.LANCZOS)
    m = Image.new('L', src.size, 0); ImageDraw.Draw(m).ellipse([0, 0, src.width - 1, src.height - 1], fill=255); src.putalpha(m)
    return src


def cursor(size):
    s = float(size); im = Image.new('RGBA', (int(s * 0.95), int(s * 1.45)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(3, 3), (3, s * 1.12), (s * 0.3, s * 0.87), (s * 0.5, s * 1.33), (s * 0.66, s * 1.26), (s * 0.46, s * 0.8), (s * 0.82, s * 0.8)]
    d.polygon(pts, fill=(255, 255, 255, 255)); d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=max(2, int(s / 14)), joint='curve')
    return shadowed(im, 6, 3, 110)


def tick(d, x, y, s, color=(255, 255, 255, 255), w=None):
    d.line([(x, y + s * 0.5), (x + s * 0.36, y + s * 0.85), (x + s, y + s * 0.1)], fill=color, width=w or max(3, int(s / 5)), joint='curve')


def lines_fit(lines, max_w, kind, start):
    size = start
    while size > 10 and max(font(kind, size).getlength(l) for l in lines) > max_w: size = int(size * 0.94)
    return size


def shift(c, dy):
    """Slide the whole picture (and you) down by dy pixels."""
    if abs(dy) < 0.5: return
    M = np.float32([[1, 0, 0], [0, 1, dy]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR); c.fy += dy


def thumb_grid(cards, cols, rows, cell, gap, i0=0, look=True):
    im = Image.new('RGBA', (cols * cell + (cols - 1) * gap, rows * int(cell * 1.25) + (rows - 1) * gap), (0, 0, 0, 0))
    ch = int(cell * 1.25)
    for k in range(cols * rows):
        src = cards[(i0 + k) % len(cards)]; src = vary(src, i0 + k) if look else src.convert('RGB')
        sw, sh = src.size; s = max(cell / sw, ch / sh); t = src.resize((max(cell, int(sw * s)), max(ch, int(sh * s))), Image.LANCZOS)
        l, tp = (t.width - cell) // 2, int((t.height - ch) * 0.3); t = t.crop((l, tp, l + cell, tp + ch)).convert('RGBA')
        m = Image.new('L', t.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cell - 1, ch - 1], max(4, cell // 12), fill=255); t.putalpha(m)
        im.alpha_composite(t, ((k % cols) * (cell + gap), (k // cols) * (ch + gap)))
    return im


def glass_widgets_v1(c, e):
    k0 = ramp(c, e, 0.3, 0)
    if e.o.get('grade', 'warm') != 'none': c.img = c.img * (1 - 0.6 * k0) + grade(c.img, e.o.get('grade', 'warm')) * 0.6 * k0
    al = fade(c, e); W = c.W; mg = W * 0.055
    S = W * 0.31; y_top = c.H * 0.07
    gd = float(e.o.get('dark', 0.2))
    a = glass(c, S, S, S * 0.2, mg + S / 2, y_top + S / 2, amt=0.14, dark=gd); d = ImageDraw.Draw(a)
    d.ellipse([S * 0.1, S * 0.115, S * 0.1 + S * 0.06, S * 0.115 + S * 0.06], fill=ORANGE + (255,))
    d.text((S * 0.2, S * 0.145), e.o.get('title', 'Claude'), font=font('uim', S * 0.085), fill=(255, 255, 255, 235), anchor='lm')
    d.text((S * 0.08, S * 0.2), e.o.get('text', '22'), font=font('uib', S * 0.44), fill=(255, 255, 255, 255))
    for j, ln in enumerate(e.o.get('sub', 'effects|one clip').split('|')):
        d.text((S * 0.1, S * (0.7 + 0.11 * j)), ln, font=font('uim', S * 0.085), fill=(255, 255, 255, 235))
    place(c, a, mg + S / 2, y_top + S / 2, 0.6 + 0.4 * pop(c, 0.0), 0, al * clamp(c.lt / 0.1), behind=True)
    bw, bh = W * 0.37, W * 0.15; bx = W - mg - bw / 2
    b = glass(c, bw, bh, bh * 0.28, bx, y_top + bh / 2, amt=0.14, dark=gd); d = ImageDraw.Draw(b)
    d.ellipse([bh * 0.17, bh * 0.2, bh * 0.17 + bh * 0.11, bh * 0.31], fill=(239, 68, 68, 255))
    d.text((bh * 0.36, bh * 0.255), 'Rendering', font=font('uim', bh * 0.19), fill=(255, 255, 255, 240), anchor='lm')
    p = ease_inout(c.lt / max(0.3, e.d * 0.85))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bw - bh * 0.17, bh * 0.6], bh * 0.05, fill=(255, 255, 255, 70))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bh * 0.17 + (bw - bh * 0.34) * max(0.04, p), bh * 0.6], bh * 0.05, fill=(255, 255, 255, 245))
    d.text((bh * 0.17, bh * 0.78), f"{e.o.get('label', 'glass UI')}  ·  {int(p * 100)}%", font=font('uim', bh * 0.14), fill=(255, 255, 255, 210), anchor='lm')
    place(c, b, bx, y_top + bh / 2, 0.6 + 0.4 * pop(c, 0.12), 0, al * clamp((c.lt - 0.12) / 0.1), behind=True)
    cy2 = y_top + bh + mg * 0.45 + bh / 2
    g = glass(c, bw, bh, bh * 0.28, bx, cy2, amt=0.14, dark=gd); d = ImageDraw.Draw(g)
    av = face_chip(c, e, bh * 0.62); g.alpha_composite(av, (int(bw - bh * 0.19 - av.width), int((bh - av.height) / 2)))
    d.text((bh * 0.2, bh * 0.36), e.o.get('name', 'Matt Penny'), font=font('uib', bh * 0.22), fill=(255, 255, 255, 255), anchor='lm')
    d.text((bh * 0.2, bh * 0.66), e.o.get('handle', '@matt_penny_applied_ai'), font=font('uim', bh * 0.14), fill=(255, 255, 255, 215), anchor='lm')
    place(c, g, bx, cy2, 0.6 + 0.4 * pop(c, 0.24), 0, al * clamp((c.lt - 0.24) / 0.1), behind=True)
    f1, f2 = font('uim', W * 0.045), font('uib', W * 0.045)
    pre, hi = e.o.get('pill', 'Edited by |Claude').split('|') if '|' in e.o.get('pill', 'Edited by |Claude') else (e.o['pill'], '')
    tw = f1.getlength(pre) + f2.getlength(hi); ph = W * 0.105; pw = tw + ph * 0.9; py = c.H * 0.865
    q = glass(c, pw, ph, ph / 2, W / 2, py, amt=0.16, tint=(26, 26, 46)); d = ImageDraw.Draw(q)
    d.text(((pw - tw) / 2, ph / 2), pre, font=f1, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((pw - tw) / 2 + f1.getlength(pre), ph / 2), hi, font=f2, fill=(167, 139, 250, 255), anchor='lm')
    place(c, shadowed(q, 14, 6, 70), W / 2, py, 0.7 + 0.3 * pop(c, 0.4), 0, al * clamp((c.lt - 0.4) / 0.1), guard=True)


@effect('red-collage', 'black and white you, a giant red word behind, kinetic type stacked beside you')
def fx_red_collage(c, e):
    k = ramp(c, e, 0.15, 0); m = c.m[..., None]
    bw = grade(c.img, 'bw'); out = bw * m + bw * 0.62 * (1 - m)
    c.img = c.img * (1 - k) + out * k
    vignette(c, 0.45 * k)
    red = rgb(e.o.get('color'), BLUE); al = fade(c, e)
    w = cached(e, 'w', lambda: fit_text(e.o.get('text', 'EDIT').upper(), c.W * 0.98, 'uib', 700, fill=red, glow=(red, 34)))
    s = 1.12 - 0.12 * ease_out(c.lt / 0.4)
    place(c, w, c.W / 2, max(w.height * 0.42, c.fy - c.fw * 1.05), s, 0, clamp(c.lt / 0.12) * al, behind=True)
    lines = e.o.get('lines', 'ONE CLIP.|22 EFFECTS.|ZERO APPS.').split('|')
    size = cached(e, 'sz', lambda: lines_fit(lines, c.U * 0.8, 'uib', int(c.U * 0.14)))
    y = min(max(c.H * 0.5, c.fy + c.fw * 1.55), c.H * 0.9 - size * len(lines))
    for j, ln in enumerate(lines):
        im = cached(e, ('l', j), lambda: text_img(ln, size, 'uib', red if j == 1 else (255, 255, 255), shadow=8))
        kk = clamp((c.lt - 0.18 - 0.13 * j) / 0.16)
        if kk > 0: place(c, im, c.U * 0.06 + im.width / 2, y + im.height / 2, 1.4 - 0.4 * ease_out(kk), 0, kk * al, guard=True)
        y += size * 1.0
    tag = cached(e, 'tag', lambda: text_img(e.o.get('tag', 'REC  ·  COLLAGE'), c.U * 0.03, 'mono', red))
    dot = Image.new('RGBA', (int(tag.height * 0.4),) * 2, (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, dot.width - 1, dot.width - 1], fill=red + (255,))
    blink = 1.0 if int(c.lt * 2.5) % 2 == 0 else 0.35
    place(c, dot, c.U * 0.07, c.H * 0.95, alpha=al * k * blink, guard=True)
    place(c, tag, c.U * 0.07 + dot.width + tag.width / 2, c.H * 0.95, alpha=al * k, guard=True)


@effect('split-headline', 'a clean headline card slides down and pushes you into the bottom of the frame')
def fx_split_headline(c, e):
    k = ease_out(c.lt / 0.38) * clamp((e.d - c.lt) / 0.25)
    ch = c.H * float(e.o.get('height', 0.36))
    shift(c, ch * float(e.o.get('push', 0.72)) * k)
    top = ch * k; W = c.W; col = rgb(e.o.get('color'), BLUE)
    lay = Image.new('RGBA', (W, int(ch)), (250, 250, 250, 255)); d = ImageDraw.Draw(lay)
    lines = e.o.get('text', 'Claude|edits my|reels.').split('|'); hl = e.o.get('hl', 'edits')
    S = cached(e, 'sz', lambda: lines_fit(lines, W * 0.84, 'uib', int(min(W * 0.135, ch * 0.74 / (len(lines) * 1.04))))); f = font('uib', S)
    x0, y0 = W * 0.07, ch * 0.13
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.12 - 0.08 * j) / 0.18)
        if kj <= 0: continue
        y = y0 + j * S * 1.04 + (1 - ease_out(kj)) * S * 0.35; a = int(255 * kj)
        x = x0
        for wi, word in enumerate(ln.split(' ')):
            tail = '.' if word.endswith('.') else ''; core = word[:-1] if tail else word
            wl = f.getlength(core)
            if core == hl:
                hk = ease_out((c.lt - 0.42) / 0.22); pad = S * 0.12
                if hk > 0: d.rounded_rectangle([x - pad, y + S * 0.02, x - pad + (wl + 2 * pad) * hk, y + S * 1.1], S * 0.16, fill=col + (a,))
                d.text((x, y), core, font=f, fill=((255, 255, 255, a) if hk > 0.55 else (20, 20, 22, a)))
            else: d.text((x, y), core, font=f, fill=(20, 20, 22, a))
            x += wl
            if tail: d.text((x, y), tail, font=f, fill=col + (a,)); x += f.getlength(tail)
            x += f.getlength(' ') + (S * 0.12 if core == hl else 0)
    d.rectangle([0, ch - max(5, W // 180), W, ch], fill=col + (255,))
    comp(c, lay, 0, top - ch)
    pt = text_img(e.o.get('pill', 'in seconds ↗'), c.U * 0.04, 'uib', (255, 255, 255))
    pill = rrect(pt.width + c.U * 0.03, pt.height * 0.95, pt.height * 0.47, col + (255,)); pill.alpha_composite(pt, (int(c.U * 0.015), int(-pt.height * 0.025)))
    place(c, shadowed(pill, 10, 4, 80), W - c.U * 0.07 - pill.width / 2, top + pill.height * 0.95, 0.6 + 0.4 * pop(c, 0.62), 0, clamp((c.lt - 0.62) / 0.1) * k, guard=True)


_grad = {}
@effect('pastel-word', 'a soft lavender backdrop, a giant word behind you and a profile card that gets followed')
def fx_pastel_word(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.2, 0); m = c.m[..., None]; al = fade(c, e)
    if (W, H) not in _grad:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); t = np.clip((yy / H) * 0.8 + (xx / W) * 0.2, 0, 1)[..., None]
        _grad[(W, H)] = np.float32([0.70, 0.67, 0.97]) * (1 - t) + np.float32([0.93, 0.90, 1.0]) * t
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    bg = _grad[(W, H)] * (0.86 + 0.22 * lum)
    you = np.clip(c.img * 0.93 + 0.05, 0, 1)
    c.img = c.img * (1 - k) + (you * m + bg * (1 - m)) * k
    word = cached(e, 'w', lambda: fit_text(e.o.get('text', 'REELS').upper(), W * 0.96, 'uib', 700, fill=(255, 255, 255)))
    dk = ease_out(c.lt / 0.45)
    place(c, shadowed(word, 24, 12, 60), W / 2, max(word.height * 0.45, c.fy - c.fw * 1.2) - (1 - dk) * H * 0.06, 1, 0, al * clamp(c.lt / 0.15), behind=True)
    cw, chh = c.U * 0.86, c.U * 0.15; cy = min(H * 0.865, H - chh * 0.6 - H * 0.03) + (1 - ease_out((c.lt - 0.15) / 0.35)) * H * 0.2
    card_ = rrect(cw, chh, chh * 0.3, (255, 255, 255, 248)); d = ImageDraw.Draw(card_)
    av = face_chip(c, e, chh * 0.64); card_.alpha_composite(av, (int(chh * 0.18), int((chh - av.height) / 2)))
    d.text((chh * 0.98, chh * 0.38), e.o.get('name', 'Matt Penny'), font=font('uib', chh * 0.22), fill=(26, 26, 46, 255), anchor='lm')
    h1 = e.o.get('handle', '@matt_penny_applied_ai  ·  '); f = font('uim', chh * 0.15)
    d.text((chh * 0.98, chh * 0.66), h1, font=f, fill=(100, 100, 140, 255), anchor='lm')
    d.text((chh * 0.98 + f.getlength(h1), chh * 0.66), e.o.get('role', 'creator'), font=f, fill=PURPLE + (255,), anchor='lm')
    at = e.d * 0.6; on = c.lt >= at
    bx = cw - chh * 0.22
    d.text((bx, chh / 2), 'Following' if on else 'Follow', font=font('uib', chh * 0.2), fill=((100, 100, 140, 255) if on else PURPLE + (255,)), anchor='rm')
    sq = 1 - 0.06 * math.sin(math.pi * clamp((c.lt - at) / 0.25)) if on else 1
    place(c, shadowed(card_, 18, 8, 90), W / 2, cy, sq, 0, al * clamp((c.lt - 0.15) / 0.12), guard=True)
    cu = cached(e, 'cur', lambda: cursor(c.U * 0.06))
    ck = ease_inout((c.lt - 0.25) / max(0.2, at - 0.3))
    tx, ty = W / 2 + cw / 2 - chh * 0.55, cy + chh * 0.12
    sx, sy = W * 1.02, H * 1.02
    place(c, cu, sx + (tx - sx) * ck + cu.width / 2, sy + (ty - sy) * ck + cu.height / 2, 0.85 if on and c.lt - at < 0.15 else 1, 0, al * clamp((c.lt - 0.25) / 0.1))


_gp = {}
@effect('check-pills', 'grid-paper room, your reels pinned behind you and blue pills that get clicked')
def fx_check_pills(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.15, 0); m = c.m[..., None]; al = fade(c, e)
    if (W, H) not in _gp:
        g = np.ones((H, W, 3), np.float32) * np.float32([0.935, 0.945, 0.96]); st = max(20, W // 20); lw = max(1, W // 700)
        for x in range(0, W, st): g[:, x:x + lw] = np.float32([0.86, 0.875, 0.9])
        for y in range(0, H, st): g[y:y + lw] = np.float32([0.86, 0.875, 0.9])
        _gp[(W, H)] = g
    c.img = c.img * (1 - k) + (c.img * m + _gp[(W, H)] * (1 - m)) * k
    def board(i, title):
        bw = int(min(W * 0.44, c.U * 0.62, H * 0.5)); im = rrect(bw, int(bw * 1.12), bw * 0.07, (255, 255, 255, 255)); d = ImageDraw.Draw(im)
        d.ellipse([bw * 0.06, bw * 0.055, bw * 0.06 + bw * 0.09, bw * 0.145], fill=(239, 68, 68, 255))
        d.text((bw * 0.19, bw * 0.1), title, font=font('uib', bw * 0.06), fill=(26, 26, 46, 255), anchor='lm')
        gr = thumb_grid(e.cards, 3, 3, int(bw * 0.28), int(bw * 0.025), i0=i * 3)
        im.alpha_composite(gr, ((bw - gr.width) // 2, int(bw * 0.2))); return shadowed(im, 16, 8, 70)
    b1 = cached(e, 'b1', lambda: board(0, e.o.get('handle', '@matt_penny_applied_ai')))
    b2 = cached(e, 'b2', lambda: board(1, e.o.get('board', 'Reels  ·  22 effects')))
    by = max(H * 0.17, c.fy - c.fw * 0.9)
    place(c, b1, W * 0.25, by, 0.6 + 0.4 * pop(c, 0.0), 8, al * clamp(c.lt / 0.1), behind=True, keep=True)
    place(c, b2, W * 0.76, by - c.U * 0.02, 0.6 + 0.4 * pop(c, 0.1), -8, al * clamp((c.lt - 0.1) / 0.1), behind=True, keep=True)
    names = e.o.get('text', 'Hook|Captions|Cuts|B-roll').split('|')
    spots = [(-0.95, 2.35), (0.55, 2.0), (-0.35, 2.95), (0.95, 2.75), (0.1, 3.45), (-1.1, 3.3)]
    ph = c.U * 0.078; cu = cached(e, 'cur', lambda: cursor(c.U * 0.055))
    pos = []
    for i, n in enumerate(names):
        sx, sy = spots[i % len(spots)]
        x = clamp(c.fx + sx * c.fw * 1.6, W * 0.16, W * 0.84); y = clamp(c.fy + sy * c.fw, H * 0.3, H * 0.9)
        t0 = 0.22 + 0.2 * i; pos.append((x, y, t0))
        if c.lt < t0: continue
        clicked = c.lt >= t0 + 0.12
        t = text_img(n, ph * 0.42, 'uib', (255, 255, 255)); pw = int(t.width + ph * (0.75 if clicked else 0.35))
        pill = rrect(pw, ph, ph / 2, BLUE + (255,)); pill.alpha_composite(t, (int(ph * 0.18), int((ph - t.height) / 2)))
        if clicked: tick(ImageDraw.Draw(pill), pw - ph * 0.55, ph * 0.33, ph * 0.33)
        sq = 1 - 0.1 * math.sin(math.pi * clamp((c.lt - t0 - 0.12) / 0.2))
        place(c, shadowed(pill, 10, 5, 90), x, y, (0.5 + 0.5 * pop(c, t0, 0.25)) * sq, 0, al, guard=True)
    if pos and c.lt > pos[0][2] - 0.1:
        seg = [p for p in pos if p[2] <= c.lt + 0.1]; tx, ty, t0 = seg[-1]
        px, py = (pos[len(seg) - 2][0], pos[len(seg) - 2][1]) if len(seg) > 1 else (W * 0.9, H * 0.95)
        q = ease_inout((c.lt - (t0 - 0.12)) / 0.2)
        place(c, cu, px + (tx - px) * q + ph * 0.3 + cu.width / 2, py + (ty - py) * q + ph * 0.1 + cu.height / 2, 1, 0, al)


def red_timeline(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.2, 0); m = c.m[..., None]; al = fade(c, e)
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    bg = np.clip(lum * np.float32([0.6, 0.3, 1.05]) * 0.85, 0, 1)
    you = np.clip(c.img * np.float32([1.04, 0.86, 0.82]), 0, 1)
    c.img = c.img * (1 - k) + (you * m + bg * (1 - m)) * k; vignette(c, 0.5 * k)
    red = rgb(e.o.get('color'), (124, 58, 237))
    sl = (1 - ease_out(c.lt / 0.35)) * W * 0.08; tb = clamp(c.lt / 0.15) * al
    secs = 21 + int(c.lt * 3)
    rec = text_img(f"{e.o.get('tc', 'REC')} 00:{secs:02d}", W * 0.032, 'mono', red)
    dot = Image.new('RGBA', (int(rec.height * 0.36),) * 2, (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, dot.width - 1, dot.width - 1], fill=red + (255,))
    comp(c, dot, W * 0.065 - sl, H * 0.075 + (rec.height - dot.height) / 2, tb * (1.0 if int(c.lt * 2.5) % 2 == 0 else 0.35), guard=True)
    comp(c, rec, W * 0.065 + dot.width * 1.4 - sl, H * 0.075, tb, guard=True)
    ti = cached(e, 'ti', lambda: text_img(e.o.get('text', 'AUTO-EDIT'), W * 0.13, 'uib', (255, 255, 255), shadow=10))
    comp(c, ti, W * 0.055 - sl, H * 0.075 + rec.height * 0.85, tb, guard=True)
    su = cached(e, 'su', lambda: text_img(e.o.get('sub', 'timeline by Claude'), W * 0.037, 'uim', red))
    comp(c, su, W * 0.065 - sl, H * 0.075 + rec.height * 0.85 + ti.height * 0.88, tb, guard=True)
    pw, phh = int(W * 0.9), int(H * 0.19); py = H * 0.755 + (1 - ease_out((c.lt - 0.1) / 0.35)) * H * 0.3
    lay = rrect(pw, phh, W * 0.03, (26, 26, 46, 215), (124, 58, 237, 90), 2); d = ImageDraw.Draw(lay)
    for j in range(4): d.text((pw * (0.05 + 0.3 * j), phh * 0.12), f'00:0{j}', font=font('mono', W * 0.022), fill=(148, 148, 184, 255), anchor='lm')
    clips = cached(e, 'cl', lambda: [(r, a, b) for r, segs in enumerate([[(0.04, 0.24), (0.26, 0.5), (0.53, 0.76), (0.79, 0.96)],
                                                                            [(0.04, 0.3), (0.33, 0.45), (0.48, 0.7)], [(0.04, 0.55), (0.6, 0.96)]]) for a, b in segs])
    p = 0.04 + 0.92 * clamp(c.lt / (e.d * 0.95)); ph_x = pw * p
    glow = Image.new('RGBA', (pw, phh), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for r, a, b in clips:
        y0 = phh * (0.27 + 0.235 * r); x0, x1 = pw * a, pw * b; on = pw * a < ph_x
        fill = red + (255,) if on else (91, 33, 182, 255)
        d.rounded_rectangle([x0, y0, x1, y0 + phh * 0.17], phh * 0.04, fill=fill)
        if on: gd.rounded_rectangle([x0, y0, x1, y0 + phh * 0.17], phh * 0.04, fill=red + (200,))
    d.line([(ph_x, phh * 0.2), (ph_x, phh * 0.97)], fill=(255, 255, 255, 255), width=max(3, W // 300))
    gd.line([(ph_x, phh * 0.2), (ph_x, phh * 0.97)], fill=(255, 255, 255, 255), width=max(8, W // 100))
    lay = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(W // 90)), lay)
    comp(c, lay, (W - pw) / 2, py, al, guard=True)


@effect('headline-box', 'a punch-in with a clean two-line headline, the second line in a white box')
def fx_headline_box(c, e):
    face_cam(c, 1 + (float(e.o.get('zoom', 1.2)) - 1) * ease_out(c.lt / 0.22), 0.45)
    W = c.W; al = fade(c, e); lines = e.o.get('text', 'How I got Claude|to edit my reels.').split('|')
    B = min(W, c.H * 0.75); S0 = cached(e, 'sz', lambda: lines_fit(lines, B * 0.84, 'uib', int(B * 0.085)))
    hx, cy_, hs, _ = clear_spot(c, e, B * 0.84, S0 * 1.3 * len(lines), ('above', 'side', 'below'), 0.6)
    S = max(8, int(S0 * hs)); y = cy_ - S * 1.3 * len(lines) / 2
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.1 - 0.12 * j) / 0.18)
        if kj <= 0: y += S * 1.3; continue
        boxed = j == len(lines) - 1
        t = cached(e, ('t', j), lambda: text_img(ln, S, 'uib', (26, 26, 46) if boxed else (255, 255, 255), shadow=0 if boxed else 9))
        if boxed:
            bx = rrect(t.width - S * 0.15, S * 1.22, S * 0.08, (255, 255, 255, 255))
            wk = ease_out(kj); bx = bx.crop((0, 0, max(1, int(bx.width * wk)), bx.height))
            comp(c, bx, hx - (t.width - S * 0.15) / 2, y, al, guard=True)
        place(c, t, hx, y + S * 0.6, 0.92 + 0.08 * ease_out(kj), 0, al * kj, guard=True)
        y += S * 1.3


@effect('profile-wall', 'your profile grid fills the wall behind you while a counter ticks up')
def fx_profile_wall(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    def wall():
        pw = int(min(W * 0.92, c.U * 1.25)); ph = int(H * 0.36); im = rrect(pw, ph, c.U * 0.035, (26, 26, 46, 240)); d = ImageDraw.Draw(im)
        tabs = ('Posts', 'Reels', 'Tagged'); f = font('uim', min(ph * 0.07, c.U * 0.032))
        for j, tb in enumerate(tabs):
            x = pw * (0.2 + 0.3 * j); d.text((x, ph * 0.065), tb, font=f, fill=((255, 255, 255, 255) if j == 1 else (100, 100, 140, 255)), anchor='mm')
            if j == 1: d.rectangle([x - pw * 0.08, ph * 0.1, x + pw * 0.08, ph * 0.1 + 4], fill=(255, 255, 255, 255))
        cell = int(min(pw * 0.225, (ph * 0.82 - pw * 0.012) / 2 / 1.25))
        gr = thumb_grid(e.cards, 4, 2, cell, int(pw * 0.012), look=False)
        im.alpha_composite(gr, ((pw - gr.width) // 2, int(ph * 0.14))); return shadowed(im, 20, 10, 110)
    wl = cached(e, 'wall', wall)
    place(c, wl, W / 2, H * 0.03 + wl.height / 2, 0.94 + 0.06 * ease_out(c.lt / 0.35), 0, al * clamp(c.lt / 0.15), behind=True, keep=True)
    cw, chh = c.U * 0.76, c.U * 0.25; cy = min(H - chh / 2 - H * 0.04, c.fy + c.fw * 2.6)
    g = glass(c, cw, chh, chh * 0.18, W / 2, cy, amt=0.5, tint=(26, 26, 46)); d = ImageDraw.Draw(g)
    target = int(e.o.get('count', 197000)); n = int(target * ease_out((c.lt - 0.2) / 0.8))
    swap = clamp((c.lt - 1.15) / 0.2)
    if swap < 1: d.text((cw / 2, chh * 0.33), f'{n:,}', font=font('uib', chh * 0.3), fill=(255, 255, 255, int(255 * (1 - swap))), anchor='mm')
    if swap > 0: d.text((cw / 2, chh * 0.33), e.o.get('label', 'views'), font=font('uib', chh * 0.3), fill=(255, 255, 255, int(255 * swap)), anchor='mm')
    av = face_chip(c, e, chh * 0.3); g.alpha_composite(av, (int(chh * 0.14), int(chh * 0.58)))
    d.text((chh * 0.52, chh * 0.68), e.o.get('name', 'matt_penny_applied_ai'), font=font('uib', chh * 0.09), fill=(255, 255, 255, 255), anchor='lm')
    d.text((chh * 0.52, chh * 0.8), e.o.get('sub', 'top reel'), font=font('uim', chh * 0.075), fill=(148, 148, 184, 255), anchor='lm')
    on = c.lt >= e.d * 0.7
    d.rounded_rectangle([cw - chh * 0.95, chh * 0.62, cw - chh * 0.14, chh * 0.86], chh * 0.12, fill=((26, 26, 46, 255) if on else (255, 255, 255, 255)))
    d.text((cw - chh * 0.545, chh * 0.74), 'Following' if on else 'Follow', font=font('uib', chh * 0.08), fill=((255, 255, 255, 255) if on else (26, 26, 46, 255)), anchor='mm')
    place(c, g, W / 2, cy + (1 - ease_out((c.lt - 0.05) / 0.3)) * H * 0.1, 1, 0, al * clamp((c.lt - 0.05) / 0.12), guard=True)


@effect('tier-list', 'a tier list drops in front of you and Claude flies into S tier')
def fx_tier_list(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    U = c.U
    tiers = [('S', (91, 33, 182)), ('A', (124, 58, 237)), ('B', (167, 139, 250)), ('C', (196, 181, 253)), ('D', (221, 214, 254)), ('F', (237, 233, 254))]
    cw = int(U * 0.66); rh = int(U * 0.082); pad = int(U * 0.015); chh = pad * 2 + rh * 6 + pad * 5
    ttl = cached(e, 'ttl', lambda: fit_text(e.o.get('title', 'best way to edit a reel?'), cw, 'serif', int(U * 0.08), fill=YELLOW, shadow=8))
    fill = dict(zip('BCDF', e.o.get('others', 'templates|timelines|apps|doing it by hand').split('|')))
    def board():
        im = rrect(cw, chh, U * 0.025, (26, 26, 46, 240)); d = ImageDraw.Draw(im)
        for i, (lab, col) in enumerate(tiers):
            y = pad + i * (rh + pad)
            d.rounded_rectangle([pad, y, pad + rh, y + rh], rh * 0.14, fill=col + (255,))
            d.text((pad + rh / 2, y + rh / 2), lab, font=font('uib', rh * 0.5), fill=(26, 26, 46, 255), anchor='mm')
            d.rounded_rectangle([pad * 2 + rh, y, cw - pad, y + rh], rh * 0.14, fill=(26, 26, 46, 255))
            if lab in fill:
                f = font('uim', rh * 0.3); tw = f.getlength(fill[lab]) + rh * 0.4
                d.rounded_rectangle([pad * 3 + rh, y + rh * 0.15, pad * 3 + rh + tw, y + rh * 0.85], rh * 0.12, fill=(100, 100, 140, 255))
                d.text((pad * 3 + rh + rh * 0.2, y + rh / 2), fill[lab], font=f, fill=(250, 250, 250, 255), anchor='lm')
        return shadowed(im, 18, 10, 120)
    bd = cached(e, 'bd', board)
    gx, gy, gs, _ = clear_spot(c, e, bd.width, bd.height + ttl.height, ('side', 'below'), 0.8, floor=0.6)
    if gs < 1: bd = bd.resize((int(bd.width * gs), int(bd.height * gs)), Image.BILINEAR); ttl = ttl.resize((int(ttl.width * gs), int(ttl.height * gs)), Image.BILINEAR); rh, pad = rh * gs, pad * gs
    top = gy - (bd.height + ttl.height) / 2
    place(c, ttl, gx, top + ttl.height / 2, 0.9 + 0.1 * ease_out(c.lt / 0.3), 0, al * clamp(c.lt / 0.15), guard=True)
    k = ease_back(c.lt / 0.35); bx, by = gx, top + ttl.height + bd.height / 2 + (1 - k) * H * 0.15
    place(c, bd, bx, by, 1, 0, al * clamp(c.lt / 0.12), guard=True)
    tile = cached(e, 'tile', lambda: shadowed(rrect(int(rh * 2.6), int(rh * 0.8), rh * 0.16, ORANGE + (255,)), 8, 4, 100))
    tx = cached(e, 'tx', lambda: text_img(e.o.get('item', 'Claude'), rh * 0.36, 'uib', (255, 255, 255)))
    tl = tile.copy(); tl.alpha_composite(tx, ((tl.width - tx.width) // 2, (tl.height - tx.height) // 2 - 3))
    sx, sy = (W - U * 0.1) if bx < c.fx else U * 0.1, c.fy + c.fw * 0.4
    ex = bx - bd.width / 2 + 18 * gs + pad * 3 + rh + tile.width / 2 - 10 * gs; ey = by - bd.height / 2 + 18 * gs + pad + rh / 2
    q = ease_back((c.lt - 0.45) / 0.4)
    if c.lt > 0.4: place(c, tl, sx + (ex - sx) * q, sy + (ey - sy) * q, (1.25 - 0.25 * clamp(q)), 18 * (1 - clamp(q)), al, guard=True)


@effect('broll-split', 'split screen: b-roll on top with a price-tag sticker, you on the bottom')
def fx_broll_split(c, e):
    W, H = c.W, c.H; k = ease_out(c.lt / 0.3) * clamp((e.d - c.lt) / 0.2); al = fade(c, e)
    shift(c, (H * 0.72 - c.fy) * k)
    sh = int(H * 0.5 * k)
    if sh > 2:
        src = e.cards[int(e.o.get('pick', 0)) % len(e.cards)].convert('RGB')
        z = 1.0 + 0.06 * clamp(c.lt / e.d); tw, th = int(W * z), int(H * 0.5 * z)
        s = max(tw / src.width, th / src.height); im = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.BILINEAR)
        l, t = (im.width - W) // 2, int((im.height - H * 0.5) * 0.35); im = im.crop((l, t, l + W, t + int(H * 0.5)))
        top = np.asarray(im, np.float32) / 255
        c.img[:sh] = top[int(H * 0.5) - sh:]; c.m[:sh] = 0
        c.img[max(0, sh - 3):sh + 3] = 1.0
    tag = cached(e, 'tag', lambda: text_img(e.o.get('text', '4 hrs  →  4 min'), W * 0.06, 'uib', (26, 26, 46)))
    tw, th = int(tag.width + W * 0.11), int(tag.height * 1.25)
    st = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(st); n = th * 0.5
    d.polygon([(0, th / 2), (n, 0), (tw, 0), (tw, th), (n, th)], fill=(255, 255, 255, 255))
    d.ellipse([n * 0.55, th / 2 - n * 0.16, n * 0.87, th / 2 + n * 0.16], fill=(243, 240, 255, 255))
    st.alpha_composite(tag, (int(n * 1.05), (th - tag.height) // 2))
    place(c, shadowed(st, 12, 6, 110), W * 0.66, H * 0.39 * k + H * 0.0, 0.5 + 0.5 * pop(c, 0.3), 8, al * clamp((c.lt - 0.3) / 0.08))


@effect('phone-fan', 'your reels fan out like a hand of phones in front of you, under a two-line headline')
def fx_phone_fan(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    lines = e.o.get('text', '22 effects.|zero editing apps.').split('|')
    B = min(W, H * 0.75); S0 = cached(e, 'sz', lambda: lines_fit(lines, B * 0.84, 'uib', int(B * 0.08)))
    hx, cy_, hs, _ = clear_spot(c, e, B * 0.95, S0 * 1.3 * len(lines), ('above', 'side'), 0.6, floor=0.45)  # the phones take the space under your chin
    S = max(8, int(S0 * hs)); y = cy_ - S * 1.3 * len(lines) / 2
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.05 - 0.1 * j) / 0.18); last = j == len(lines) - 1
        t = cached(e, ('t', j), lambda: text_img(ln, S, 'uib', (26, 26, 46) if last else (255, 255, 255), shadow=0 if last else 9))
        if last: comp(c, rrect(t.width - S * 0.15, S * 1.22, S * 0.08, (255, 255, 255, 255)), hx - (t.width - S * 0.15) / 2, y, al * kj, guard=True)
        place(c, t, hx, y + S * 0.6, 1, 0, al * kj, guard=True); y += S * 1.3
    pw = int(W * 0.23); ph = int(pw * 2.0)
    def phone(i):
        im = rrect(pw, ph, pw * 0.16, (26, 26, 46, 255))
        scr = card(vary(e.cards[i % len(e.cards)], i) if e.o.get('images') is None else e.cards[i % len(e.cards)], pw - 10)
        inner = scr.crop(((scr.width - (pw - 10)) // 2, (scr.height - (ph - 10)) // 2 - 6, (scr.width + pw - 10) // 2, (scr.height + ph - 10) // 2 - 6))
        im.alpha_composite(inner, (5, 5))
        ImageDraw.Draw(im).rounded_rectangle([pw * 0.36, ph * 0.025, pw * 0.64, ph * 0.045], pw * 0.03, fill=(0, 0, 0, 255))
        return shadowed(im, 14, 8, 120)
    ph_ = cached(e, 'ph', lambda: [phone(i) for i in range(4)])
    cx = W / 2 * 0.5 + c.fx * 0.5; cy = max(c.fy + c.fw * 1.1 + ph / 2, H * 0.62)
    cy = min(cy, H - ph * 0.42)
    for i, o in enumerate((-1.5, -0.5, 0.5, 1.5)):
        q = ease_back((c.lt - 0.2 - 0.06 * i) / 0.4)
        place(c, ph_[i], cx + o * W * 0.19 * q, cy + o * o * W * 0.025 * q, 0.9, -o * 11 * q, al * clamp((c.lt - 0.2) / 0.1), guard=True)


@effect('dot-reveal', 'your shot builds itself out of glowing dots, then snaps into the full picture')
def fx_dot_reveal(c, e):
    p = clamp(c.lt / e.d); W, H = c.W, c.H
    cell = max(6, int(W * float(e.o.get('cell', 0.017)))); gh, gw = H // cell + 1, W // cell + 1
    def geo():
        yy, xx = np.mgrid[0:gh * cell, 0:gw * cell].astype(np.float32)
        dist = np.sqrt((xx % cell - cell / 2 + 0.5) ** 2 + (yy % cell - cell / 2 + 0.5) ** 2)[:H, :W]
        return dist, np.random.default_rng(5).random((gh, gw)).astype(np.float32)
    dist, thr = cached(e, 'geo', geo)
    pad = np.pad(c.img, ((0, gh * cell - H), (0, gw * cell - W), (0, 0)), mode='edge')
    small = cv2.resize(pad, (gw, gh), interpolation=cv2.INTER_AREA)
    lum = small @ np.float32([0.299, 0.587, 0.114])
    on = np.clip((p * 1.7 - thr * 0.95) / 0.3, 0, 1)
    sparkle = 0.75 + 0.25 * np.sin(thr * 40 + c.lt * 18)
    r = (0.18 + 0.32 * np.sqrt(np.clip(lum, 0, 1))) * cell * on
    col = rgb(e.o.get('color'), (124, 58, 237))
    q2 = clamp((p - 0.3) / 0.35)
    dc = np.float32(col) / 255 * (0.55 + 0.6 * lum[..., None]) * sparkle[..., None] * (1 - q2) + np.clip(small * 1.15, 0, 1) * q2
    R = np.repeat(np.repeat(r, cell, 0), cell, 1)[:H, :W]
    DC = np.repeat(np.repeat(dc, cell, 0), cell, 1)[:H, :W]
    dm = np.clip(R - dist + 0.5, 0, 1)[..., None]
    bgc = np.float32(rgb(e.o.get('bg'), (26, 26, 46))) / 255
    dots = bgc * (1 - dm) + DC * dm
    q = ease_inout((p - 0.6) / 0.4)
    c.img = dots * (1 - q) + c.img * q


def tracked(s, size, kind, fill, spacing, colors=None):
    """Letter-spaced text. colors: optional per-character fill list."""
    f = font(kind, size); w = sum(f.getlength(ch) for ch in s) + spacing * max(0, len(s) - 1)
    bb = f.getbbox('Ag'); im = Image.new('RGBA', (int(w) + 8, int(bb[3] - bb[1] + size * 0.4)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 4
    for i, ch in enumerate(s):
        d.text((x, -bb[1] + size * 0.2), ch, font=f, fill=(colors[i] if colors else fill) + (255,)); x += f.getlength(ch) + spacing
    return im


def rich(parts, size, kind, base, accent, accent_kind=None, shadow=0):
    """One line of text where *starred* words take the accent colour (and optionally another font)."""
    segs = []
    for j, p in enumerate(parts.split('*')):
        if p: segs.append(text_img(p, size, accent_kind if (j % 2 and accent_kind) else kind, accent if j % 2 else base, shadow=shadow))
    pad = int(size * 0.2 + shadow * 2.5) + 4
    w = sum(s.width - 2 * pad for s in segs) + 2 * pad; h = max(s.height for s in segs)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    for s in segs: im.alpha_composite(s, (x, (h - s.height) // 2)); x += s.width - 2 * pad
    return im


@effect('headline-wall', 'a wall of your own reel headlines piles up behind your head, then your total views pop in front')
def fx_headline_wall(c, e):
    W, H = c.W, c.H; u = W / 1080; al = fade(c, e)
    items = [x.split('::') for x in e.o.get('text', 'Protect your personal data with ChatGPT Agent Mode::197K views|Easiest no-code scroll animation websites::124K views|'
                                         'How to make your resume un-rejectable using Claude::83K views|Same prompt: Claude Fable 5 vs ChatGPT 5.6 Sol::50K views|'
                                         'Jev, the new AI model faster and cheaper than Claude::40K views|Scrape LinkedIn automatically::38K views|'
                                         'Protect your personal data on the internet::140K views').split('|')]
    looks = [((255, 255, 255), (26, 26, 46)), ((26, 26, 46), (255, 255, 255)), ((243, 240, 255), (26, 26, 46)), ((124, 58, 237), (255, 255, 255))]
    def hcard(i):
        title, meta = (items[i % len(items)] + [''])[:2]; bg, fg = looks[i % len(looks)]
        cw = int(c.U * 0.5); f = font('uib', cw * 0.085); words = title.split(' '); lines, cur = [], ''
        for w_ in words:
            tst = (cur + ' ' + w_).strip()
            if f.getlength(tst) > cw * 0.84 and cur: lines.append(cur); cur = w_
            else: cur = tst
        lines.append(cur); lh = cw * 0.1
        chh = int(cw * 0.1 + lh * len(lines) + cw * 0.16)
        im = rrect(cw, chh, cw * 0.04, bg + (255,)); d = ImageDraw.Draw(im)
        for j, ln in enumerate(lines): d.text((cw * 0.08, cw * 0.07 + j * lh), ln, font=f, fill=fg + (255,))
        my = chh - cw * 0.085; s = cw * 0.04
        d.polygon([(cw * 0.08, my - s / 2), (cw * 0.08, my + s / 2), (cw * 0.08 + s * 0.9, my)], fill=(124, 58, 237, 255))
        d.text((cw * 0.08 + s * 1.5, my), ('@matt_penny_applied_ai  ·  ' + meta) if meta else '@matt_penny_applied_ai', font=font('uim', cw * 0.045), fill=fg + (170,), anchor='lm')
        return shadowed(im, 14, 8, 110)
    N = int(e.o.get('count', 13))
    cards = cached(e, 'cards', lambda: [hcard(i) for i in range(N)])
    pos = cached(e, 'pos', lambda: [(random.Random(i * 7 + 1).uniform(0.2, 0.8), random.Random(i * 7 + 2).uniform(0.07, 0.42), random.Random(i * 7 + 3).uniform(-9, 9)) for i in range(N)])
    gap = float(e.o.get('gap', 0.09))
    for i in range(N):
        t0 = i * gap
        if c.lt < t0: break
        x, y, r = pos[i]; kk = ease_back((c.lt - t0) / 0.22)
        place(c, cards[i], x * W, y * H, 0.55 + 0.45 * kk, r, al * clamp((c.lt - t0) / 0.06), behind=True, keep=True)
    t1 = N * gap + 0.1
    if c.lt > t1:
        tot = e.o.get('total', '672K'); lab = e.o.get('label', 'views from 7 reels')
        a = text_img(tot, 96 * u, 'anton', (255, 255, 255)); b = text_img(lab, 34 * u, 'uib', (255, 255, 255))
        pw = int(a.width + b.width + 30 * u); ph = int(max(a.height, b.height) + 10 * u)
        pill = rrect(pw, ph, ph * 0.28, (124, 58, 237, 245)); pill.alpha_composite(a, (int(8 * u), (ph - a.height) // 2)); pill.alpha_composite(b, (int(a.width + 8 * u), (ph - b.height) // 2))
        place(c, shadowed(pill, 18, 8, 110), W / 2, max(c.fy + c.fw * 1.8, H * 0.6), 0.6 + 0.4 * pop(c, t1, 0.3), -3, al * clamp((c.lt - t1) / 0.08), guard=True)


@effect('checklist', 'a Claude task list builds under your chin: each step spins, then ticks green')
def fx_checklist(c, e):
    W, H = c.W, c.H; u = min(W, H) / 1080; al = fade(c, e)
    rows = [x.split('::') for x in e.o.get('text', 'Found your face::every frame|Cut you out of the room::AI mask|Put the text behind you::depth|'
                                        'Graded the colour::warm|Rendered in 4K::2160p').split('|')]
    n = len(rows)
    _, _, sc, _ = clear_spot(c, e, 972 * u, 120 * u + 104 * u * n + 26 * u, ('below', 'side'), 0.8); u *= sc
    cw = 972 * u; rh = 104 * u; hh = 120 * u; chh = hh + rh * n + 26 * u
    cx, cy, _, _ = clear_spot(c, e, cw / sc, chh / sc, ('below', 'side'), 0.8); cy += (1 - ease_out(c.lt / 0.35)) * H * 0.12
    span = max(0.4, e.d - 0.55); done_at = [0.3 + span * (i + 1) / n for i in range(n)]
    g = glass(c, cw, chh, 40 * u, cx, cy, amt=0.78, tint=(26, 26, 46), blur=int(30 * u)); d = ImageDraw.Draw(g)
    sx, sy = 44 * u, hh / 2
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        d.line([(sx, sy), (sx + 18 * u * math.cos(ang), sy + 18 * u * math.sin(ang))], fill=(124, 58, 237, 255), width=int(7 * u))
        d.line([(sx, sy), (sx + 18 * u * math.cos(ang + math.pi / 4), sy + 18 * u * math.sin(ang + math.pi / 4))], fill=(124, 58, 237, 255), width=int(5 * u))
    d.text((80 * u, hh / 2), e.o.get('title', 'Claude is editing your clip'), font=font('uib', 42 * u), fill=(255, 255, 255, 255), anchor='lm')
    nd = sum(c.lt >= t for t in done_at)
    d.text((cw - 36 * u, hh / 2), f'{nd} of {n}', font=font('uim', 28 * u), fill=(148, 148, 184, 255), anchor='rm')
    d.line([(30 * u, hh), (cw - 30 * u, hh)], fill=(255, 255, 255, 30), width=max(1, int(2 * u)))
    for i, (txt, meta) in enumerate([(r + [''])[:2] for r in rows]):
        y = hh + 13 * u + rh * i + rh / 2; x = 56 * u; r_ = 24 * u
        start = done_at[i - 1] if i else 0.3
        if c.lt >= done_at[i]:
            q = ease_back((c.lt - done_at[i]) / 0.25); rr = r_ * (0.6 + 0.4 * q)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(16, 185, 129, 255)); tick(d, x - rr * 0.5, y - rr * 0.45, rr, w=int(5 * u))
            fc, mc = (255, 255, 255, 255), (16, 185, 129, 255)
        elif c.lt >= start:
            a0 = (c.lt * 540) % 360; d.ellipse([x - r_, y - r_, x + r_, y + r_], outline=(255, 255, 255, 50), width=int(5 * u))
            d.arc([x - r_, y - r_, x + r_, y + r_], a0, a0 + 100, fill=(124, 58, 237, 255), width=int(5 * u)); fc, mc = (255, 255, 255, 255), (148, 148, 184, 255)
        else:
            d.ellipse([x - r_, y - r_, x + r_, y + r_], outline=(255, 255, 255, 60), width=int(4 * u)); fc, mc = (255, 255, 255, 110), (148, 148, 184, 90)
        d.text((x + 48 * u, y), txt, font=font('uib', 40 * u), fill=fc, anchor='lm')
        d.text((cw - 36 * u, y), meta, font=font('mono', 28 * u), fill=mc, anchor='rm')
    place(c, shadowed(g, 24, 12, 120), cx, cy, 1, 0, al * clamp(c.lt / 0.12), guard=True)


def np_thumb(c, w, h):
    """The current frame as a small PIL thumbnail (cropped to w:h around your face)."""
    ar = w / h; ch = c.H * 0.62; cw = ch * ar
    x0 = int(clamp(c.fx - cw / 2, 0, c.W - cw)); y0 = int(clamp(c.fy - ch * 0.4, 0, c.H - ch))
    crop = c.img[y0:int(y0 + ch), x0:int(x0 + cw)]
    return Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize((int(w), int(h)), Image.LANCZOS)


def glow_panel(w, h, r, top, bot, line, glow, gblur):
    """A rounded panel with a vertical gradient fill, a thin border and an outer glow."""
    w, h = int(w), int(h); pad = int(gblur * 2.2)
    out = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    g = Image.new('RGBA', out.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=glow)
    out.alpha_composite(g.filter(ImageFilter.GaussianBlur(gblur)))
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    fill = (np.float32(top) * (1 - t) + np.float32(bot) * t) * np.ones((1, w, 1), np.float32)
    body = Image.fromarray(np.concatenate([fill, np.full((h, w, 1), 255, np.float32)], 2).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255); body.putalpha(m)
    ImageDraw.Draw(body).rounded_rectangle([1, 1, w - 2, h - 2], r, outline=line, width=max(2, int(w / 400)))
    out.alpha_composite(body, (pad, pad))
    return out, pad


def np_thumb_pil(im, w, h):
    src = im.convert('RGB'); s = max(w / src.width, h / src.height)
    t = src.resize((max(w, int(src.width * s) + 1), max(h, int(src.height * s) + 1)), Image.LANCZOS)
    l, tp = (t.width - w) // 2, int((t.height - h) * 0.3); t = t.crop((l, tp, l + w, tp + h)).convert('RGBA')
    m = Image.new('L', t.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], max(3, w // 10), fill=255); t.putalpha(m)
    return t


def glass_widgets_v2(c, e):
    """More widgets, artifact-style: stat tile, render bar, profile, a mini views artifact, now-playing, calendar, a 4K ring and the Edited by Claude pill."""
    W, H = c.W, c.H; u = c.U / 1080
    k0 = ramp(c, e, 0.3, 0)
    if e.o.get('grade', 'warm') != 'none': c.img = c.img * (1 - 0.6 * k0) + grade(c.img, e.o.get('grade', 'warm')) * 0.6 * k0
    al = fade(c, e); gd = float(e.o.get('dark', 0.22)); white = (255, 255, 255)
    def bob(i): return 6 * u * math.sin(2 * math.pi * (c.lt * 0.55 + i * 0.17))
    def show(im, x, y, i, front=False):
        t0 = 0.07 * i
        if c.lt < t0: return
        place(c, im, x, y + bob(i), 0.6 + 0.4 * pop(c, t0, 0.32), 0, al * clamp((c.lt - t0) / 0.08), behind=not front, guard=front)
    G = lambda w, h, cx, cy, r=None: glass(c, w, h, r or min(w, h) * 0.2, cx, cy, amt=0.14, dark=gd)
    # 1 · stat tile
    S = 300 * u; ax, ay = 50 * u + S / 2, 118 * u + S / 2
    a = G(S, S, ax, ay); d = ImageDraw.Draw(a)
    d.ellipse([S * 0.1, S * 0.115, S * 0.16, S * 0.175], fill=ORANGE + (255,))
    d.text((S * 0.2, S * 0.145), e.o.get('title', 'Claude'), font=font('uim', S * 0.085), fill=white + (235,), anchor='lm')
    d.text((S * 0.08, S * 0.2), e.o.get('text', '38'), font=font('uib', S * 0.44), fill=white + (255,))
    for j, ln in enumerate(e.o.get('sub', 'effects|one clip').split('|')): d.text((S * 0.1, S * (0.7 + 0.11 * j)), ln, font=font('uim', S * 0.085), fill=white + (235,))
    show(a, ax, ay, 0)
    # 2 · render bar
    bw, bh = 400 * u, 150 * u; bx, by = W - 50 * u - bw / 2, 118 * u + bh / 2
    b = G(bw, bh, bx, by, bh * 0.28); d = ImageDraw.Draw(b); p = ease_inout(c.lt / max(0.3, e.d * 0.85))
    d.ellipse([bh * 0.17, bh * 0.2, bh * 0.28, bh * 0.31], fill=(239, 68, 68, 255))
    d.text((bh * 0.36, bh * 0.255), 'Rendering', font=font('uim', bh * 0.19), fill=white + (240,), anchor='lm')
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bw - bh * 0.17, bh * 0.6], bh * 0.05, fill=white + (70,))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bh * 0.17 + (bw - bh * 0.34) * max(0.04, p), bh * 0.6], bh * 0.05, fill=white + (245,))
    d.text((bh * 0.17, bh * 0.78), f"4K render  ·  {int(p * 100)}%", font=font('uim', bh * 0.14), fill=white + (210,), anchor='lm')
    show(b, bx, by, 1)
    # 3 · profile
    cy3 = by + bh / 2 + 22 * u + bh / 2
    g = G(bw, bh, bx, cy3, bh * 0.28); d = ImageDraw.Draw(g)
    av = face_chip(c, e, bh * 0.62); g.alpha_composite(av, (int(bw - bh * 0.19 - av.width), int((bh - av.height) / 2)))
    d.text((bh * 0.2, bh * 0.36), e.o.get('name', 'Matt Penny'), font=font('uib', bh * 0.22), fill=white + (255,), anchor='lm')
    d.text((bh * 0.2, bh * 0.66), e.o.get('handle', '@matt_penny_applied_ai'), font=font('uim', bh * 0.14), fill=white + (215,), anchor='lm')
    show(g, bx, cy3, 2)
    # 4 · views artifact (a mini page inside the glass)
    aw, ah = 330 * u, 330 * u; dx, dy = 50 * u + aw / 2, ay + S / 2 + 26 * u + ah / 2
    art = G(aw, ah, dx, dy, 44 * u); d = ImageDraw.Draw(art)
    d.text((24 * u, 30 * u), 'artifact · views.html', font=font('mono', 15 * u), fill=white + (220,), anchor='lm')
    inn = rrect(aw - 36 * u, ah - 74 * u, 20 * u, (250, 250, 250, 255)); di = ImageDraw.Draw(inn); iw, ih = inn.size
    for j in range(3): di.ellipse([14 * u + j * 16 * u, 14 * u, 24 * u + j * 16 * u, 24 * u], fill=((239, 68, 68), (245, 158, 11), (16, 185, 129))[j] + (255,))
    di.text((16 * u, 40 * u), 'Top reels', font=font('uib', 26 * u), fill=(26, 26, 46, 255))
    di.text((16 * u, 72 * u), '197K', font=font('anton', 44 * u), fill=(124, 58, 237, 255))
    vals = [197, 140, 124, 83, 50, 40, 38]; gx0, gx1, gy1 = 16 * u, iw - 16 * u, ih - 18 * u; bwid = (gx1 - gx0) / 7 * 0.66
    for j, v in enumerate(vals):
        q = ease_out((c.lt - 0.35 - 0.05 * j) / 0.4); hh = (ih * 0.42) * v / 197 * q; x0 = gx0 + (gx1 - gx0) * j / 7
        if hh > 1: di.rounded_rectangle([x0, gy1 - hh, x0 + bwid, gy1], 5 * u, fill=((167, 139, 250) if j == 0 else (124, 58, 237)) + (255,))
    art.alpha_composite(inn, (int(18 * u), int(56 * u)))
    show(art, dx, dy, 3)
    # 5 · now playing
    mw, mh = 360 * u, 220 * u; mx, my = W - 50 * u - mw / 2, cy3 + bh / 2 + 22 * u + mh / 2
    mu = G(mw, mh, mx, my, 40 * u); d = ImageDraw.Draw(mu); A = 96 * u
    t = np.linspace(0, 1, int(A), dtype=np.float32)[:, None, None]
    art2 = Image.fromarray(np.concatenate([(np.float32([167, 139, 250]) * (1 - t) + np.float32([91, 33, 182]) * t) * np.ones((1, int(A), 1), np.float32), np.full((int(A), int(A), 1), 255, np.float32)], 2).astype(np.uint8), 'RGBA')
    am = Image.new('L', art2.size, 0); ImageDraw.Draw(am).rounded_rectangle([0, 0, art2.width - 1, art2.height - 1], 16 * u, fill=255); art2.putalpha(am)
    ad = ImageDraw.Draw(art2)
    for k_ in range(6):
        ang = k_ * math.pi / 3; ad.line([(A / 2 - 26 * u * math.cos(ang), A / 2 - 26 * u * math.sin(ang)), (A / 2 + 26 * u * math.cos(ang), A / 2 + 26 * u * math.sin(ang))], fill=(255, 255, 255, 255), width=int(7 * u))
    mu.alpha_composite(art2, (int(22 * u), int(22 * u)))
    d.text((134 * u, 44 * u), 'NOW EDITING', font=font('mono', 15 * u), fill=white + (200,), anchor='lm')
    d.text((134 * u, 78 * u), e.o.get('song', 'soft UI pops'), font=font('uib', 28 * u), fill=white + (255,), anchor='lm')
    d.text((134 * u, 108 * u), 'sfx · 25.7s', font=font('uim', 20 * u), fill=white + (200,), anchor='lm')
    pp = clamp(c.lt / max(0.5, e.d)); d.rounded_rectangle([22 * u, 140 * u, mw - 22 * u, 146 * u], 3 * u, fill=white + (70,))
    d.rounded_rectangle([22 * u, 140 * u, 22 * u + (mw - 44 * u) * pp, 146 * u], 3 * u, fill=white + (240,))
    cxm, cym = mw / 2, 184 * u
    d.polygon([(cxm - 12 * u, cym - 16 * u), (cxm - 12 * u, cym + 16 * u), (cxm + 16 * u, cym)], fill=white + (255,))
    for sgn in (-1, 1):
        x = cxm + sgn * 80 * u
        d.polygon([(x - sgn * 10 * u, cym - 11 * u), (x - sgn * 10 * u, cym + 11 * u), (x + sgn * 6 * u, cym)], fill=white + (220,))
        d.polygon([(x + sgn * 4 * u, cym - 11 * u), (x + sgn * 4 * u, cym + 11 * u), (x + sgn * 20 * u, cym)], fill=white + (220,))
    show(mu, mx, my, 4)
    # 6 · calendar
    kw, kh = 330 * u, 190 * u; kx, ky = 50 * u + kw / 2, dy + ah / 2 + 26 * u + kh / 2
    ca = G(kw, kh, kx, ky, 40 * u); d = ImageDraw.Draw(ca)
    d.text((26 * u, 36 * u), e.o.get('day', 'WED'), font=font('uib', 22 * u), fill=(124, 58, 237, 255), anchor='lm')
    d.text((26 * u, 82 * u), e.o.get('date', '21'), font=font('uib', 56 * u), fill=white + (255,), anchor='lm')
    d.rounded_rectangle([22 * u, 120 * u, kw - 22 * u, 168 * u], 12 * u, fill=(124, 58, 237, 210))
    d.text((36 * u, 144 * u), e.o.get('event', 'Post 2 reels · tonight'), font=font('uib', 22 * u), fill=white + (255,), anchor='lm')
    show(ca, kx, ky, 5)
    # 7 · 4K ring
    R = 250 * u; rx, ry = W - 50 * u - R / 2, my + mh / 2 + 26 * u + R / 2
    rg = G(R, R, rx, ry, 56 * u); d = ImageDraw.Draw(rg); rp = ease_inout((c.lt - 0.4) / 1.0); rr = R * 0.34
    d.ellipse([R / 2 - rr, R / 2 - rr - 8 * u, R / 2 + rr, R / 2 + rr - 8 * u], outline=white + (60,), width=int(16 * u))
    if rp > 0: d.arc([R / 2 - rr, R / 2 - rr - 8 * u, R / 2 + rr, R / 2 + rr - 8 * u], -90, -90 + 360 * rp, fill=(16, 185, 129, 255), width=int(16 * u))
    d.text((R / 2, R / 2 - 8 * u), '4K', font=font('uib', 52 * u), fill=white + (255,), anchor='mm')
    d.text((R / 2, R - 26 * u), 'render', font=font('uim', 20 * u), fill=white + (210,), anchor='mm')
    show(rg, rx, ry, 6)
    # 8 · Edited by Claude pill (in front)
    f1, f2 = font('uim', c.U * 0.045), font('uib', c.U * 0.045); pre, hi = 'Edited by ', 'Claude'
    tw = f1.getlength(pre) + f2.getlength(hi); ph = c.U * 0.105; pw = tw + ph * 0.9; py = H * 0.875
    q = glass(c, pw, ph, ph / 2, W / 2, py, amt=0.16, tint=(26, 26, 46)); d = ImageDraw.Draw(q)
    d.text(((pw - tw) / 2, ph / 2), pre, font=f1, fill=white + (255,), anchor='lm')
    d.text(((pw - tw) / 2 + f1.getlength(pre), ph / 2), hi, font=f2, fill=(167, 139, 250, 255), anchor='lm')
    show(shadowed(q, 14, 6, 70), W / 2, py, 7, front=True)


@effect('glass-widgets', 'frosted glass phone widgets and mini artifacts float around your head, with an Edited by Claude pill')
def fx_glass_widgets(c, e):
    (glass_widgets_v1 if e.o.get('look') == 'simple' else glass_widgets_v2)(c, e)


@effect('timeline', 'a dark red cinematic grade with an editing timeline, a REC timecode and a glowing playhead')
def fx_timeline(c, e):
    studio = globals().get('studio_timeline')
    (studio if studio and e.o.get('look') != 'red' else red_timeline)(c, e)


_emoji = {}
def emoji(ch, size):
    """A colour emoji as an RGBA image (Apple Color Emoji on a Mac). Returns None where the font is missing."""
    k = (ch, int(size))
    if k not in _emoji:
        try:
            f = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', 160)
            im = Image.new('RGBA', (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).text((20, 10), ch, font=f, embedded_color=True)
            im = im.crop(im.getbbox()); _emoji[k] = im.resize((int(size), int(size * im.height / im.width)), Image.LANCZOS)
        except Exception:
            _emoji[k] = None
    return _emoji[k]


def comment_sheet(c, e):
    """Reels 1021 + VOX look: an Instagram Comments sheet above your head (your hair in front). The word types in, posts,
    gets a heart, then your reply drops in with a link chip."""
    W, H = c.W, c.H; u = W / 1080; al = fade(c, e)
    word = e.o.get('text', 'EFFECTS'); handle = e.o.get('handle', 'matt_penny_applied_ai')
    reply = e.o.get('reply', 'Sent you the pack'); chip = e.o.get('chip', '22 effects')
    sw, sh = 740 * u, 450 * u
    t_post = 0.3 + 0.06 * len(word) + 0.1; t_heart, t_rep = t_post + 0.25, t_post + 0.4
    sheet = rrect(sw, sh, 30 * u, (26, 26, 46, 248)); d = ImageDraw.Draw(sheet)
    white, grey, blue = (250, 250, 250, 255), (148, 148, 184, 255), (124, 58, 237, 255)
    d.rounded_rectangle([sw / 2 - 32 * u, 14 * u, sw / 2 + 32 * u, 20 * u], 3 * u, fill=(100, 100, 140, 255))
    d.text((sw / 2, 50 * u), 'Comments', font=font('uib', 26 * u), fill=white, anchor='mm')
    d.line([(0, 80 * u), (sw, 80 * u)], fill=(26, 26, 46, 255), width=max(1, int(2 * u)))
    def avatar(sz):
        a = Image.new('RGBA', (int(sz), int(sz)), (0, 0, 0, 0)); ad = ImageDraw.Draw(a)
        ad.ellipse([0, 0, sz - 1, sz - 1], fill=(124, 58, 237, 255)); ad.text((sz / 2, sz / 2), 'M', font=font('uib', sz * 0.5), fill=(255, 255, 255, 255), anchor='mm')
        return a
    if c.lt < t_post:
        d.text((sw / 2, 190 * u), 'Start the conversation.', font=font('uim', 21 * u), fill=grey, anchor='mm')
    else:
        q = ease_out((c.lt - t_post) / 0.25); oy = (1 - q) * -20 * u; a8 = int(255 * clamp(q * 1.5))
        av = avatar(46 * u); av.putalpha(av.split()[3].point(lambda v: v * a8 // 255)); sheet.alpha_composite(av, (int(26 * u), int(100 * u + oy)))
        d.text((88 * u, 108 * u + oy), 'you', font=font('uib', 19 * u), fill=white[:3] + (a8,), anchor='lm')
        d.text((88 * u + font('uib', 19 * u).getlength('you ') + 4 * u, 108 * u + oy), 'now', font=font('uim', 18 * u), fill=grey[:3] + (a8,), anchor='lm')
        d.text((86 * u, 128 * u + oy), word, font=font('uib', 50 * u), fill=white[:3] + (a8,))
        d.text((88 * u, 196 * u + oy), 'Reply', font=font('uim', 17 * u), fill=grey[:3] + (a8,), anchor='lm')
        hk = ease_back((c.lt - t_heart) / 0.3)
        if hk > 0:
            hh = heart(30 * u * hk, (239, 68, 68)); sheet.alpha_composite(hh, (int(sw - 46 * u - hh.width / 2), int(130 * u - hh.height / 2)))
        rk = ease_out((c.lt - t_rep) / 0.25)
        if rk > 0:
            ra = int(255 * clamp(rk * 1.5)); ry = 226 * u + (1 - rk) * 16 * u; rx = 88 * u
            fc = face_chip(c, e, 34 * u); fc.putalpha(fc.split()[3].point(lambda v: v * ra // 255)); sheet.alpha_composite(fc, (int(rx), int(ry)))
            d.text((rx + 46 * u, ry + 8 * u), handle, font=font('uib', 18 * u), fill=white[:3] + (ra,), anchor='lm')
            d.text((rx + 46 * u + font('uib', 18 * u).getlength(handle) + 10 * u, ry + 8 * u), 'Author', font=font('uim', 16 * u), fill=grey[:3] + (ra,), anchor='lm')
            d.text((rx + 46 * u, ry + 36 * u), reply, font=font('uim', 22 * u), fill=white[:3] + (ra,), anchor='lm')
            gift = emoji('🎁', 24 * u)
            if gift is not None:
                g2 = gift.copy(); g2.putalpha(g2.split()[3].point(lambda v: v * ra // 255))
                sheet.alpha_composite(g2, (int(rx + 52 * u + font('uim', 22 * u).getlength(reply)), int(ry + 36 * u - g2.height / 2)))
            ck = ease_back((c.lt - t_rep - 0.12) / 0.3)
            if ck > 0:
                ct = text_img(chip, 19 * u, 'uib', (26, 26, 46)); lk = emoji('🔗', 20 * u)
                cw_ = ct.width + (lk.width + 4 * u if lk is not None else 0) + 10 * u
                cp = rrect(cw_, ct.height * 0.9, ct.height * 0.45, (245, 158, 11, 255))
                x0 = 6 * u
                if lk is not None: cp.alpha_composite(lk, (int(x0 + 4 * u), int((cp.height - lk.height) / 2))); x0 += lk.width + 4 * u
                cp.alpha_composite(ct, (int(x0), int((cp.height - ct.height) / 2)))
                cp = cp.resize((max(1, int(cp.width * (0.6 + 0.4 * ck))), max(1, int(cp.height * (0.6 + 0.4 * ck)))))
                sheet.alpha_composite(cp, (int(rx + 46 * u), int(ry + 56 * u)))
    ey = sh - 140 * u
    chars = ['❤️', '🙌', '🔥', '👏', '😢', '😍', '😮', '😂']
    for j, ch in enumerate(chars):
        im = emoji(ch, 36 * u)
        if im is not None: sheet.alpha_composite(im, (int(36 * u + j * (sw - 72 * u - 36 * u) / 7), int(ey)))
    iy = sh - 78 * u
    sheet.alpha_composite(avatar(48 * u), (int(22 * u), int(iy)))
    d.rounded_rectangle([82 * u, iy, sw - 22 * u, iy + 48 * u], 24 * u, fill=(26, 26, 46, 255))
    typed = word[:int(clamp((c.lt - 0.3) / (0.06 * len(word))) * len(word) + 1e-3)] if c.lt < t_post else ''
    if typed:
        d.text((104 * u, iy + 24 * u), typed, font=font('uib', 26 * u), fill=white, anchor='lm')
        if int(c.lt * 4) % 2: d.rectangle([104 * u + font('uib', 26 * u).getlength(typed) + 3 * u, iy + 10 * u, 106 * u + font('uib', 26 * u).getlength(typed) + 3 * u, iy + 38 * u], fill=(124, 58, 237, 255))
    else:
        d.text((104 * u, iy + 24 * u), f'Add a comment for {handle}', font=font('uim', 20 * u), fill=grey, anchor='lm')
    pressed = t_post - 0.08 <= c.lt < t_post
    d.text((sw - 44 * u, iy + 24 * u), 'Post', font=font('uib', 23 * u), fill=(blue if typed else (124, 58, 237, 255)) if not pressed else (167, 139, 250, 255), anchor='rm')
    sheet = shadowed(sheet, 22, 10, 120)
    cx, cy, s, slot = clear_spot(c, e, sheet.width, sheet.height, ('above', 'side', 'below'), 0.7)
    cy += 3 * u * math.sin(c.lt * 3.2)
    place(c, sheet, cx, cy, s * (0.85 + 0.15 * ease_back(c.lt / 0.3)), 1.2, al * clamp(c.lt / 0.1), behind=slot == 'above', guard=slot != 'above')


@effect('comment-box', 'an Instagram comments sheet above your head types your word, posts it, gets a heart and your reply')
def fx_comment_box(c, e):
    (comment_bar if e.o.get('look') == 'bar' else comment_sheet)(c, e)


# ---------- pack 3: showcase effects (added 23 Oct 2026) ----------
def num_parts(s):
    """'197K' -> (197.0, 'K', 0 decimals); '59%' -> (59.0, '%', 0); '4.8' -> (4.8, '', 1)."""
    s = str(s).strip(); i = len(s)
    while i and not (s[i - 1].isdigit()): i -= 1
    n = s[:i].replace(',', '') or '0'
    return float(n), s[i:], (len(n.split('.')[1]) if '.' in n else 0)


@effect('liquid-glass-graph', 'a liquid glass card floats under your chin while a graph climbs and the number counts up')
def fx_liquid_glass_graph(c, e):
    if e.o.get('look') == 'bento': return glass_bento(c, e)
    q = ease_out(c.lt / 0.4); al = fade(c, e) * clamp(c.lt / 0.12)
    if al <= 0: return
    W = c.W; B = min(W, c.H); cw, ch = B * 0.74, B * 0.46; sc = 0.88 + 0.12 * q
    cx, cy, s, _ = clear_spot(c, e, cw, ch, ('below', 'side'), 0.8); cw, ch = int(cw * s), int(ch * s); cy += (1 - q) * B * 0.08
    gw, gh = int(cw * sc), int(ch * sc)
    im = glass(c, gw, gh, gh * 0.12, cx, cy, amt=0.16, blur=max(10, W // 30), dark=0.12)
    hi = cached(e, ('hi', gw, gh), lambda: Image.fromarray(np.dstack([np.full((gh, gw, 3), 255, np.uint8),
        (np.clip(1 - np.linspace(0, 1, gh) * 2.2, 0, 1)[:, None] * np.ones(gw) * 46).astype(np.uint8)]), 'RGBA'))
    hm = Image.new('L', (gw, gh), 0); ImageDraw.Draw(hm).rounded_rectangle([0, 0, gw - 1, gh - 1], int(gh * 0.12), fill=255)
    hl = hi.copy(); hl.putalpha(Image.fromarray(np.minimum(np.asarray(hi)[..., 3], np.asarray(hm)))); im.alpha_composite(hl)
    lay = Image.new('RGBA', (gw, gh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); pad = gw * 0.07
    g = ease_inout((c.lt - 0.25) / max(0.3, e.d * 0.72))
    lab = e.o.get('text', 'RETENTION').upper()
    d.text((pad, pad * 0.9), lab, font=font('mono', gw * 0.04), fill=(255, 255, 255, 190))
    a, _, _ = num_parts(e.o.get('from', '0')); b, suf, dp = num_parts(e.o.get('to', '59%'))
    v = a + (b - a) * g; s = f'{v:.{dp}f}{suf}'
    f = font('uib', gw * 0.12); d.text((gw - pad - f.getlength(s), pad * 0.55), s, font=f, fill=(255, 255, 255, 255))
    x0, x1, y0, y1 = pad, gw - pad, gh - pad * 0.9, gh * 0.36
    def ycurve(u): return y0 - (y0 - y1) * (u ** 1.5) + math.sin(u * 13) * gh * 0.018 * (1 - u)
    n = 60; pts = [(x0 + (x1 - x0) * j / n, ycurve(j / n)) for j in range(int(n * g) + 1)]
    green = rgb(e.o.get('color'), (16, 185, 129))
    if len(pts) > 1:
        area = Image.new('RGBA', (gw, gh), (0, 0, 0, 0))
        ImageDraw.Draw(area).polygon(pts + [(pts[-1][0], y0), (x0, y0)], fill=green + (55,)); lay.alpha_composite(area)
        glow = Image.new('RGBA', (gw, gh), (0, 0, 0, 0)); lw = max(4, int(gw * 0.011))
        ImageDraw.Draw(glow).line(pts, fill=green + (255,), width=lw * 3, joint='curve')
        lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(lw * 2)))
        ImageDraw.Draw(lay).line(pts, fill=green + (255,), width=lw, joint='curve')
        hx, hy = pts[-1]; r = lw * 1.9
        ImageDraw.Draw(lay).ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255, 255), outline=green + (255,), width=max(2, lw // 2))
    for j in range(1, 4):
        yy = y0 - (y0 - y1) * j / 3.4
        d.line([(x0, yy), (x1, yy)], fill=(255, 255, 255, 40), width=max(1, int(gw * 0.002)))
    im.alpha_composite(lay)
    place(c, shadowed(im, max(10, W // 70), W // 90, 90), cx, cy, alpha=al, guard=True)


@effect('carousel-spin', 'your reels spin around you in a 3D carousel, then slow to a stop')
def fx_carousel_spin(c, e):
    K = int(e.o.get('count', max(6, min(12, len(e.cards))))); cw = int(c.U * float(e.o.get('size', 0.3)))
    def mk():
        out = []
        for i, im in enumerate(e.cards):
            f = card(vary(im, i) if e.o.get('images') is None else im, cw)
            dk = f.copy(); a = np.asarray(dk).copy(); a[..., :3] = (a[..., :3] * 0.55).astype(np.uint8); out.append((f, Image.fromarray(a, 'RGBA')))
        return out
    cards = cached(e, 'cards', mk)
    k = ramp(c, e, 0.3, 0.25); xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.55)) ** 2 + ((yy - (c.fy + c.H * 0.15)) / (c.H * 0.5)) ** 2
    dim = 1 - k * 0.5 * np.clip(d, 0, 1) - k * 0.12
    c.img *= (dim * (1 - c.m) + c.m)[..., None]
    p = clamp(c.lt / e.d); spin = float(e.o.get('turns', 1.1)) * 2 * math.pi * (1 - (1 - p) ** 2.4)
    intro, out = ease_out(c.lt / 0.45), fade(c, e, 0.25)
    R, ry = c.W * 0.56 * intro, c.H * 0.07
    cy = min(c.fy + c.fw * 1.8, c.H * 0.98 - cw * 0.95)  # keep the front covers on screen
    items = sorted((math.cos(i * 2 * math.pi / K + spin), i * 2 * math.pi / K + spin, i) for i in range(K))
    for depth, th, i in items:
        n = len(cards); f, dk = cards[(i * (3 if n % 3 else 2)) % n]; src = f if depth >= 0 else dk  # spread similar covers apart
        sx = max(0.06, abs(math.cos(th)) ** 0.6)
        s = (0.72 + 0.34 * (depth + 1) / 2) * (0.5 + 0.5 * intro)
        w2, h2 = max(2, int(src.width * s * sx)), max(2, int(src.height * s))
        place(c, src.resize((w2, h2), Image.BILINEAR), c.fx + R * math.sin(th), cy + ry * depth, 1.0, 0,
              out * clamp(c.lt / 0.12) * (0.85 + 0.15 * depth), behind=depth < 0, guard=depth >= 0)


MATCH_TXT = ('one clip went in and every cut came back before lunch while editors once spent whole weeks rebuilding the same '
             'timeline by hand early users called it unsettling then impossible to ignore the dead air was gone the captions '
             'matched and the colour finally looked like the room it was shot in nobody opened an editing app all week').split()


def match_page(c, e, j, wx, wy):
    """One article page, with the key word in a red box locked at (wx, wy)."""
    W, H = c.W, c.H; rnd = random.Random(31 + j)
    paper = [(250, 250, 250), (243, 240, 255), (250, 250, 250), (250, 250, 250), (250, 250, 250), (243, 240, 255)][j % 6]
    kind = ['serif', 'mont', 'ui', 'serif', 'anton', 'monts'][j % 6]
    size = W * [0.085, 0.07, 0.072, 0.095, 0.08, 0.068][j % 6]; f = font(kind, size); lh = size * 1.22
    word = e.o.get('text', 'Claude'); red = rgb(e.o.get('color'), (124, 58, 237))
    im = Image.new('RGB', (W, H), paper); d = ImageDraw.Draw(im); ink = (26, 26, 46)
    base = f.getbbox('Ag'); asc = -base[1]
    ww = f.getlength(word); bx0 = wx - ww / 2
    def run(x, y, direction):
        while (x < W + size if direction > 0 else x > -size * 6):
            w_ = rnd.choice(MATCH_TXT) + ' '
            if direction < 0: x -= f.getlength(w_)
            d.text((x, y), w_, font=f, fill=ink)
            if direction > 0: x += f.getlength(w_)
    off = rnd.uniform(0, size * 3)
    ys = wy - asc - lh * math.ceil((wy - asc) / lh + 1)
    y = ys
    while y < H + lh:
        if abs(y - (wy - asc)) < 1: pass
        else: run(-off - rnd.uniform(0, size * 4), y, 1)
        y += lh
    ky = wy - asc
    d.rectangle([0, ky - lh * 0.1, W, ky + lh * 0.95], fill=paper)
    run(bx0 - size * 0.45, ky, -1); run(bx0 + ww + size * 0.45, ky, 1)
    a = np.asarray(im, np.float32) / 255
    bl = cv2.GaussianBlur(a, (0, 0), W * 0.006)
    yy, xx = np.ogrid[0:H, 0:W]
    dd = np.clip((((xx - wx) / (W * 0.62)) ** 2 + ((yy - wy) / (H * 0.32)) ** 2) - 0.15, 0, 1)[..., None]
    a = a * (1 - dd) + bl * dd
    a *= (1 - 0.18 * np.clip(dd * 1.4, 0, 1))
    pg = Image.fromarray((a * 255).astype(np.uint8)).convert('RGBA')
    bf = font(kind, size); bb = bf.getbbox(word); padx, pady = size * 0.22, size * 0.12
    box = rrect(ww + 2 * padx, (bb[3] - bb[1]) + 2 * pady + size * 0.08, size * 0.08, red + (255,))
    ImageDraw.Draw(box).text((padx, pady - bb[1]), word, font=bf, fill=(255, 255, 255, 255))
    pg.alpha_composite(box, (int(bx0 - padx), int(wy - asc + bb[1] - pady)))
    return np.asarray(pg.convert('RGB'), np.uint8)


@effect('match-cut', 'news pages cut on one word, locked in place behind your head')
def fx_match_cut(c, e):
    k = clamp(c.lt / 0.06) * fade(c, e, 0.12)
    face_cam(c, 1 + 0.06 * ease_out(c.lt / e.d), 0.44)
    wx, wy = cached(e, 'anchor', lambda: (c.W / 2, max(c.H * 0.1, c.fy - c.fw * 1.55)))
    durs = [0.15, 0.15, 0.17, 0.19, 0.22, 0.26, 0.3, 0.45]; t, j = c.lt, 0
    while j < len(durs) - 1 and t > durs[j]: t -= durs[j]; j += 1
    pg = cached(e, ('pg', j), lambda: match_page(c, e, j, wx, wy)).astype(np.float32) / 255
    m = c.m[..., None]
    c.img = c.img * (1 - k) + (pg * (1 - m) + c.img * m) * k


@effect('apple-toggles', 'an iPhone settings card under your chin flips its switches on, one line at a time')
def fx_apple_toggles(c, e):
    rows = e.o.get('text', 'One clip|Type /effects|Zero editing apps').split('|')
    W = c.W; cw = int(W * 0.72); rh = int(W * 0.125); ch = rh * len(rows); r = int(W * 0.055)
    order = ('below',) if e.o.get('pos') == 'below' else ('above', 'side', 'below')
    slot = clear_spot(c, e, cw, ch, order, 0.75)[3]
    if slot == 'above': face_cam(c, 1 + (float(e.o.get('zoom', 1.12)) - 1) * ease_out(c.lt / 0.5), 0.56)
    tw, th = int(W * 0.135), int(W * 0.08); tx = cw - int(W * 0.05) - tw
    def base():
        im = rrect(cw, ch, r, (255, 255, 255, 250)); d = ImageDraw.Draw(im)
        f = font('ui', W * 0.05)
        for i, s in enumerate(rows):
            d.text((W * 0.05, i * rh + rh / 2), s, font=f, fill=(26, 26, 46, 255), anchor='lm')
            if i: d.line([(W * 0.05, i * rh), (cw, i * rh)], fill=(243, 240, 255, 255), width=max(2, W // 900))
        pad = max(10, W // 60) * 2 + W // 90
        return shadowed(im, max(10, W // 60), W // 90, 110), pad
    sh, pad = cached(e, 'base', base)
    ts = [float(x) for x in e.o['ticks'].split('|')] if e.o.get('ticks') else [0.45 + 0.34 * i for i in range(len(rows))]
    im = sh.copy(); d = ImageDraw.Draw(im)
    off, on = np.float32((250, 250, 250)), np.float32(rgb(e.o.get('color'), (16, 185, 129)))
    for i in range(len(rows)):
        u = ease_out((c.lt - ts[i]) / 0.2) if i < len(ts) else 0.0
        col = tuple(int(v) for v in off * (1 - u) + on * u) + (255,)
        x0, y0 = pad + tx, pad + i * rh + (rh - th) / 2
        d.rounded_rectangle([x0, y0, x0 + tw, y0 + th], th // 2, fill=col)
        kr = th / 2 - W * 0.006; kx = x0 + th / 2 + (tw - th) * u; ky = y0 + th / 2
        d.ellipse([kx - kr, ky - kr + W * 0.002, kx + kr, ky + kr + W * 0.004], fill=(0, 0, 0, 40))
        d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=(255, 255, 255, 255))
    q = pop(c, 0.0, 0.38); al = fade(c, e) * clamp(c.lt / 0.1)
    cx, cy, s, slot = clear_spot(c, e, cw, ch, order, 0.75)
    if slot != 'above':
        place(c, im, cx, cy, s * (0.6 + 0.4 * q), 0, al, guard=True); return
    # above you, tucked behind your head: your hair overlaps only the bottom edge
    cy = max(min(c.W, c.H) * 0.035 + ch / 2, c.fy - c.fw * 0.95 + c.fw * float(e.o.get('overlap', 0.08)) - ch / 2)
    place(c, im, cx, cy + (1 - q) * c.W * 0.04, 0.6 + 0.4 * q, 0, al, behind=True)


@effect('led-sign', 'the lights drop and a glowing LED sign types itself out behind you')
def fx_led_sign(c, e):
    k = ramp(c, e, 0.2, 0.2)
    face_cam(c, 1 + (float(e.o.get('push', 1.08)) - 1) * ease_inout(c.lt / e.d), 0.42)
    lines = e.o.get('text', 'CLAUDE').upper().split('|'); col = np.float32(rgb(e.o.get('color'), (124, 58, 237))) / 255
    def setup():
        mats = []
        for s in lines:
            f = font('uib', 40); w = int(f.getlength(s)) + 8
            im = Image.new('L', (w, 56), 0); ImageDraw.Draw(im).text((4, 2), s, font=f, fill=255)
            bb = im.getbbox() or (0, 0, w, 56); im = im.crop(bb)
            rows = 11; cols = max(1, round(im.width / im.height * rows))
            mats.append(np.asarray(im.resize((cols, rows), Image.BOX), np.float32) / 255 > 0.42)
        cols = max(m.shape[1] for m in mats) + 2
        cell = int(min(c.W * 0.96 / cols, c.H * 0.3 / (len(mats) * 12)))
        L = np.zeros((len(mats) * 12 - 1, cols), np.float32)
        for i, m in enumerate(mats): o = (cols - m.shape[1]) // 2; L[i * 12:i * 12 + 11, o:o + m.shape[1]] = m
        yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32); rr = np.hypot(xx - cell / 2 + 0.5, yy - cell / 2 + 0.5)
        dot = np.clip(cell * 0.36 - rr + 0.5, 0, 1)
        return L, cell, dot, np.random.default_rng(3).random(L.shape).astype(np.float32)
    L, cell, dot, rnd = cached(e, 'm', setup)
    rows, cols = L.shape
    sweep = clamp((c.lt - 0.15) / 0.75) * (cols + 4)
    lit = L * np.clip((sweep - np.arange(cols)[None, :]) / 3, 0, 1)
    flick = 0.82 + 0.18 * np.sin(rnd * 50 + c.lt * 30)
    b = np.maximum(lit * flick, 0.09)
    pan = np.kron(b, dot)[..., None] * col
    glow = cv2.GaussianBlur(pan, (0, 0), cell * 0.9)
    pan = np.clip(pan + glow * 1.6, 0, 1)
    ph, pw = pan.shape[:2]; x0 = int(c.W / 2 - pw / 2)
    y0 = int(max(c.H * 0.03, c.fy - c.fw * 0.75 - ph))
    xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.6)) ** 2 + ((yy - (c.fy + c.H * 0.25)) / (c.H * 0.55)) ** 2
    bright = 1 - k * (0.84 - 0.3 * np.clip(1 - d, 0, 1))
    c.img *= (bright * (1 - c.m) + c.m * (1 - 0.18 * k))[..., None]
    xa, xb = max(0, x0), min(c.W, x0 + pw); ya, yb = max(0, y0), min(c.H, y0 + ph)
    if xb > xa and yb > ya:
        sub = pan[ya - y0:yb - y0, xa - x0:xb - x0] * k * (1 - c.m[ya:yb, xa:xb, None])
        c.img[ya:yb, xa:xb] = np.clip(c.img[ya:yb, xa:xb] + sub, 0, 1)


@effect('slow-push', 'a slow cinematic push-in from the wide shot to your face, the room melting out of focus')
def fx_slow_push(c, e):
    p = ease_inout(c.lt / e.d)
    face_cam(c, 1 + (float(e.o.get('zoom', 1.6)) - 1) * p, 0.4)
    s = c.W * float(e.o.get('blur', 0.006)) * p
    if s > 0.6:
        bl = cv2.GaussianBlur(c.img, (0, 0), s); m = c.m[..., None]
        c.img = c.img * m + bl * (1 - m)
    vignette(c, 0.25 * p)


# ---------- pack 3 looks: sparkle spotlight, editorial cover, glass bento (added 23 Oct 2026) ----------
def star(size, color=(243, 240, 255)):
    """A 4-point sparkle with a soft glow."""
    s = max(8, int(size)); h = s / 2; t = s * 0.075
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(h, s * 0.02), (h + t, h - t), (s * 0.98, h), (h + t, h + t), (h, s * 0.98), (h - t, h + t), (s * 0.02, h), (h - t, h - t)], fill=tuple(color) + (255,))
    g = im.filter(ImageFilter.GaussianBlur(s * 0.07)); out = Image.alpha_composite(g, g); out.alpha_composite(im)
    r = s * 0.07; ImageDraw.Draw(out).ellipse([h - r, h - r, h + r, h + r], fill=(255, 255, 255, 255))
    return out


def gradient_text(s, size, kind, top, bot, glow=None):
    """Text filled with a vertical colour gradient (gold, chrome...), with an optional glow."""
    f = font(kind, size); bb = f.getbbox(s); pad = int(size * 0.25 + (glow[1] * 2.5 if glow else 0))
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), s, font=f, fill=255)
    g = np.linspace(0, 1, h)[:, None, None]; col = np.float32(top) * (1 - g) + np.float32(bot) * g
    im = Image.fromarray(np.dstack([np.broadcast_to(col, (h, w, 3)).astype(np.uint8), np.asarray(m)]), 'RGBA')
    if glow:
        gl = Image.new('RGBA', (w, h), tuple(glow[0]) + (0,)); gl.putalpha(m.filter(ImageFilter.GaussianBlur(glow[1])))
        im = Image.alpha_composite(Image.alpha_composite(gl, gl), im)
    return im


def spotlight_sparkle(c, e):
    k = ramp(c, e, 0.25, 0.2); W, H = c.W, c.H
    face_cam(c, 1 + (float(e.o.get('push', 1.12)) - 1) * ease_inout(c.lt / e.d), 0.46)
    gold = np.float32(rgb(e.o.get('color'), (167, 139, 250))) / 255
    xx, yy = grid(c)
    d = ((xx - c.fx) / (W * 0.55)) ** 2 + ((yy - (c.fy + H * 0.15)) / (H * 0.5)) ** 2
    pool = np.clip(1 - d, 0, 1) ** 1.5
    c.img *= ((1 - k * (0.92 - 0.3 * pool)) * (1 - c.m) + c.m * (1 + 0.06 * k))[..., None]
    ox, oy = c.fx, c.fy - c.fw * 1.1
    q = 4; sy, sx = np.mgrid[0:H // q, 0:W // q].astype(np.float32) * q
    ang = np.arctan2(sy - oy, sx - ox); rad = np.hypot(sx - ox, sy - oy)
    rays = (0.5 + 0.5 * np.cos(16 * ang + c.lt * 0.9)) ** 5 * np.exp(-rad / (H * 0.42)) + 0.9 * np.exp(-(rad / (H * 0.2)) ** 2)
    rays = cv2.resize(rays.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    halo = np.clip(cv2.GaussianBlur(c.m, (0, 0), W * 0.012) * 1.6 - c.m, 0, 1)
    c.img += (rays * 0.32 + halo * 0.7)[..., None] * gold * k * (1 - c.m[..., None])
    word = e.o.get('text', 'CLAUDE')
    def wimg():
        size = int(H * 0.2)
        while size > 20 and font('didonei', size).getlength(word) > W * 0.86: size = int(size * 0.94)
        im = gradient_text(word, size, 'didonei', (250, 250, 250), (167, 139, 250), glow=(tuple(int(v * 255) for v in gold), size * 0.06))
        im = shadowed(im, int(size * 0.05), 0, 200)
        return np.asarray(im, np.float32) / 255
    wa = cached(e, 'w', wimg); wh, ww = wa.shape[:2]
    band = np.exp(-(((np.arange(ww)[None, :] + np.arange(wh)[:, None] * 0.5) - (-0.3 + 1.6 * clamp((c.lt - 0.25) / 0.9)) * ww * 1.3) / (ww * 0.07)) ** 2)
    w2 = wa.copy(); w2[..., :3] = np.clip(w2[..., :3] + band[..., None] * 0.9, 0, 1)
    s = 1.08 - 0.08 * ease_out(c.lt / 0.5)
    im = Image.fromarray((w2 * 255).astype(np.uint8), 'RGBA')
    place(c, im, W / 2, max(wh * 0.5 + H * 0.06, c.fy - c.fw * 1.05 - wh * 0.28), s, 0, k, behind=True)
    def spots():
        rnd = random.Random(9)
        return [(rnd.uniform(0.04, 0.96), rnd.uniform(0.07, 0.62), rnd.uniform(0.025, 0.07), rnd.uniform(0, 6.3), rnd.uniform(5, 9), rnd.random() < 0.35) for _ in range(48)]
    spr = cached(e, 'star', lambda: star(W * 0.07))
    for x, y, sz, ph, sp, front in cached(e, 'sp', spots):
        a = max(0.0, math.sin(ph + c.lt * sp)) ** 2 * k
        if a < 0.03: continue
        sc = sz / 0.07 * (0.45 + 0.75 * a)
        place(c, spr, x * W, y * H, sc, c.lt * 40 + ph * 30, a, behind=not front, guard=front)


def cover_editorial(c, e):
    k = ease_out(c.lt / 0.35); al = fade(c, e); W, H = c.W, c.H
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    soft = (c.img * 0.82 + lum * 0.18) * 0.9 + np.float32((243, 240, 255)) / 255 * 0.1
    q = 4; bl = cv2.resize(np.clip(c.img[::q, ::q] - 0.62, 0, 1), (W, H), interpolation=cv2.INTER_LINEAR)
    bloom = cv2.GaussianBlur(bl, (0, 0), W * 0.012)
    c.img = c.img * (1 - k) + np.clip(soft + bloom * 0.55, 0, 1) * k
    ink, rose = rgb(e.o.get('color'), (26, 26, 46)), rgb(e.o.get('accent'), (124, 58, 237))
    cream = (250, 250, 250)
    title = e.o.get('text', 'EFFECTS').upper()
    def mast():
        size = int(H * 0.16)
        while size > 20 and font('didoneb', size).getlength(title) + size * 0.04 * len(title) > W * 0.92: size = int(size * 0.95)
        return tracked(title, size, 'didoneb', ink, size * 0.04)
    m = cached(e, 'm', mast)
    s = 1.05 - 0.05 * ease_out(c.lt / 0.5)
    place(c, m, W / 2, H * 0.085 + m.height / 2, s, 0, al * k, behind=True)
    iss = cached(e, 'i', lambda: tracked(e.o.get('issue', 'THE ONE-CLIP ISSUE  ·  NO. 42  ·  OCTOBER 2026'), int(W * 0.022), 'ui', ink, W * 0.006))
    place(c, iss, W / 2, H * 0.075, alpha=al * k, behind=True)
    rule = cached(e, 'r', lambda: rrect(W * 0.86, max(3, W // 600), 1, ink + (255,)))
    place(c, rule, W / 2, H * 0.087 + m.height, alpha=al * k * 0.8, behind=True)
    lines = e.o.get('lines', 'One clip,|42 looks.|NO EDITOR  ·  NO APPS').split('|')
    styles = [('didonei', 0.085, ink), ('didoneb', 0.105, rose), ('ui', 0.03, ink)]
    y = H * float(e.o.get('lines_y', 0.575))
    for j, ln in enumerate(lines):
        kind, sz, col = styles[min(j, 2)]
        im = cached(e, ('l', j), lambda: (tracked(ln, int(W * sz), kind, col, W * 0.006) if kind == 'ui' else text_img(ln, W * sz, kind, col, glow=(cream, W * 0.012))))
        kj = ease_out((c.lt - 0.2 - 0.1 * j) / 0.35)
        comp(c, im, W * 0.05 - (1 - kj) * W * 0.03, y, al * kj); y += im.height * (0.82 if kind != 'ui' else 1.6)
    right = e.o.get('right', 'the art of the|effortless edit').split('|')
    y = H * float(e.o.get('right_y', 0.715))
    for j, ln in enumerate(right):
        im = cached(e, ('r', j), lambda: text_img(ln, W * 0.058, 'didonei', ink, glow=(cream, W * 0.01)))
        kj = ease_out((c.lt - 0.45 - 0.1 * j) / 0.35)
        comp(c, im, W * 0.95 - im.width + (1 - kj) * W * 0.03, y, al * kj); y += im.height * 0.78


def donut(size, pct, col, label, value):
    S = int(size) * 2; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = int(S * 0.1); pad = int(S * 0.08)
    d.arc([pad, pad, S - pad, S - pad], 0, 360, fill=(255, 255, 255, 46), width=w)
    if pct > 0.002: d.arc([pad, pad, S - pad, S - pad], -90, -90 + 360 * pct, fill=tuple(col) + (255,), width=w)
    f = font('uib', S * 0.2); d.text((S / 2, S / 2 - S * 0.02), value, font=f, fill=(255, 255, 255, 255), anchor='mm')
    f2 = font('mono', S * 0.065); d.text((S / 2, S / 2 + S * 0.15), label.upper(), font=f2, fill=(255, 255, 255, 170), anchor='mm')
    return im.resize((int(size), int(size)), Image.LANCZOS)


def glass_bento(c, e):
    W, H = c.W, c.H; al = fade(c, e) * clamp(c.lt / 0.12)
    if al <= 0: return
    green = rgb(e.o.get('color'), (16, 185, 129)); peach = (167, 139, 250)
    # 1. the big graph, on a smoked glass screen behind you
    q = ease_out(c.lt / 0.4); pw, ph = int(W * 0.9), int(H * 0.3); pcx, pcy = W / 2, H * 0.08 + ph / 2 + (1 - q) * H * 0.02
    pan = glass(c, pw, ph, W * 0.04, pcx, pcy, amt=0.06, dark=0.62, blur=max(10, W // 30))
    lay = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); pad = pw * 0.05
    g = ease_inout((c.lt - 0.2) / max(0.3, e.d * 0.75))
    d.text((pad, pad * 0.8), e.o.get('text', 'VIEWS').upper(), font=font('mono', pw * 0.026), fill=(255, 255, 255, 180))
    a, _, _ = num_parts(e.o.get('from', '0')); b, suf, dp = num_parts(e.o.get('to', '197K')); s = f'{a + (b - a) * g:.{dp}f}{suf}'
    f = font('uib', pw * 0.085); d.text((pw - pad - f.getlength(s), pad * 0.45), s, font=f, fill=(255, 255, 255, 255))
    x0, x1, y0, y1 = pad, pw - pad, ph - pad * 0.8, ph * 0.3
    for j in range(1, 4): yy = y0 - (y0 - y1) * j / 3.3; d.line([(x0, yy), (x1, yy)], fill=(255, 255, 255, 34), width=max(1, W // 1000))
    n = 80; pts = [(x0 + (x1 - x0) * j / n, y0 - (y0 - y1) * ((j / n) ** 1.7) + math.sin(j / n * 17) * ph * 0.02 * (1 - j / n)) for j in range(int(n * g) + 1)]
    if len(pts) > 1:
        area = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); ImageDraw.Draw(area).polygon(pts + [(pts[-1][0], y0), (x0, y0)], fill=green + (60,)); lay.alpha_composite(area)
        lw = max(4, int(pw * 0.006)); gl = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); ImageDraw.Draw(gl).line(pts, fill=green + (255,), width=lw * 3, joint='curve')
        lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(lw * 2))); ImageDraw.Draw(lay).line(pts, fill=green + (255,), width=lw, joint='curve')
        hx, hy = pts[-1]; r = lw * 2; ImageDraw.Draw(lay).ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255, 255), outline=green + (255,), width=lw // 2)
    pan.alpha_composite(lay)
    place(c, pan, pcx, pcy, alpha=al * q, behind=True)
    # 2. the bento tiles in front of you
    def tile(i, cx, cy, tw, th, draw):
        k = pop(c, 0.15 + 0.12 * i, 0.4)
        if k <= 0: return
        t = glass(c, tw, th, W * 0.035, cx, cy, amt=0.08, dark=0.5, blur=max(10, W // 34))
        draw(t, ImageDraw.Draw(t), tw, th); place(c, shadowed(t, max(8, W // 80), W // 120, 90), cx, cy, 0.7 + 0.3 * k, 0, al * clamp(k * 2))
    dv, dl = (e.o.get('donut', '29%::ERASE share').split('::') + [''])[:2]; pct = num_parts(dv)[0] / 100
    def dr_donut(t, d, tw, th):
        p = ease_out((c.lt - 0.35) / 0.8) * pct
        dn = donut(tw * 0.86, p, peach, dl, f'{round(p * 100)}%'); t.alpha_composite(dn, (int((tw - dn.width) / 2), int((th - dn.height) / 2)))
    kv, kl = (e.o.get('kpi', '672K::views · top 7 reels').split('::') + [''])[:2]
    def dr_kpi(t, d, tw, th):
        b, suf, dp = num_parts(kv); v = b * ease_out((c.lt - 0.45) / 0.8)
        d.text((tw * 0.1, th * 0.18), f'{v:.{dp}f}{suf}', font=font('uib', th * 0.36), fill=(255, 255, 255, 255))
        d.text((tw * 0.1, th * 0.7), kl.upper(), font=font('mono', th * 0.1), fill=(255, 255, 255, 170))
    bv, bl = (e.o.get('bars', '197|140|124|83|50::top reels · K views').split('::') + [''])[:2]; vals = [num_parts(v)[0] for v in bv.split('|')]
    def dr_bars(t, d, tw, th):
        d.text((tw * 0.1, th * 0.06), bl.upper(), font=font('mono', tw * 0.055), fill=(255, 255, 255, 170))
        n = len(vals); bw = tw * 0.8 / n; top, base = th * 0.2, th * 0.88; mx = max(vals)
        for j, v in enumerate(vals):
            kk = ease_out((c.lt - 0.4 - 0.08 * j) / 0.5); hgt = (base - top) * v / mx * kk; x = tw * 0.1 + j * bw
            d.rounded_rectangle([x + bw * 0.14, base - hgt, x + bw * 0.86, base], int(bw * 0.18), fill=(green if j == 0 else (255, 255, 255)) + (255 if j == 0 else 150,))
            if kk > 0.6: d.text((x + bw / 2, base - hgt - tw * 0.02), f'{v:g}', font=font('uib', tw * 0.06), fill=(255, 255, 255, 230), anchor='md')
    tw = W * 0.25; gap = W * 0.02; ty = max(H * 0.5, c.fy + c.fw * 1.1)
    tile(0, W * 0.15, ty + tw * 0.5, tw, tw, dr_donut)
    tile(1, W * 0.15, ty + tw + gap + tw * 0.28, tw, tw * 0.56, dr_kpi)
    tile(2, W * 0.85, ty + tw * 0.65, tw, tw * 1.3, dr_bars)


# ---------- pack 4: over-the-shoulder zoom, messages, place-in-grid (added 27 Oct 2026) ----------
GREEN = (16, 185, 129)


def liquid_glass(c, box, r=None, blur=None):
    """Liquid glass panel on c.img, after liquid-glass-js (MIT, dashersw): rounded-rect SDF, edge + rim refraction
    along the normal, a light blur so the room still shows through, a faint top-to-bottom tint, a specular rim lit
    from the top-left, plus a red/blue fringe at the edge (after React Bits' GlassSurface)."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]; w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8: return
    u = c.W / 2160; r = r or 72 * u; M = int(140 * u)
    X0, Y0, X1, Y1 = max(0, x0 - M), max(0, y0 - M), min(c.W, x1 + M), min(c.H, y1 + M)
    tex = cv2.GaussianBlur(c.img[Y0:Y1, X0:X1], (0, 0), blur or 7 * u)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    q = np.stack([np.abs(xx - w / 2) - (w / 2 - r), np.abs(yy - h / 2) - (h / 2 - r)], -1)
    sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.maximum(q[..., 0], q[..., 1]), 0) - r
    d = np.maximum(-sdf, 0) / u
    nx, ny = xx - w / 2, yy - h / 2; nl = np.sqrt(nx * nx + ny * ny) + 1e-3; nx, ny = nx / nl, ny / nl
    k = (70 * np.exp(-d / 14) + 34 * np.exp(-d / 70) + 10 * np.exp(-d / 260)) * u
    out = np.zeros((h, w, 3), np.float32)
    for ch, fr in enumerate((1.10, 1.0, 0.90)):
        mx = (xx + x0 - X0 + nx * k * fr).astype(np.float32); my = (yy + y0 - Y0 + ny * k * fr).astype(np.float32)
        out[..., ch] = cv2.remap(tex[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * 0.86 + 0.06 * (1.0 - 0.30 * (yy / h))[..., None] - 0.05
    spec = np.exp(-d / 5) * np.clip(0.55 - 0.45 * (nx * 0.6 + ny * 0.8), 0, 1)
    out = np.clip(out + (spec * 0.85 + np.exp(-d / 30) * 0.10)[..., None], 0, 1)
    a = np.clip(0.5 - sdf, 0, 1)[..., None]
    gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(c.W, x1), min(c.H, y1)
    sl = (slice(gy0 - y0, gy1 - y0), slice(gx0 - x0, gx1 - x0))
    dst = c.img[gy0:gy1, gx0:gx1]; dst[:] = dst * (1 - a[sl]) + out[sl] * a[sl]


def split_num(s):
    """'197K' -> (197.0, 'K', 0 decimals); '82%' -> (82.0, '%', 0); '1.2M' -> (1.2, 'M', 1)."""
    import re as _re
    m = _re.match(r'\s*([\d.,]+)\s*(.*)', str(s)); n = m.group(1).replace(',', '') if m else '0'
    return float(n), (m.group(2) if m else ''), (len(n.split('.')[1]) if '.' in n else 0)


def glass_graph(c, cx, cy, k, prog, label, value, kind, scale=1.0):
    """A see-through glass stat card: spaced-caps label, a number that counts up, a glowing line or bar chart."""
    if k <= 0: return
    u = c.U / 2160 * scale; sc = 0.82 + 0.18 * ease_back(k)
    w, h = 1760 * u * sc, 1056 * u * sc; lift = 40 * u * (1 - k); m = min(c.W, c.H) * 0.03
    cx, cy = clamp(cx, m + w / 2, c.W - m - w / 2), clamp(cy, m + h / 2, c.H - m - h / 2)  # whole card on screen
    x0, y0 = cx - w / 2, cy - h / 2 + lift
    liquid_glass(c, (x0, y0, x0 + w, y0 + h))
    v = w / 1500
    lay = Image.new('RGBA', (int(w) + 40, int(h) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); o = 20
    lab, big = font('uim', 44 * v), font('uib', 170 * v)
    num, suf, dec = split_num(value); txt = f'{num * ease_out(prog):.{dec}f}{suf}'
    xx = o + 64 * v
    for chh in label.upper(): d.text((xx, o + 64 * v), chh, font=lab, fill=(255, 255, 255, 235)); xx += lab.getlength(chh) + 9 * v
    d.text((o + w - 70 * v - big.getlength(txt), o + 40 * v), txt, font=big, fill=(255, 255, 255, 255))
    gx0, gx1, gy0, gy1 = o + 64 * v, o + w - 64 * v, o + 290 * v, o + h - 80 * v
    for j in range(3): d.line([gx0, gy0 + (gy1 - gy0) * j / 2, gx1, gy0 + (gy1 - gy0) * j / 2], fill=(255, 255, 255, 70), width=max(1, int(3 * v)))
    halo = Image.new('RGBA', lay.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(halo)
    xx = o + 64 * v
    for chh in label.upper(): hd.text((xx, o + 64 * v), chh, font=lab, fill=(0, 0, 0, 150)); xx += lab.getlength(chh) + 9 * v
    hd.text((o + w - 70 * v - big.getlength(txt), o + 40 * v), txt, font=big, fill=(0, 0, 0, 150))
    base = halo.filter(ImageFilter.GaussianBlur(10 * v))
    chart = Image.new('RGBA', lay.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(chart)
    if kind == 'line':
        ys = [0.04, 0.07, 0.10, 0.16, 0.22, 0.35, 0.52, 0.74, 1.0]; n = max(0.02, (len(ys) - 1) * ease_out(prog)); pts = []
        for i in range(int(n) + 1):
            t = min(i, n); i0 = min(int(t), len(ys) - 2); f = t - i0; yv = ys[i0] + (ys[i0 + 1] - ys[i0]) * f
            pts.append((gx0 + (gx1 - gx0) * t / (len(ys) - 1), gy1 - (gy1 - gy0) * yv))
        if len(pts) > 1:
            cd.polygon(pts + [(pts[-1][0], gy1), (pts[0][0], gy1)], fill=GREEN + (70,))
            gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).line(pts, fill=GREEN + (255,), width=int(60 * v), joint='curve')
            chart.alpha_composite(gl.filter(ImageFilter.GaussianBlur(26 * v)))
            cd = ImageDraw.Draw(chart); cd.line(pts, fill=GREEN + (255,), width=max(2, int(20 * v)), joint='curve')
            ex, ey = pts[-1]
            cd.ellipse([ex - 30 * v, ey - 30 * v, ex + 30 * v, ey + 30 * v], fill=GREEN + (90,)); cd.ellipse([ex - 15 * v, ey - 15 * v, ex + 15 * v, ey + 15 * v], fill=(243, 240, 255, 255))
    else:
        vals = [1.0, 0.71, 0.63, 0.42, 0.25, 0.20, 0.19]; bw = (gx1 - gx0) / len(vals)
        for i, val in enumerate(vals):
            g = ease_out(clamp(prog * 1.6 - i * 0.1)); top = gy1 - (gy1 - gy0) * val * g; bx = gx0 + i * bw + bw * 0.16
            if i == 0:
                gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle([bx, top, bx + bw * 0.68, gy1], int(18 * v), fill=GREEN + (230,))
                chart.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22 * v))); cd = ImageDraw.Draw(chart)
            cd.rounded_rectangle([bx, top, bx + bw * 0.68, gy1], int(18 * v), fill=GREEN + (230 if i == 0 else 120,))
    base.alpha_composite(chart); base.alpha_composite(lay)
    comp(c, base, x0 - o, y0 - o)


@effect('over-the-shoulder-zoom', 'the camera pushes into one top corner, a liquid glass graph pops beside your head, then the other corner with a second graph')
def fx_over_the_shoulder_zoom(c, e):
    p = clamp(c.lt / e.d); z0 = float(e.o.get('zoom', 2.0))
    lx, rx = c.fx - c.W * 0.17, c.fx + c.W * 0.19
    keys = [(0, 1.0, c.fx, c.fy), (0.30, 1.04, c.fx, c.fy), (0.46, z0, lx, c.fy), (0.66, z0 + 0.04, lx, c.fy), (0.76, 1.05, c.fx, c.fy), (0.87, z0, rx, c.fy), (1.0, z0 + 0.04, rx, c.fy)]
    for (pa, za, xa, ya), (pb, zb, xb, yb) in zip(keys, keys[1:]):
        if pa <= p <= pb: q = ease_inout((p - pa) / (pb - pa)); z, x, y = za + (zb - za) * q, xa + (xb - xa) * q, ya + (yb - ya) * q; break
    camera(c, z, x, y)
    k1 = clamp((p - 0.42) / 0.065) * (1 - clamp((p - 0.66) / 0.055)); k2 = clamp((p - 0.84) / 0.065)
    if k1 <= 0 and k2 <= 0: return
    me, m = c.img.copy(), c.m[..., None]
    a, b = (e.o.get('text') or 'Views · this reel|Top reels · total').split('|')[:2]
    va, vb = (str(e.o.get('to') or '197K|672K')).split('|')[:2]
    glass_graph(c, c.W * 0.43, c.H * 0.255, k1, clamp((p - 0.45) / 0.17), a, va, 'line')
    glass_graph(c, c.W * 0.57, c.H * 0.255, k2, clamp((p - 0.86) / 0.14), b, vb, 'bars')
    c.img = c.img * (1 - m) + me * m   # your head stays in front of the cards


def msg_bubble(c, y, title, body, a, cx=None, u=None):
    """One creamy glass iMessage notification with a soft white halo, centred at (cx, y)."""
    u = u or c.W / 2160; cx = c.W / 2 if cx is None else cx
    w, h = int(1880 * u), int(330 * u); y0 = int(y - h / 2)
    if a <= 0 or y0 + h < 0 or y0 > c.H: return
    s = 0.82 + 0.18 * ease_back(a); ww, hh = int(w * s), int(h * s); xs, ys = int(cx - ww / 2), int(y - hh / 2)
    halo = Image.new('RGBA', (ww + int(240 * u), hh + int(240 * u)), (0, 0, 0, 0)); p = int(120 * u)
    ImageDraw.Draw(halo).rounded_rectangle([p - 30 * u, p - 30 * u, p + ww + 30 * u, p + hh + 30 * u], int(100 * u), fill=(255, 250, 240, int(215 * clamp(a * 2))))
    comp(c, halo.filter(ImageFilter.GaussianBlur(56 * u)), xs - p, ys - p)
    gx0, gy0, gx1, gy1 = max(0, xs), max(0, ys), min(c.W, xs + ww), min(c.H, ys + hh)
    if gx1 <= gx0 or gy1 <= gy0: return
    reg = cv2.GaussianBlur(c.img[gy0:gy1, gx0:gx1], (0, 0), 20 * u)
    yy = np.linspace(0, 1, gy1 - gy0, dtype=np.float32)[:, None, None]
    reg = reg * (1 - 0.78) + np.float32([243, 240, 255]) / 255 * 0.78 + (1 - yy) * 0.08
    mk = Image.new('L', (ww, hh), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, ww - 1, hh - 1], int(70 * u * s), fill=255)
    mk = np.asarray(mk, np.float32)[gy0 - ys:gy1 - ys, gx0 - xs:gx1 - xs, None] / 255 * clamp(a * 2.5)
    dst = c.img[gy0:gy1, gx0:gx1]; dst[:] = dst * (1 - mk) + np.clip(reg, 0, 1) * mk
    lay = Image.new('RGBA', (ww, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); v = s * u; al = int(255 * clamp(a * 2.5))
    d.rounded_rectangle([1, 1, ww - 2, hh - 2], int(70 * v), outline=(255, 255, 255, int(170 * clamp(a * 2.5))), width=max(1, int(3 * v)))
    ic = np.linspace(0, 1, int(160 * v), dtype=np.float32)[:, None]
    icon = np.dstack([110 - ic * 64, 232 - ic * 51, 120 - ic * 51, np.full_like(ic, 255)]).repeat(int(160 * v), 1).astype(np.uint8)
    icon = Image.fromarray(icon, 'RGBA'); im_ = Image.new('L', icon.size, 0); ImageDraw.Draw(im_).rounded_rectangle([0, 0, icon.width - 1, icon.height - 1], int(40 * v), fill=al); icon.putalpha(im_)
    ImageDraw.Draw(icon).ellipse([30 * v, 34 * v, 130 * v, 114 * v], fill=(255, 255, 255, al)); ImageDraw.Draw(icon).polygon([(44 * v, 102 * v), (36 * v, 130 * v), (72 * v, 110 * v)], fill=(255, 255, 255, al))
    lay.alpha_composite(icon, (int(56 * v), int(70 * v)))
    d.text((262 * v, 76 * v), title, font=font('uib', 72 * v), fill=(28, 28, 30, al)); d.text((262 * v, 170 * v), body, font=font('uim', 76 * v), fill=(44, 44, 46, al))
    comp(c, lay, xs, ys)


@effect('messages', 'iMessage notifications pop in one after another, creamy glass with a soft glow, stacking up above the bottom of the frame')
def fx_messages(c, e):
    msgs = (e.o.get('text') or 'how did you edit this??|wait, which app is this|send me the effects pls|EFFECTS').split('|')
    title = e.o.get('title', 'Messages'); n = len(msgs); u = min(c.W, c.H) / 2160
    gap = min(0.4, e.d * 0.75 / max(1, n)); pops = [0.13 + i * gap for i in range(n)]
    cx, cy, s, _ = clear_spot(c, e, 1880 * u, 365 * u * n, ('side', 'below'), 0.8); u *= s
    bottom = cy + 365 * u * n / 2 + 18 * u; out = fade(c, e, 0.2)
    for k in range(n):
        if c.lt < pops[k]: continue
        newer = sum(ease_out(clamp((c.lt - pops[j]) / 0.17)) for j in range(k + 1, n) if c.lt >= pops[j])
        msg_bubble(c, bottom - 165 * u - newer * 365 * u, title, msgs[k], clamp((c.lt - pops[k]) / 0.17) * out, cx, u)


def views_icon(px):
    """The Instagram 'views' eye: an arc above a teardrop (traced from the IG app)."""
    paths = [[(325, 490), [(-43, -9, -73, -30, -97, -68), (-28, -46, -14, -53, 22, -10), (37, 45, 79, 62, 133, 55), (33, -4, 50, -14, 80, -48), (40, -44, 60, -46, 37, -3), (-29, 52, -112, 87, -175, 74)]],
             [(315, 405), [(-51, -50, -21, -115, 52, -115), (51, 0, 88, 65, 41, 72), (-14, 2, -29, 15, -38, 35), (-8, 18, -19, 33, -23, 33), (-4, 0, -19, -11, -32, -25)]]]
    k = px / 24 * 4; im = Image.new('L', (int(34 * k), int(24 * k)), 0); d = ImageDraw.Draw(im)
    tx = lambda x, y: ((0.1 * x - 19) * k, (80 - 0.1 * y - 29) * k)
    for (sx, sy), segs in paths:
        pts = [tx(sx, sy)]; cx, cy = sx, sy
        for s in segs:
            p0, p1, p2, p3 = (cx, cy), (cx + s[0], cy + s[1]), (cx + s[2], cy + s[3]), (cx + s[4], cy + s[5])
            for j in range(1, 13):
                t = j / 12; pts.append(tx(*[(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * cc + t ** 3 * dd for a, b, cc, dd in zip(p0, p1, p2, p3)]))
            cx, cy = p3
        d.polygon(pts, fill=255)
    im = im.resize((int(34 * px / 24), px), Image.LANCZOS); out = Image.new('RGBA', im.size, (255, 255, 255, 0)); out.putalpha(im); return out


def grid_tile(im, w, h, views, r):
    t = im.convert('RGB'); s = max(w / t.width, h / t.height); t = t.resize((int(t.width * s) + 1, int(t.height * s) + 1), Image.LANCZOS)
    t = t.crop(((t.width - w) // 2, (t.height - h) // 2, (t.width - w) // 2 + w, (t.height - h) // 2 + h)).convert('RGBA')
    mk = Image.new('L', (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    if views:
        u = w / 660; fd = Image.linear_gradient('L').resize((w, int(h * 0.28))).point(lambda v: int(v * 0.75))
        sh = Image.new('RGBA', fd.size, (0, 0, 0, 0)); sh.putalpha(fd); t.alpha_composite(sh, (0, h - fd.height))
        ic = views_icon(int(56 * u)); x, y = int(34 * u), int(h - 92 * u); t.alpha_composite(ic, (x, y + int(2 * u)))
        ImageDraw.Draw(t).text((x + ic.width + 14 * u, y - 6 * u), views, font=font('uib', 58 * u), fill=(255, 255, 255, 255))
    t.putalpha(mk); ImageDraw.Draw(t).rounded_rectangle([1, 1, w - 2, h - 2], r, outline=(255, 255, 255, 150), width=max(1, int(4 * w / 660)))
    return t


@effect('place-in-grid', 'you shrink into the centre tile of your 3x3 profile grid on frosted glass, then 8 of your reels pop in around you, one per frame, view counts on every tile')
def fx_place_in_grid(c, e):
    W, H = c.W, c.H; g, m = int(33 * W / 2160), int(68 * W / 2160)
    tw = (W - 2 * m - 2 * g) // 3; th = int(tw * 16 / 9); top = (H - (3 * th + 2 * g)) // 2; r = int(28 * W / 2160)
    rect = lambda i: (m + (i % 3) * (tw + g), top + (i // 3) * (th + g))
    views = (e.o.get('views') or '2.4M|847K|1.2M|312K|3.4M|596K|268K|1.8M|3.1M').split('|')
    tiles = cached(e, 'tiles', lambda: [grid_tile(vary(im, i) if e.o.get('images') is None else im, tw, th, views[i % len(views)], r) for i, im in enumerate((e.cards * 8)[:8])])
    me = c.img.copy(); p = ease_inout(clamp(c.lt / 0.45))
    fz = cv2.resize(cv2.GaussianBlur(cv2.resize(me, (W // 8, H // 8)), (0, 0), 14), (W, H), interpolation=cv2.INTER_CUBIC)
    lum = (fz @ np.float32([0.299, 0.587, 0.114]))[..., None]; fz = np.clip(lum + (fz - lum) * 1.25, 0, 1)
    c.img = fz * (1 - 0.37) + np.float32([243, 240, 255]) / 255 * 0.37
    for j, slot in enumerate((1, 5, 7, 3, 2, 8, 6, 0)):
        a = clamp((c.lt - 0.47 - j / 30) / 0.1)
        if a > 0: x, y = rect(slot); place(c, tiles[j], x + tw / 2, y + th / 2, 0.82 + 0.18 * ease_back(a), 0, clamp(a * 2))
    cx, cy = rect(4); w2, h2 = int(W + (tw - W) * p), int(H + (th - H) * p)
    mine = Image.fromarray((np.clip(me, 0, 1) * 255).astype(np.uint8))
    tile = grid_tile(mine, w2, h2, views[8 % len(views)] if p > 0.9 else None, int(r * p))
    comp(c, tile, cx * p, cy * p)
    if p > 0.95: d = Image.new('RGBA', (tw + 8, th + 8), (0, 0, 0, 0)); ImageDraw.Draw(d).rounded_rectangle([2, 2, tw + 5, th + 5], r + 2, outline=(124, 58, 237, 255), width=8); comp(c, d, cx - 4, cy - 4)



# Optional private effects (not part of the public pack). If fx_private.py sits next to this file, its effects load too.
_PRIV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fx_private.py')
if os.path.exists(_PRIV): exec(open(_PRIV).read(), globals())


# ---------- pack 5: phrase pops starters (added 2 Nov 2026) ----------
INKY, TAPE, CRAYON, CREAMY = (26, 26, 46), (167, 139, 250), (124, 58, 237), (243, 240, 255)
def above_head(c, h): return max(min(c.W, c.H) * 0.035 + h / 2, c.fy - c.fw * 1.75)


@effect('tape-label', 'a strip of yellow tape with your line lands on your chest')
def fx_tape_label(c, e):
    k = pop(c, 0.05, 0.25) * fade(c, e)
    if k <= 0: return
    def tape():
        S = int(c.W * 0.055); t = text_img(e.o.get('text', 'your own reels'), S, 'hand', INKY)
        w, h = int(t.width + S * 0.6), int(t.height + S * 0.2); o = max(4, S // 9)
        im = Image.new('RGBA', (w + o, h + o), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([o, o, w + o - 1, h + o - 1], fill=(26, 26, 46, 255)); d.rectangle([0, 0, w - 1, h - 1], fill=TAPE + (255,))
        im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2)); return im
    im = cached(e, 'tape', tape)
    place(c, im, c.W / 2, clamp(c.fy + c.fw * 1.6, c.H * 0.45, c.H * 0.68), 0.85 + 0.15 * k, 0, clamp(k * 1.5), guard=True)


@effect('select-resize', 'a blue selection box grabs your number and a cursor drags it bigger')
def fx_select_resize(c, e):
    al = fade(c, e) * clamp(c.lt / 0.08)
    if al <= 0: return
    cx, cy, s, slot = clear_spot(c, e, c.W * 0.5, c.W * 0.26, ('above', 'side'), 0.6, floor=0.6)
    p = ease_inout((c.lt - 0.25) / 0.7); S = max(8, int(c.W * 0.2 * s * (0.55 + 0.45 * p)) // 4 * 4)
    t = cached(e, ('t', S), lambda: text_img(e.o.get('text', '2X'), S, 'didone', CREAMY, shadow=8))
    bw, bh = t.width + c.W * 0.03 * s, t.height
    x0, y0 = cx - bw / 2, cy - bh / 2
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); B = BLUE + (255,); lw = max(2, c.W // 360)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=BLUE + (int(130 * (1 - 0.7 * clamp((c.lt - 0.9) / 0.3))),))
    for (ax, ay, bx, by) in ((x0, y0, x0 + bw, y0), (x0, y0 + bh, x0 + bw, y0 + bh), (x0, y0, x0, y0 + bh), (x0 + bw, y0, x0 + bw, y0 + bh)):
        n = max(1, int(math.hypot(bx - ax, by - ay) / (c.W * 0.018)))
        for j in range(0, n, 2): d.line([(ax + (bx - ax) * j / n, ay + (by - ay) * j / n), (ax + (bx - ax) * (j + 1) / n, ay + (by - ay) * (j + 1) / n)], fill=B, width=lw)
    hs = c.W * 0.009
    for qx, qy in ((x0, y0), (x0 + bw, y0), (x0, y0 + bh), (x0 + bw, y0 + bh)): d.rectangle([qx - hs, qy - hs, qx + hs, qy + hs], fill=(255, 255, 255, 255), outline=B, width=lw)
    comp(c, to_np(lay), 0, 0, al, behind=True); place(c, t, cx, cy, 1, 0, al, behind=True)
    cu = cached(e, 'cu', lambda: cursor(c.W * 0.045)); place(c, cu, x0 + bw + cu.width * 0.4, y0 + bh + cu.height * 0.4, 1, 0, al)


@effect('wave-trim', 'the silent parts of your voice are trimmed away on screen until only your words are left')
def fx_wave_trim(c, e):
    al = pop(c, 0, 0.2) * fade(c, e)
    if al <= 0: return
    p = ease_inout((c.lt - 0.25) / 0.5); pw, ph, ww = c.W * (0.84 - 0.4 * p), c.W * 0.2, c.W * 0.3
    hts = cached(e, 'h', lambda: np.random.default_rng(3).uniform(0.15, 1, 60))
    lay = Image.new('RGBA', (int(pw) + 2, int(ph) + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, pw, ph], fill=INKY + (240,)); cx, cy = pw / 2, ph / 2; st = ww / len(hts)
    for j, h in enumerate(hts):
        x = cx - ww / 2 + j * st; v = h * ph * 0.36 * (0.55 + 0.45 * math.sin(j * 0.33))
        d.rectangle([x, cy - v, x + st * 0.45, cy + v], fill=CREAMY + (255,))
    r, gap = c.W * 0.0045, c.W * 0.016
    for sd in (-1, 1):
        x = cx + sd * (ww / 2 + gap)
        while 0 < x < pw: d.ellipse([x - r, cy - r, x + r, cy + r], fill=BLUE + (255,)); x += sd * gap
    cx, cy, s, slot = clear_spot(c, e, c.W * 0.84, ph, ('above', 'below'), 0.7)
    place(c, lay, cx, cy, s, 0, al, behind=slot == 'above', guard=slot != 'above')


@effect('huge-strike', 'one huge serif word fills the wall behind you, then a red line crosses it out')
def fx_huge_strike(c, e):
    al = fade(c, e)
    t = cached(e, 't', lambda: fit_text(e.o.get('text', '8 HOURS'), c.W * 0.9, 'didone', int(c.W * 0.28), fill=CREAMY, shadow=10))
    cw = int(t.width * ease_out(c.lt / 0.35)); cy = above_head(c, t.height)
    if cw > 2: place(c, t.crop((0, 0, cw, t.height)), c.W / 2 - (t.width - cw) / 2, cy, 1, 0, al, behind=True)
    at = float(e.o.get('at', 0.6)); k = ease_out((c.lt - at) / 0.18)
    if k > 0:
        lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); x0, x1 = c.W / 2 - t.width * 0.46, c.W / 2 + t.width * 0.46
        pts = [(x0 + (x1 - x0) * u, cy + t.height * 0.04 - u * t.height * 0.05 + math.sin(u * 19) * c.W * 0.002) for u in np.linspace(0, 1, 40)]
        hand_path(ImageDraw.Draw(lay), pts, RED + (255,), max(6, c.W // 80), k); comp(c, to_np(lay), 0, 0, al, behind=True)


@effect('crayon-write', 'a red crayon writes your word behind your head, then underlines it')
def fx_crayon_write(c, e):
    al = fade(c, e)
    B = min(c.W, c.H * 0.75)
    cx, cy, s, slot = clear_spot(c, e, B * 0.82, B * 0.2, ('above', 'below'), 0.6)
    bh = slot == 'above'  # behind your head when it's above you, in front of your chest otherwise
    t = cached(e, 't', lambda: fit_text(e.o.get('text', 'NOBODY'), B * 0.82 * s, 'hand', int(B * 0.17 * s), fill=CRAYON, shadow=4))
    p = ease_inout((c.lt - 0.05) / 0.8); cw = int(t.width * p); x0 = cx - t.width / 2
    if cw > 2: place(c, t.crop((0, 0, cw, t.height)), x0 + cw / 2, cy, 1, 0, al, behind=bh, guard=not bh)
    if c.lt > 0.9:
        lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); yy = cy + t.height * 0.42
        pts = [(x0 + t.width * (0.06 + 0.88 * u), yy - u * c.W * 0.006 + math.sin(u * 23) * c.W * 0.002) for u in np.linspace(0, 1, 40)]
        hand_path(ImageDraw.Draw(lay), pts, CRAYON + (255,), max(5, int(B) // 95), ease_out((c.lt - 0.9) / 0.25)); comp(c, to_np(lay), 0, 0, al, behind=bh, guard=not bh)
    def mk():
        L = int(B * 0.22); T = int(L * 0.2); im = Image.new('RGBA', (L + T, T), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(0, T / 2), (T, 0), (T, T)], fill=(124, 58, 237, 255)); d.rounded_rectangle([T * 0.9, 0, L + T - 1, T - 1], T // 5, fill=(124, 58, 237, 255))
        for xx in (T * 1.5, L + T * 0.4): d.rectangle([xx, 0, xx + T * 0.35, T - 1], fill=(124, 58, 237, 255))
        return shadowed(im.rotate(-38, Image.BICUBIC, expand=True), 6, 4, 100)
    cr = cached(e, 'cr', mk); away = ease_inout((c.lt - 1.1) / 0.3)
    if away < 1:
        tx, ty = x0 + cw + away * c.W * 0.6, cy + math.sin(c.lt * 30) * t.height * 0.12 + away * c.H * 0.2
        place(c, cr, tx + cr.width * 0.47, ty + cr.height * 0.45, 1, 0, al)


@effect('fan-build', 'your reel covers deal into a fan behind your head, one card at a time')
def fx_fan_build(c, e):
    n = int(e.o.get('count', 13)); al = fade(c, e); cw = int(min(c.W, c.H * 0.75) * 0.15)
    cards = cached(e, 'cards', lambda: [card(vary(e.cards[i % len(e.cards)], i) if e.o.get('images') is None else e.cards[i % len(e.cards)], cw, 0.05) for i in range(n)])
    px, py = c.fx, c.fy + c.fw * 0.1
    R = max(c.fw * 1.45, min(c.fw * 2.15, py - cards[0].height * 0.45))  # keep the top of the fan in frame
    spread = 62 + 38 * clamp((c.fw * 2.15 - R) / (c.fw * 0.7))  # less headroom: fan wider so the cards show beside you
    for i in range(n):
        t0 = 0.055 * i
        if c.lt < t0: break
        q = ease_out((c.lt - t0) / 0.3); a = -95 + (-spread + 2 * spread * i / max(1, n - 1) + 95) * q; r = math.radians(a)
        place(c, cards[i], px + R * math.sin(r), py - R * math.cos(r), 1, -a, al, behind=True)


# ---------- pack 4: Applied AI Mastermind additions (Nov 2026) ----------
ACC, ACC_L, ACC_LL, NAVY, PAPER, MUTE = (124, 58, 237), (167, 139, 250), (237, 233, 254), (26, 26, 46), (250, 250, 250), (100, 100, 140)




def _ker(r): return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(r) + 1, 2 * int(r) + 1))


def _wrap(text, f, max_w):
    lines, cur = [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w).strip()
        if f.getlength(t) > max_w and cur: lines.append(cur); cur = w
        else: cur = t
    return lines + [cur]


@effect('outline-glow', 'a glowing purple outline draws itself around you and pulses')
def fx_outline_glow(c, e):
    k = ramp(c, e, 0.2, 0.25); col = np.float32(rgb(e.o.get('color'), ACC)) / 255
    m = c.m; r = max(3, int(c.U * 0.006))
    ring = np.clip(cv2.dilate(m, _ker(r)) - m, 0, 1)
    yy = grid(c)[1]; sweep = clamp(c.lt / 0.55) * (c.H * 1.15)  # draws on from the top of your head down
    ring = ring * np.clip((sweep - yy) / (c.H * 0.06), 0, 1)
    glow = cv2.GaussianBlur(ring, (0, 0), c.U * 0.022) * 2.2 * (0.82 + 0.18 * math.sin(c.lt * 5.5))
    c.img = c.img * (1 - 0.3 * k * (1 - m))[..., None]
    c.img = np.clip(c.img + col * (glow * k)[..., None] + (ring * k * 0.75)[..., None], 0, 1)


@effect('lower-third', 'a name and title bar wipes in at the bottom corner')
def fx_lower_third(c, e):
    U = c.U; al = fade(c, e); name = e.o.get('text', 'Matt Penny'); role = e.o.get('role', 'Applied AI Mastermind')
    nm = cached(e, 'n', lambda: text_img(name, U * 0.075, 'bold', (255, 255, 255), shadow=8))
    rt = cached(e, 'r', lambda: text_img(role, U * 0.042, 'uib', (255, 255, 255)))
    x0 = U * 0.07; y0 = c.H * float(e.o.get('y', 0.8 if c.H > c.W else 0.76)); bw = max(6, int(U * 0.012))
    k1 = ease_out(c.lt / 0.25); k2 = ease_out((c.lt - 0.12) / 0.35); k3 = ease_out((c.lt - 0.3) / 0.3)
    bh = int((nm.height * 0.72 + rt.height * 1.5) * k1)
    if bh > 2: comp(c, rrect(bw, bh, bw / 2, ACC + (255,)), x0, y0 + (nm.height * 0.72 + rt.height * 1.5 - bh) / 2 + nm.height * 0.14, al, guard=True)
    tx = x0 + bw + U * 0.025
    if k2 > 0: comp(c, nm.crop((0, 0, max(1, int(nm.width * k2)), nm.height)), tx - (1 - k2) * U * 0.03, y0, al, guard=True)
    if k3 > 0:
        pill = rrect(rt.width + U * 0.04, rt.height * 1.15, rt.height * 0.3, ACC + (255,)); pill.alpha_composite(rt, (int(U * 0.02), int(rt.height * 0.05)))
        comp(c, pill.crop((0, 0, max(1, int(pill.width * k3)), pill.height)), tx + U * 0.004, y0 + nm.height * 0.86, al, guard=True)


@effect('big-stat', 'a huge number counts up beside you with a label and a hand-drawn underline')
def fx_big_stat(c, e):
    U = c.U; al = fade(c, e) * clamp(c.lt / 0.1); val = str(e.o.get('to', '3.2M')); lab = e.o.get('text', 'views in 30 days')
    num, suf, dec = split_num(val); S = int(U * 0.24)
    full = cached(e, 'full', lambda: text_img(val, S, 'bold', (255, 255, 255), shadow=10))
    lt = cached(e, 'lab', lambda: text_img(lab.upper(), U * 0.048, 'uib', ACC_LL, shadow=6))
    w, h = max(full.width, lt.width), full.height * 0.78 + lt.height * 1.6
    cx, cy, s, slot = clear_spot(c, e, w, h, ('side', 'below'), 0.7, floor=0.55)
    p = ease_out((c.lt - 0.1) / max(0.5, e.d * 0.45))
    now = text_img(f'{num * p:.{dec}f}{suf}', S, 'bold', (255, 255, 255), shadow=10)
    top = cy - h * s / 2
    place(c, now, cx, top + full.height * s * 0.42, s * (0.85 + 0.15 * ease_back(c.lt / 0.3)), 0, al, guard=True)
    uy = top + full.height * s * 0.8; uw = full.width * s * 0.9
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0))
    pts = [(cx - uw / 2 + uw * u, uy + math.sin(u * 9) * U * 0.004 - u * U * 0.008) for u in np.linspace(0, 1, 40)]
    hand_path(ImageDraw.Draw(lay), pts, ACC + (255,), max(5, int(U * s) // 70), ease_out((c.lt - 0.45) / 0.35))
    comp(c, to_np(lay), 0, 0, al, guard=True)
    place(c, lt, cx, uy + lt.height * s * 1.0, s, 0, al * clamp((c.lt - 0.3) / 0.2), guard=True)


@effect('step-tracker', 'a step counter card: Step 2 of 4 with a progress bar that fills')
def fx_step_tracker(c, e):
    U = c.U; al = fade(c, e); n = int(e.o.get('of', 4)); cur = int(e.o.get('step', 2)); title = e.o.get('text', 'Write the hook')
    cw, ch = U * 0.8, U * 0.26; pad = U * 0.05
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('above', 'side', 'below'), 0.75, floor=0.6)
    im = rrect(cw, ch, ch * 0.2, NAVY + (240,)); d = ImageDraw.Draw(im)
    d.text((pad, ch * 0.24), f'STEP {cur} OF {n}', font=font('uib', ch * 0.13), fill=ACC_L + (255,), anchor='lm')
    d.text((pad, ch * 0.5), title, font=font('bold', ch * 0.24), fill=(255, 255, 255, 255), anchor='lm')
    gap = U * 0.015; sw = (cw - 2 * pad - gap * (n - 1)) / n; y0, y1 = ch * 0.76, ch * 0.84
    fillk = ease_inout((c.lt - 0.35) / 0.6)
    for i in range(n):
        x = pad + i * (sw + gap)
        d.rounded_rectangle([x, y0, x + sw, y1], (y1 - y0) / 2, fill=(255, 255, 255, 46))
        f = 1.0 if i < cur - 1 else (fillk if i == cur - 1 else 0.0)
        if f > 0.02: d.rounded_rectangle([x, y0, x + sw * f, y1], (y1 - y0) / 2, fill=ACC + (255,))
    q = pop(c, 0.0, 0.32)
    place(c, shadowed(im, 16, 8, 110), cx, cy + (1 - clamp(q)) * U * 0.03, s * (0.7 + 0.3 * q), 0, al * clamp(c.lt / 0.1), behind=slot == 'above', guard=slot != 'above')


@effect('search-type', 'a search bar types your question, then the cursor clicks it')
def fx_search_type(c, e):
    U = c.U; al = fade(c, e); q = e.o.get('text', 'how to edit reels with AI')
    bw, bh = U * 0.86, U * 0.14
    cx, cy, s, slot = clear_spot(c, e, bw, bh, ('above', 'below'), 0.75, floor=0.6)
    t_done = 0.25 + 0.045 * len(q); t_click = t_done + 0.35
    typed = q[:int(clamp((c.lt - 0.25) / max(0.05, t_done - 0.25)) * len(q))]
    press = math.sin(math.pi * clamp((c.lt - t_click) / 0.22)) if c.lt > t_click else 0
    im = rrect(bw, bh, bh / 2, (255, 255, 255, 250), ACC + ((255,) if c.lt > t_click else (0,)), max(3, int(U * 0.006))); d = ImageDraw.Draw(im)
    r = bh * 0.17; ix, iy = bh * 0.55, bh * 0.47; lw = max(3, int(bh * 0.045))
    d.ellipse([ix - r, iy - r, ix + r, iy + r], outline=MUTE + (255,), width=lw)
    d.line([(ix + r * 0.75, iy + r * 0.75), (ix + r * 1.55, iy + r * 1.55)], fill=MUTE + (255,), width=lw)
    f = font('ui', bh * 0.32); tx = bh * 1.0
    d.text((tx, bh / 2), typed or 'Search', font=f, fill=(NAVY if typed else (148, 148, 184)) + (255,), anchor='lm')
    if typed and c.lt < t_click and int(c.lt * 3.5) % 2 == 0:
        xx = tx + f.getlength(typed) + bh * 0.03; d.rectangle([xx, bh * 0.3, xx + max(2, bh * 0.025), bh * 0.7], fill=ACC + (255,))
    qk = pop(c, 0.0, 0.3)
    place(c, shadowed(im, 18, 8, 110), cx, cy, s * (0.75 + 0.25 * qk) * (1 - 0.04 * press), 0, al * clamp(c.lt / 0.1), behind=slot == 'above', guard=slot != 'above')
    cu = cached(e, 'cu', lambda: cursor(U * 0.06)); ck = ease_inout((c.lt - t_done) / 0.35)
    if c.lt > t_done:
        tx2, ty2 = cx + bw * s * 0.36, cy + bh * s * 0.1; sx, sy = cx + bw * s * 0.5, cy + bh * s * 1.6
        place(c, cu, sx + (tx2 - sx) * ck + cu.width / 2, sy + (ty2 - sy) * ck + cu.height / 2, 0.88 if press > 0.3 else 1, 0, al, keep=True)


@effect('quote-card', 'a pull-quote card: a big purple quote mark, your line typed word by word, and your name')
def fx_quote_card(c, e):
    U = c.U; al = fade(c, e); quote = e.o.get('text', 'The best edit is the one nobody notices.'); who = e.o.get('by', 'Matt Penny')
    cw = U * 0.82; pad = U * 0.06; f = font('bold', U * 0.062); fb = font('uib', U * 0.034)
    lines = cached(e, 'ln', lambda: _wrap(quote, f, cw - 2 * pad)); lh = U * 0.074
    ch = pad * 1.2 + U * 0.11 + lh * len(lines) + U * 0.085
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.55)
    im = rrect(cw, ch, U * 0.035, PAPER + (250,)); d = ImageDraw.Draw(im)
    d.text((pad, pad * 0.5), '“', font=font('bold', U * 0.26), fill=ACC + (255,))
    words = quote.split(' '); shown = int(clamp((c.lt - 0.25) / max(0.3, 0.09 * len(words))) * len(words) + 0.001); seen = 0
    y = pad * 1.2 + U * 0.11
    for ln in lines:
        ws = ln.split(' '); take = max(0, min(len(ws), shown - seen)); seen += len(ws)
        if take: d.text((pad, y), ' '.join(ws[:take]), font=f, fill=NAVY + (255,))
        y += lh
    kb = clamp((c.lt - 0.35 - 0.09 * len(words)) / 0.25)
    if kb > 0:
        d.rectangle([pad, y + U * 0.022, pad + U * 0.05 * kb, y + U * 0.022 + max(3, U * 0.006)], fill=ACC + (255,))
        d.text((pad + U * 0.065, y + U * 0.025), who, font=fb, fill=MUTE + (int(255 * kb),), anchor='lm')
    q = pop(c, 0.0, 0.32)
    place(c, shadowed(im, 20, 10, 110), cx, cy + (1 - clamp(q)) * U * 0.03, s * (0.75 + 0.25 * q), 0, al * clamp(c.lt / 0.1), guard=True)


# ---------- pack 5: graphics (Nov 2026) ----------
OK, ERR, WHITE = (16, 185, 129), (239, 68, 68), (255, 255, 255)


def _show(c, e, im, cx, cy, s, slot=None, t0=0.0, front=True):
    """Pop a card in at its spot and fade it out with the effect."""
    q = pop(c, t0, 0.32)
    place(c, shadowed(im, 18, 8, 110), cx, cy + (1 - clamp(q)) * c.U * 0.03, s * (0.75 + 0.25 * q), 0,
          fade(c, e) * clamp((c.lt - t0) / 0.1), behind=not front, guard=front)


def _cross(d, x, y, s, color, w):
    d.line([(x, y), (x + s, y + s)], fill=color, width=w); d.line([(x + s, y), (x, y + s)], fill=color, width=w)


@effect('chapter-title', 'a chapter card: a big purple number, a line that wipes in and the chapter title')
def fx_chapter_title(c, e):
    U = c.U; num = str(e.o.get('n', '01')); title = e.o.get('text', 'The setup'); al = fade(c, e)
    nt = cached(e, 'n', lambda: text_img(num, U * 0.26, 'bold', ACC_L, shadow=10))
    tt = cached(e, 't', lambda: fit_text(title, U * 0.8, 'bold', int(U * 0.1), fill=WHITE, shadow=9))
    lt = cached(e, 'l', lambda: text_img(e.o.get('label', 'CHAPTER'), U * 0.046, 'uib', WHITE, shadow=5))
    w = max(nt.width + lt.width + U * 0.04, tt.width); h = nt.height * 0.8 + tt.height * 0.95 + U * 0.03
    cx, cy, s, slot = clear_spot(c, e, w, h, ('side', 'below'), 0.7, floor=0.55)
    x0, y0 = cx - w * s / 2, cy - h * s / 2
    k1, k2, k3 = ease_out(c.lt / 0.3), ease_out((c.lt - 0.15) / 0.35), ease_out((c.lt - 0.3) / 0.35)
    def put(im, x, y, k, dy=0):
        if k <= 0: return
        im2 = im if s >= 0.999 else im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        comp(c, im2, x, y + (1 - k) * dy, al * k, guard=True)
    put(nt, x0, y0, k1, U * 0.04)
    put(lt, x0 + (nt.width + U * 0.03) * s, y0 + nt.height * 0.52 * s, k2)
    ly = y0 + nt.height * 0.8 * s
    if k2 > 0: comp(c, rrect(max(2, w * s * k2), max(4, U * 0.008 * s), U * 0.004, ACC + (255,)), x0, ly, al, guard=True)
    if k3 > 0: put(tt.crop((0, 0, max(1, int(tt.width * k3)), tt.height)), x0, ly + U * 0.02 * s, 1)


@effect('versus', 'two cards face off either side of a VS badge, then the winner lights up')
def fx_versus(c, e):
    U = c.U; a, b = (e.o.get('text', 'Claude|ChatGPT').split('|') + ['B'])[:2]; win = int(e.o.get('win', 1))
    cw, ch, gap = U * 0.36, U * 0.18, U * 0.1; W_, H_ = cw * 2 + gap, ch
    cx, cy, s, slot = clear_spot(c, e, W_, H_, ('below', 'side'), 0.75, floor=0.6)
    t_win = max(1.2, e.d * 0.5); wk = ease_out((c.lt - t_win) / 0.3) if win in (1, 2) else 0
    im = Image.new('RGBA', (int(W_), int(H_ * 1.25)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); oy = H_ * 0.125
    for i, name in enumerate((a, b)):
        k = ease_back((c.lt - 0.08 * i) / 0.35); x = (0 if i == 0 else cw + gap) + (-1 if i == 0 else 1) * (1 - clamp(k)) * U * 0.12
        won = (i + 1 == win); mix = wk if won else 0
        fill = tuple(int(PAPER[j] * (1 - mix) + ACC[j] * mix) for j in range(3)) + (int(250 * (1 - 0.45 * (wk if not won else 0))),)
        d.rounded_rectangle([x, oy, x + cw, oy + ch], ch * 0.22, fill=fill)
        f = font('bold', min(ch * 0.36, cw * 0.82 / max(1, font('bold', 100).getlength(name) / 100)))
        d.text((x + cw / 2, oy + ch / 2), name, font=f, fill=(WHITE if mix > 0.5 else NAVY) + (255,), anchor='mm')
        if won and wk > 0.3:
            r = ch * 0.17; bx, by = x + cw - r * 0.6, oy - r * 0.2
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=OK + (255,)); tick(d, bx - r * 0.5, by - r * 0.45, r, WHITE + (255,), max(3, int(r / 4)))
    vk = ease_back((c.lt - 0.25) / 0.3); r = gap * 0.62 * clamp(vk)
    if r > 2:
        d.ellipse([W_ / 2 - r, oy + ch / 2 - r, W_ / 2 + r, oy + ch / 2 + r], fill=NAVY + (255,), outline=WHITE + (255,), width=max(2, int(U * 0.005)))
        d.text((W_ / 2, oy + ch / 2), 'VS', font=font('bold', r * 0.8), fill=WHITE + (255,), anchor='mm')
    place(c, shadowed(im, 16, 8, 100), cx, cy, s, 0, fade(c, e) * clamp(c.lt / 0.1), guard=True)


@effect('pros-cons', 'a two-column card: green ticks for the pros, red crosses for the cons, one row at a time')
def fx_pros_cons(c, e):
    U = c.U; pros = e.o.get('pros', 'Fast|Free to start|No editor').split('|'); cons = e.o.get('cons', 'Needs setup|Learning curve').split('|')
    rows = max(len(pros), len(cons)); cw = U * 0.86; rh = U * 0.075; pad = U * 0.045; ch = pad * 2 + U * 0.06 + rh * rows
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.035, PAPER + (250,)); d = ImageDraw.Draw(im); half = cw / 2
    d.line([(half, pad), (half, ch - pad)], fill=ACC_LL + (255,), width=max(2, int(U * 0.004)))
    for j, (head, col, items, x0) in enumerate((('PROS', OK, pros, pad), ('CONS', ERR, cons, half + pad * 0.8))):
        d.text((x0, pad + U * 0.012), head, font=font('uib', U * 0.036), fill=col + (255,), anchor='lm')
        for i, it in enumerate(items):
            t0 = 0.3 + 0.18 * (i * 2 + j); k = ease_out((c.lt - t0) / 0.22)
            if k <= 0: continue
            y = pad + U * 0.06 + rh * i + rh * 0.5; r = rh * 0.26; a = int(255 * k); bx = x0 + r
            d.ellipse([bx - r, y - r, bx + r, y + r], fill=col + (a,))
            if j == 0: tick(d, bx - r * 0.5, y - r * 0.45, r, WHITE + (a,), max(2, int(r / 3.5)))
            else: _cross(d, bx - r * 0.38, y - r * 0.38, r * 0.76, WHITE + (a,), max(2, int(r / 3.5)))
            f = font('ui', min(U * 0.04, (half - pad * 1.6 - r * 2.8) / max(1, font('ui', 100).getlength(it)) * 100))
            d.text((x0 + r * 2.8 - (1 - k) * U * 0.02, y), it, font=f, fill=NAVY + (a,), anchor='lm')
    _show(c, e, im, cx, cy, s)


@effect('roadmap', 'a timeline of steps: the line fills left to right and each stop lights up with its label')
def fx_roadmap(c, e):
    U = c.U; stops = e.o.get('text', 'Idea|Script|Record|Edit|Post').split('|'); n = len(stops)
    cw, ch = U * 0.88, U * 0.24; pad = U * 0.09
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('above', 'below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, ch * 0.2, NAVY + (238,)); d = ImageDraw.Draw(im)
    y = ch * 0.4; x0, x1 = pad, cw - pad; lw = max(4, int(U * 0.008))
    p = ease_inout((c.lt - 0.3) / max(0.8, e.d * 0.55))
    d.line([(x0, y), (x1, y)], fill=(255, 255, 255, 50), width=lw)
    if p > 0: d.line([(x0, y), (x0 + (x1 - x0) * p, y)], fill=ACC_L + (255,), width=lw)
    f = font('uib', min(U * 0.034, (x1 - x0) / max(1, n - 1) * 0.9 / max(1, max(font('uib', 100).getlength(t) for t in stops)) * 100))
    for i, t in enumerate(stops):
        u = i / max(1, n - 1); x = x0 + (x1 - x0) * u; on = clamp((p - u) / 0.06 + 0.5) if p >= u - 0.03 else 0
        k = ease_back(on); r = U * 0.02 * (0.7 + 0.5 * k)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(ACC if on > 0.5 else NAVY) + (255,), outline=(WHITE if on > 0.5 else (148, 148, 184)) + (255,), width=max(2, int(U * 0.005)))
        d.text((x, y + ch * 0.32), t, font=f, fill=((WHITE if on > 0.5 else (148, 148, 184)) + (255,)), anchor='mm')
    _show(c, e, im, cx, cy, s, front=slot != 'above')


@effect('price-drop', 'the old price gets struck out in red and the new price slams in')
def fx_price_drop(c, e):
    U = c.U; old = e.o.get('from', '$99/mo'); new = e.o.get('to', '$0'); lab = e.o.get('text', 'with Claude')
    cw, ch = U * 0.6, U * 0.4
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.04, PAPER + (250,)); d = ImageDraw.Draw(im)
    fo = font('uib', U * 0.07); ow = fo.getlength(old); ox = cw / 2 - ow / 2; oy = ch * 0.2
    sk = ease_out((c.lt - 0.45) / 0.25)
    d.text((cw / 2, oy), old, font=fo, fill=(MUTE if sk > 0.5 else NAVY) + (255,), anchor='mm')
    if sk > 0: d.line([(ox - U * 0.015, oy + U * 0.004), (ox - U * 0.015 + (ow + U * 0.03) * sk, oy - U * 0.006)], fill=ERR + (255,), width=max(4, int(U * 0.009)))
    nk = ease_back((c.lt - 0.75) / 0.3)
    if nk > 0:
        nt = text_img(new, U * 0.19 * (0.6 + 0.4 * nk), 'bold', ACC)
        im.alpha_composite(nt, (int(cw / 2 - nt.width / 2), int(ch * 0.56 - nt.height / 2)))
        d.text((cw / 2, ch * 0.86), lab, font=font('uib', U * 0.04), fill=MUTE + (int(255 * clamp((c.lt - 0.95) / 0.2)),), anchor='mm')
    _show(c, e, im, cx, cy, s)


@effect('bar-compare', 'two bars race: the long grey "before" against the short purple "after"')
def fx_bar_compare(c, e):
    U = c.U
    rows = [(x.split('::') + ['', '1'])[:3] for x in e.o.get('text', 'By hand::4 hrs::1|With Claude::4 min::0.12').split('|')][:3]
    cw = U * 0.86; pad = U * 0.05; rh = U * 0.13; ch = pad * 2 + rh * len(rows)
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.035, NAVY + (240,)); d = ImageDraw.Draw(im); track = cw - pad * 2
    for i, (lab, val, frac) in enumerate(rows):
        y = pad + rh * i; k = ease_out((c.lt - 0.25 - 0.3 * i) / 0.7); last = i == len(rows) - 1
        d.text((pad, y + rh * 0.2), lab, font=font('uib', U * 0.036), fill=(ACC_L if last else (148, 148, 184)) + (255,), anchor='lm')
        by0, by1 = y + rh * 0.42, y + rh * 0.82; w = max(by1 - by0, track * clamp(float(frac)) * k)
        d.rounded_rectangle([pad, by0, pad + track, by1], (by1 - by0) / 2, fill=(255, 255, 255, 26))
        if k > 0:
            d.rounded_rectangle([pad, by0, pad + w, by1], (by1 - by0) / 2, fill=(ACC if last else MUTE) + (255,))
            fv = font('bold', U * 0.042); tw = fv.getlength(val)
            inside = w > tw + U * 0.05
            d.text((pad + w - U * 0.02 if inside else pad + w + U * 0.02, (by0 + by1) / 2), val, font=fv, fill=WHITE + (int(255 * clamp(k * 1.5)),), anchor='rm' if inside else 'lm')
    _show(c, e, im, cx, cy, s)


@effect('prompt-box', 'an AI chat box types your prompt, then the send button fires')
def fx_prompt_box(c, e):
    U = c.U; text = e.o.get('text', 'Edit this reel: cut the pauses, add captions and a hook'); model = e.o.get('model', 'Claude')
    cw, ch = U * 0.86, U * 0.34; pad = U * 0.045
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    t_done = 0.25 + 0.03 * len(text); t_send = t_done + 0.3; sent = c.lt > t_send
    im = rrect(cw, ch, U * 0.05, PAPER + (252,), ACC_LL + (255,), max(2, int(U * 0.004))); d = ImageDraw.Draw(im)
    f = font('ui', U * 0.042); lines = cached(e, 'ln', lambda: _wrap(text, f, cw - pad * 2)); lh = U * 0.055
    nshow = int(clamp((c.lt - 0.25) / max(0.05, t_done - 0.25)) * len(text)); seen = 0; lx = ly = None
    if sent:
        dots = '.' * (1 + int(c.lt * 3) % 3)
        d.text((pad, pad + lh * 0.5), f'{model} is editing{dots}', font=font('uib', U * 0.042), fill=ACC + (255,), anchor='lm')
    else:
        for j, ln in enumerate(lines[:3]):
            take = max(0, min(len(ln), nshow - seen)); seen += len(ln) + 1
            if take: d.text((pad, pad + lh * j + lh * 0.5), ln[:take], font=f, fill=NAVY + (255,), anchor='lm'); lx, ly = pad + f.getlength(ln[:take]), pad + lh * j
        if nshow == 0: d.text((pad, pad + lh * 0.5), 'Ask anything', font=f, fill=(148, 148, 184, 255), anchor='lm')
        if lx is not None and int(c.lt * 3.5) % 2 == 0: d.rectangle([lx + U * 0.006, ly + lh * 0.18, lx + U * 0.011, ly + lh * 0.82], fill=ACC + (255,))
    by = ch - pad - U * 0.04; r = U * 0.04
    d.ellipse([pad, by - r * 0.8, pad + r * 1.6, by + r * 0.8], outline=(148, 148, 184, 255), width=max(2, int(U * 0.004)))
    d.text((pad + r * 0.8, by), '+', font=font('ui', U * 0.05), fill=MUTE + (255,), anchor='mm')
    fm = font('uib', U * 0.032); mw = fm.getlength(model) + U * 0.05
    d.rounded_rectangle([pad + r * 2.1, by - r * 0.7, pad + r * 2.1 + mw, by + r * 0.7], r * 0.7, fill=ACC_LL + (255,))
    d.text((pad + r * 2.1 + mw / 2, by), model, font=fm, fill=ACC + (255,), anchor='mm')
    press = math.sin(math.pi * clamp((c.lt - t_send) / 0.25)) if sent else 0; rr = r * (1 - 0.18 * press); sx = cw - pad - r
    ready = nshow >= len(text)
    d.ellipse([sx - rr, by - rr, sx + rr, by + rr], fill=(ACC if ready else (200, 196, 220)) + (255,))
    aw = max(3, int(U * 0.007))
    d.line([(sx, by + rr * 0.42), (sx, by - rr * 0.42)], fill=WHITE + (255,), width=aw)
    d.line([(sx - rr * 0.36, by - rr * 0.06), (sx, by - rr * 0.44), (sx + rr * 0.36, by - rr * 0.06)], fill=WHITE + (255,), width=aw, joint='curve')
    _show(c, e, im, cx, cy, s)


@effect('terminal', 'a terminal window types your command and prints green ticks as each step finishes')
def fx_terminal(c, e):
    U = c.U; cmd = e.o.get('text', 'claude "edit my reel"'); outs = e.o.get('lines', 'Cut 14 pauses|Added captions|Rendered in 38s').split('|')
    cw = U * 0.86; pad = U * 0.045; bar = U * 0.07; lh = U * 0.062; ch = bar + pad * 1.6 + lh * (1 + len(outs))
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.03, (18, 18, 32, 245)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, cw - 1, bar], U * 0.03, fill=(38, 38, 62, 255)); d.rectangle([0, bar * 0.5, cw - 1, bar], fill=(38, 38, 62, 255))
    for j, col in enumerate((ERR, (245, 158, 11), OK)):
        r = bar * 0.17; x = pad + j * r * 3.2; d.ellipse([x, bar / 2 - r, x + 2 * r, bar / 2 + r], fill=col + (255,))
    d.text((cw / 2, bar / 2), e.o.get('title', 'frame-pilot'), font=font('uim', bar * 0.38), fill=(148, 148, 184, 255), anchor='mm')
    f = font('mono', min(U * 0.04, (cw - pad * 2) / max(1, font('mono', 100).getlength('$ ' + cmd + '_')) * 100)); y = bar + pad * 0.8 + lh / 2
    t_done = 0.3 + 0.045 * len(cmd); typed = cmd[:int(clamp((c.lt - 0.3) / max(0.05, t_done - 0.3)) * len(cmd))]
    d.text((pad, y), '$ ', font=f, fill=ACC_L + (255,), anchor='lm'); px = pad + f.getlength('$ ')
    d.text((px, y), typed, font=f, fill=WHITE + (255,), anchor='lm')
    if c.lt < t_done + 0.2 and int(c.lt * 3.5) % 2 == 0:
        xx = px + f.getlength(typed); d.rectangle([xx + 2, y - lh * 0.3, xx + f.getlength('_'), y + lh * 0.3], fill=WHITE + (220,))
    fo = font('mono', f.size * 0.9)
    for i, ln in enumerate(outs):
        t0 = t_done + 0.35 + 0.4 * i
        if c.lt < t0: break
        yy = y + lh * (i + 1); a = int(255 * clamp((c.lt - t0) / 0.15))
        tick(d, pad, yy - lh * 0.2, lh * 0.36, OK + (a,), max(2, int(U * 0.006)))
        d.text((pad + lh * 0.7, yy), ln, font=fo, fill=(226, 232, 240, a), anchor='lm')
    _show(c, e, im, cx, cy, s)


@effect('comment-cta', 'a call to action: Comment the keyword and I will send it, with a bouncing arrow')
def fx_comment_cta(c, e):
    U = c.U; word = e.o.get('text', 'EFFECTS').upper(); pre = e.o.get('pre', 'Comment'); post = e.o.get('post', "and I'll send it")
    f = font('uib', U * 0.05); fk = font('bold', U * 0.056); pad = U * 0.045; chip_w = fk.getlength(word) + U * 0.05
    cw = pad * 2 + f.getlength(pre + ' ') + chip_w; ch = U * 0.2
    cw = max(cw, pad * 2 + font('ui', U * 0.036).getlength(post))
    cx, cy, s, slot = clear_spot(c, e, cw, ch + U * 0.1, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, ch * 0.24, PAPER + (252,)); d = ImageDraw.Draw(im); y1 = ch * 0.36
    d.text((pad, y1), pre, font=f, fill=NAVY + (255,), anchor='lm'); x = pad + f.getlength(pre + ' ')
    typed = word[:int(clamp((c.lt - 0.35) / max(0.1, 0.07 * len(word))) * len(word))]
    d.rounded_rectangle([x, y1 - U * 0.04, x + chip_w, y1 + U * 0.04], U * 0.018, fill=ACC + (255,))
    d.text((x + chip_w / 2, y1), typed, font=fk, fill=WHITE + (255,), anchor='mm')
    d.text((pad, ch * 0.74), post, font=font('ui', U * 0.036), fill=MUTE + (255,), anchor='lm')
    _show(c, e, im, cx, cy - U * 0.05 * s, s)
    ak = clamp((c.lt - 0.6) / 0.2) * fade(c, e)
    if ak > 0:
        b = abs(math.sin(c.lt * 4.2)) * U * 0.022; ar = Image.new('RGBA', (int(U * 0.1), int(U * 0.1)), (0, 0, 0, 0)); ad = ImageDraw.Draw(ar)
        m_ = U * 0.05; lw = max(5, int(U * 0.012))
        ad.line([(m_, U * 0.012), (m_, U * 0.08)], fill=ACC_L + (255,), width=lw)
        ad.line([(m_ - U * 0.028, U * 0.052), (m_, U * 0.084), (m_ + U * 0.028, U * 0.052)], fill=ACC_L + (255,), width=lw, joint='curve')
        place(c, shadowed(ar, 6, 3, 110), cx, cy + (ch / 2 + U * 0.03) * s + b, s, 0, ak, guard=True, keep=True)


@effect('myth-fact', 'a MYTH card in red flips over to become the FACT in green')
def fx_myth_fact(c, e):
    U = c.U; myth = e.o.get('myth', 'You need an editor'); fact = e.o.get('fact', 'You need one prompt')
    cw, ch = U * 0.8, U * 0.3; pad = U * 0.05
    cx, cy, s, slot = clear_spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    t_flip = max(1.3, e.d * 0.48); ph = (c.lt - t_flip) / 0.36; front = ph < 0.5
    label, col, body = ('MYTH', ERR, myth) if front else ('FACT', OK, fact)
    def side():
        im = rrect(cw, ch, U * 0.04, PAPER + (252,)); d = ImageDraw.Draw(im)
        fl = font('bold', U * 0.042); lw_ = fl.getlength(label) + U * 0.05
        d.rounded_rectangle([pad, pad, pad + lw_, pad + U * 0.075], U * 0.016, fill=col + (255,))
        d.text((pad + lw_ / 2, pad + U * 0.0375), label, font=fl, fill=WHITE + (255,), anchor='mm')
        fb = font('bold', min(U * 0.068, (cw - pad * 2) / max(1, font('bold', 100).getlength(body)) * 100))
        d.text((pad, ch * 0.68), body, font=fb, fill=NAVY + (255,), anchor='lm')
        if front and c.lt > 0.7:
            k = ease_out((c.lt - 0.7) / 0.25); tw = fb.getlength(body)
            d.line([(pad, ch * 0.69), (pad + tw * k, ch * 0.675)], fill=ERR + (255,), width=max(4, int(U * 0.009)))
        return shadowed(im, 18, 8, 110)
    im = side(); sy = abs(math.cos(math.pi * clamp(ph))) if 0 < ph < 1 else 1.0
    if sy < 0.999: im = im.resize((im.width, max(2, int(im.height * max(0.04, sy)))), Image.BILINEAR)
    q = pop(c, 0.0, 0.32)
    place(c, im, cx, cy, s * (0.75 + 0.25 * q), 0, fade(c, e) * clamp(c.lt / 0.1), guard=True)


# ---------- pack 6: one format each (see "aspect" in effects.json) ----------
@effect('ticker', 'a news ticker slides up from the bottom and scrolls your headlines non-stop')
def fx_ticker(c, e):
    U = c.U; items = e.o.get('text', 'Claude can now edit your reels|No timeline needed|69 effects from one prompt').split('|'); tag = e.o.get('tag', 'LIVE')
    bh = int(U * 0.09); k = min(ease_out(c.lt / 0.3), ease_out((e.d - c.lt) / 0.25))  # slides, never fades
    y = c.H * float(e.o.get('y', 0.86 if c.H > c.W else 0.88)) + (1 - k) * (c.H * 0.16)
    strip = cached(e, 's', lambda: text_img('      •      '.join(items) + '      •      ', U * 0.042, 'uib', WHITE))
    ft = font('bold', U * 0.042); tw = int(ft.getlength(tag) + U * 0.07)
    bar = Image.new('RGBA', (c.W, bh), NAVY + (242,)); x = tw - int(c.lt * U * 0.2) % strip.width
    while x < c.W:
        bar.alpha_composite(strip, (x, int((bh - strip.height) / 2))); x += strip.width
    d = ImageDraw.Draw(bar); d.rectangle([0, 0, tw, bh], fill=ACC + (255,)); d.polygon([(tw, 0), (tw + bh * 0.3, 0), (tw, bh)], fill=ACC + (255,))
    if int(c.lt * 2) % 2 == 0: d.ellipse([U * 0.02, bh / 2 - U * 0.008, U * 0.036, bh / 2 + U * 0.008], fill=WHITE + (255,))
    d.text((U * 0.046, bh / 2), tag, font=ft, fill=WHITE + (255,), anchor='lm')
    d.rectangle([0, 0, c.W, max(2, int(U * 0.004))], fill=ACC_L + (255,))
    comp(c, bar, 0, y, guard=True)


@effect('reactions', 'live-stream reactions: hearts and emojis bubble up the side of the frame, swaying as they rise')
def fx_reactions(c, e):
    U = c.U; ems = e.o.get('emoji', '❤️|🔥|👏|😮').split('|'); N = int(e.o.get('count', 18))
    left = cached(e, 'side', lambda: c.fx > c.W * 0.55); base = U * 0.13 if left else c.W - U * 0.13
    for i in range(N):
        rnd = random.Random(i * 13 + 5); t0 = rnd.uniform(0, e.d * 0.75); life = rnd.uniform(1.5, 2.3); a = (c.lt - t0) / life
        if not 0 < a < 1: continue
        size = U * rnd.uniform(0.075, 0.115); ch = ems[i % len(ems)]
        im = emoji(ch, size) or heart(size, ACC_L)
        x = base + math.sin(a * 6.5 + rnd.uniform(0, 6)) * U * 0.045 + rnd.uniform(-1, 1) * U * 0.03
        y = c.H * 0.95 - (a ** 0.85) * c.H * 0.62
        place(c, im, x, y, clamp(ease_out(a / 0.12)), math.sin(a * 9 + i) * 12, clamp((1 - a) / 0.3), guard=True)


# ---------- pack 7: cards that fade in and stay put, no bounce (Nov 2026) ----------
def _card(c, e, im, cx, cy, s):
    place(c, shadowed(im, 16, 8, 110), cx, cy, s, 0, fade(c, e) * clamp(c.lt / 0.2))  # locked card stays whole, no face guard nibbling it


def _spot(c, e, w, h, order=('above', 'side', 'below'), min_s=0.75, floor=0.6):
    """clear_spot, picked once so the card never follows your head. Portrait: centred on the frame.
    Landscape: the biggest spot against the left or right edge that touches neither your head nor your body."""
    def pick():
        cx, cy, s, slot = clear_spot(c, e, w, h, order, min_s, floor=floor)
        m = min(c.W, c.H) * 0.035
        if c.H >= c.W: return (c.W / 2 if slot != 'side' else cx), cy, s, slot
        hx0, hx1, hy0, hy1 = c.fx - c.fw * 1.15, c.fx + c.fw * 1.15, c.fy - c.fw * 1.4, c.fy + c.fw * 1.6
        for sc in (1.0, 0.9, 0.8, 0.7, 0.62, 0.55, 0.48):  # ponytail: coarse grid search, fine enough for a locked card
            sw, sh = w * sc, h * sc; best = None
            if sh > c.H - 2 * m: continue
            for x0 in (c.W - m - sw, m):
                for y0 in np.linspace(m, c.H - m - sh, 14):
                    if x0 < hx1 + m and x0 + sw > hx0 - m and y0 < hy1 and y0 + sh > hy0: continue
                    a0, a1, b0, b1 = int(max(0, y0 - m)), int(min(c.H, y0 + sh + m)), int(max(0, x0 - m)), int(min(c.W, x0 + sw + m))
                    if c.m[a0:a1, b0:b1].mean() > 0.01: continue
                    score = abs(y0 + sh / 2 - c.fy)
                    if best is None or score < best[0]: best = (score, x0 + sw / 2, y0 + sh / 2)
            if best: return best[1], best[2], sc, 'side'
        return cx, cy, s, slot
    return cached(e, 'lock', pick)


def _fit(kind, text, size, max_w): return font(kind, min(size, max_w / max(1, font(kind, 100).getlength(text)) * 100))


@effect('stat-row', 'three numbers count up side by side on one card, each with its label')
def fx_stat_row(c, e):
    U = c.U; items = [(x.split('::') + [''])[:2] for x in e.o.get('text', '3.2M::views|48K::followers|12::clients').split('|')][:3]
    n = len(items); cw, ch = U * 0.9, U * 0.24; col = cw / n
    cx, cy, s, slot = _spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.04, NAVY + (240,)); d = ImageDraw.Draw(im)
    for i, (val, lab) in enumerate(items):
        num, suf, dec = split_num(val); t0 = 0.2 + 0.25 * i; p = clamp((c.lt - t0) / 0.9); a = int(255 * clamp((c.lt - t0) / 0.2)); x = col * (i + 0.5)
        if i: d.line([(col * i, ch * 0.22), (col * i, ch * 0.78)], fill=(62, 62, 80, 255), width=max(2, int(U * 0.003)))
        d.text((x, ch * 0.42), f'{num * p:.{dec}f}{suf}', font=_fit('bold', val, ch * 0.42, col * 0.8), fill=WHITE + (a,), anchor='mm')
        d.text((x, ch * 0.75), lab.upper(), font=_fit('uib', lab.upper(), ch * 0.115, col * 0.84), fill=ACC_L + (a,), anchor='mm')
    _card(c, e, im, cx, cy, s)


@effect('chat-reply', 'your prompt goes up as a chat bubble, the AI thinks for a beat, then its answer streams in underneath')
def fx_chat_reply(c, e):
    U = c.U; q = e.o.get('text', 'Turn this video into 5 reels'); who = e.o.get('model', 'Claude')
    ans = e.o.get('reply', 'Done. I cut the pauses, added captions and picked your 5 strongest hooks.')
    cw = U * 0.86; f = font('ui', U * 0.04); lh = U * 0.054; pad = U * 0.032; bw = cw * 0.84; lab = U * 0.05; gap = U * 0.025
    ql = cached(e, 'q', lambda: _wrap(q, f, bw - 2 * pad)[:2]); al = cached(e, 'a', lambda: _wrap(ans, f, bw - 2 * pad)[:4])
    qh = lh * len(ql) + 2 * pad; ah = lab + lh * len(al) + 2 * pad; ch = qh + gap + ah
    cx, cy, s, slot = _spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    im = Image.new('RGBA', (int(cw), int(ch)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = U * 0.04
    k1 = clamp((c.lt - 0.1) / 0.2)
    if k1 > 0:
        qw = max(f.getlength(l) for l in ql) + 2 * pad; x0 = cw - qw; y0 = 0; A = int(255 * k1)
        d.rounded_rectangle([x0, y0, cw, y0 + qh], r, fill=ACC + (A,))
        for j, l in enumerate(ql): d.text((x0 + pad, y0 + pad + lh * (j + 0.5)), l, font=f, fill=WHITE + (A,), anchor='lm')
    t1, t2 = 0.75, 1.5; y0 = qh + gap
    if t1 < c.lt <= t2:
        A = int(255 * clamp((c.lt - t1) / 0.15)); d.rounded_rectangle([0, y0, U * 0.2, y0 + lh + pad], r, fill=PAPER + (A,))
        for i in range(3):
            g = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(c.lt * 9 - i * 1.1)); x = U * 0.055 + i * U * 0.045; yy = y0 + (lh + pad) / 2; rr = U * 0.012
            d.ellipse([x - rr, yy - rr, x + rr, yy + rr], fill=MUTE + (int(A * g),))
    elif c.lt > t2:
        words = sum(len(l.split(' ')) for l in al); nshow = int(clamp((c.lt - t2) / min(max(0.6, e.d - t2 - 0.9), 0.09 * words)) * words) + 1; seen = 0
        d.rounded_rectangle([0, y0, bw, y0 + ah], r, fill=PAPER + (250,))
        d.text((pad, y0 + pad + lab * 0.3), who, font=font('uib', U * 0.032), fill=ACC + (255,), anchor='lm')
        for j, l in enumerate(al):
            ws = l.split(' '); take = max(0, min(len(ws), nshow - seen)); seen += len(ws)
            if take: d.text((pad, y0 + pad + lab + lh * (j + 0.5)), ' '.join(ws[:take]), font=f, fill=NAVY + (255,), anchor='lm')
    place(c, shadowed(im, 14, 6, 100), cx, cy, s, 0, fade(c, e))


@effect('numbered-list', 'a titled list that reveals one numbered point at a time, the current one lit and the earlier ones dimmed')
def fx_numbered_list(c, e):
    U = c.U; title = e.o.get('title', '3 reasons to switch'); items = e.o.get('text', 'It is faster|It is cheaper|It sounds like you').split('|')[:5]
    n = len(items); cw = U * 0.8; rh = U * 0.1; pad = U * 0.045; th = U * 0.085; ch = pad * 2 + th + rh * n
    cx, cy, s, slot = _spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.6)
    step = min(0.9, max(0.3, (e.d - 1.2) / n)); cur = min(n - 1, int(max(0, c.lt - 0.4) / step))
    im = rrect(cw, ch, U * 0.04, NAVY + (240,)); d = ImageDraw.Draw(im)
    d.text((pad, pad + th * 0.35), title.upper(), font=_fit('uib', title.upper(), U * 0.036, cw - pad * 2), fill=ACC_L + (255,), anchor='lm')
    for i, it in enumerate(items):
        k = clamp((c.lt - 0.4 - step * i) / 0.2)
        if k <= 0: continue
        dim = 1.0 if i == cur else 0.5; A = int(255 * k * dim); y = pad + th + rh * (i + 0.5); q = rh * 0.3; x = pad + q
        d.rounded_rectangle([x - q, y - q, x + q, y + q], q * 0.45, fill=ACC + (A,))
        d.text((x, y), str(i + 1), font=font('bold', q * 1.2), fill=WHITE + (A,), anchor='mm')
        d.text((x + q * 1.8, y), it, font=_fit('bold', it, U * 0.05, cw - pad * 2 - q * 2.8), fill=WHITE + (A,), anchor='lm')
    _card(c, e, im, cx, cy, s)


# ---------- pack 8: eased cards, locked in place (Nov 2026) ----------
def _k(c, t0, dur=0.45): return ease_out((c.lt - t0) / dur)  # 0..1, decelerating, never overshoots
def _over(im): return Image.new('RGBA', im.size, (0, 0, 0, 0))  # animated parts go here, so a fade never punches a hole in the card
def _mix(a, b, k): return tuple(int(a[j] * (1 - k) + b[j] * k) for j in range(3))


def _enter(c, e, im, cx, cy, s, dim=1.0, t0=0.0):
    k = _k(c, t0, 0.5); a = ease_inout((c.lt - t0) / 0.4) * ease_inout((e.d - c.lt) / 0.35) * dim
    place(c, shadowed(im, 16, 8, 110), cx, cy + (1 - k) * c.U * 0.022 * s, s * (0.97 + 0.03 * k), 0, a)


def _mark(d, x, y, r, yes, k, A=255):
    """A green tick or red cross disc whose stroke draws itself on as k goes 0..1."""
    d.ellipse([x - r, y - r, x + r, y + r], fill=(OK if yes else ERR) + (A,)); w = max(2, int(r / 3.5)); col = WHITE + (A,)
    if yes:
        a, b, cc = (x - r * 0.5, y + r * 0.05), (x - r * 0.14, y + r * 0.4), (x + r * 0.5, y - r * 0.35)
        pts = [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for u in np.linspace(0, 1, 8)] + [(b[0] + (cc[0] - b[0]) * u, b[1] + (cc[1] - b[1]) * u) for u in np.linspace(0, 1, 16)][1:]
        hand_path(d, pts, col, w, k)
    else:
        q = r * 0.38
        for (x0, y0, x1, y1), kk in (((x - q, y - q, x + q, y + q), clamp(k * 2)), ((x + q, y - q, x - q, y + q), clamp(k * 2 - 1))):
            if kk > 0: d.line([(x0, y0), (x0 + (x1 - x0) * kk, y0 + (y1 - y0) * kk)], fill=col, width=w)


@effect('post-card', 'a social post card with your face, name and handle: the post writes itself, then the likes count up')
def fx_post_card(c, e):
    U = c.U; text = e.o.get('text', 'I stopped editing my own videos 3 months ago. My views doubled.'); likes = str(e.o.get('likes', '12.4K'))
    name = e.o.get('name', 'Matt Penny'); handle = e.o.get('handle', '@matt_penny_applied_ai')
    cw = U * 0.86; pad = U * 0.045; f = font('ui', U * 0.044); lh = U * 0.06; hh = U * 0.13; fh = U * 0.085
    lines = cached(e, 'ln', lambda: _wrap(text, f, cw - pad * 2)[:4]); ch = pad * 2 + hh + lh * len(lines) + fh
    cx, cy, s, slot = _spot(c, e, cw, ch, ('below', 'side'), 0.75, floor=0.6)
    av = face_chip(c, e, hh * 0.82)
    im = rrect(cw, ch, U * 0.04, PAPER + (252,)); d = ImageDraw.Draw(im); im.alpha_composite(av, (int(pad), int(pad)))
    tx = pad + hh * 0.82 + pad * 0.6
    d.text((tx, pad + hh * 0.26), name, font=font('bold', U * 0.042), fill=NAVY + (255,), anchor='lm')
    d.text((tx, pad + hh * 0.6), handle, font=_fit('ui', handle, U * 0.032, cw - tx - pad), fill=MUTE + (255,), anchor='lm')
    d.line([(pad, ch - pad - fh * 0.85), (cw - pad, ch - pad - fh * 0.85)], fill=ACC_LL + (255,), width=max(1, int(U * 0.003)))
    ov = _over(im); od = ImageDraw.Draw(ov); n = sum(len(l.split(' ')) for l in lines); step = min(0.1, 1.5 / n); i = 0; sp = f.getlength(' ')
    for j, l in enumerate(lines):
        x = pad
        for wd in l.split(' '):
            k = _k(c, 0.45 + step * i, 0.35); i += 1
            if k > 0: od.text((x, pad + hh + lh * (j + 0.5) + (1 - k) * U * 0.012), wd, font=f, fill=NAVY + (int(255 * k),), anchor='lm')
            x += f.getlength(wd) + sp
    t_done = 0.45 + step * n + 0.2; p = _k(c, t_done, 1.1); y = ch - pad - fh * 0.35; hs = int(fh * 0.5)
    num, suf, dec = split_num(likes); im.alpha_composite(ov)
    im.alpha_composite(heart(hs, _mix((196, 196, 214), ACC, clamp(p * 4))), (int(pad), int(y - hs / 2)))
    d.text((pad + hs * 1.4, y), f'{num * p:.{dec}f}{suf}', font=font('uib', U * 0.036), fill=_mix((148, 148, 184), NAVY, clamp(p * 4)) + (255,), anchor='lm')
    _enter(c, e, im, cx, cy, s)


@effect('bar-chart', 'a bar chart: your bars grow one after another, each with its value, the last one in purple')
def fx_bar_chart(c, e):
    U = c.U; title = e.o.get('title', 'Views per month'); items = [(x.split('::') + ['0'])[:2] for x in e.o.get('text', 'Jan::12K|Feb::18K|Mar::31K|Apr::64K').split('|')][:6]
    n = len(items); cw, ch = U * 0.8, U * 0.56; pad = U * 0.05
    cx, cy, s, slot = _spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.04, NAVY + (240,)); d = ImageDraw.Draw(im); ov = _over(im); od = ImageDraw.Draw(ov)
    d.text((pad, pad + U * 0.012), title.upper(), font=_fit('uib', title.upper(), U * 0.034, cw - pad * 2), fill=ACC_L + (255,), anchor='lm')
    top, base = pad + U * 0.13, ch - pad - U * 0.055; colw = (cw - pad * 2) / n; bw = colw * 0.6; mx = max(split_num(v)[0] for _, v in items) or 1
    for g in range(4): d.line([(pad, base - (base - top) * g / 3), (cw - pad, base - (base - top) * g / 3)], fill=(67, 67, 84, 255) if g == 0 else (42, 42, 62, 255), width=max(1, int(U * 0.003)))
    for i, (lab, val) in enumerate(items):
        x = pad + colw * (i + 0.5); t0 = 0.4 + 0.16 * i; k = _k(c, t0, 0.9); num, suf, dec = split_num(val); h = (base - top) * num / mx * k; last = i == n - 1
        la = _k(c, t0 - 0.1, 0.4)
        if la > 0: od.text((x, base + U * 0.032), lab, font=_fit('ui', lab, U * 0.032, colw * 0.95), fill=(200, 200, 225, int(255 * la)), anchor='mm')
        if h > 1: od.rounded_rectangle([x - bw / 2, base - h, x + bw / 2, base], min(bw * 0.18, h / 2), fill=(ACC if last else (98, 98, 140)) + (255,))
        if la > 0: od.text((x, base - h - U * 0.03), f'{num * k:.{dec}f}{suf}', font=_fit('bold', val, U * 0.038, colw * 0.98), fill=WHITE + (int(255 * la),), anchor='mm')
    im.alpha_composite(ov); _enter(c, e, im, cx, cy, s)


@effect('do-dont', 'two stacked cards: the DON\'T with a red cross, then the DO with a green tick, and the DON\'T fades back')
def fx_do_dont(c, e):
    U = c.U; dont = e.o.get('dont', 'Post and hope for the best'); do = e.o.get('do', 'Open with a hook and end on a CTA')
    cw, rh, gap = U * 0.86, U * 0.19, U * 0.025; pad = U * 0.04; r = rh * 0.24
    cx, cy, s, slot = _spot(c, e, cw, rh * 2 + gap, ('below', 'side'), 0.75, floor=0.6)
    t2 = float(e.o.get('at', max(1.2, e.d * 0.42)))
    def row(key, head, col, text, yes, t0):
        def make():
            im = rrect(cw, rh, U * 0.035, PAPER + (252,)); d = ImageDraw.Draw(im); tx = pad + r * 2 + pad * 0.8
            d.text((tx, rh * 0.3), head, font=font('uib', U * 0.03), fill=col + (255,), anchor='lm')
            d.text((tx, rh * 0.62), text, font=_fit('bold', text, U * 0.046, cw - tx - pad), fill=NAVY + (255,), anchor='lm')
            return im
        im = cached(e, key, make).copy(); _mark(ImageDraw.Draw(im), pad + r, rh / 2, r, yes, ease_inout((c.lt - t0 - 0.25) / 0.45)); return im
    off = (rh + gap) / 2 * s
    _enter(c, e, row('a', "DON'T", ERR, dont, False, 0.0), cx, cy - off, s, dim=1 - 0.5 * ease_inout((c.lt - t2) / 0.5))
    if c.lt > t2: _enter(c, e, row('b', 'DO', OK, do, True, t2), cx, cy + off, s, t0=t2)


def _star5(d, cx, cy, r, fill):
    d.polygon([(cx + (r if i % 2 == 0 else r * 0.42) * math.sin(i * math.pi / 5), cy - (r if i % 2 == 0 else r * 0.42) * math.cos(i * math.pi / 5)) for i in range(10)], fill=fill)


@effect('rating-stars', 'a review card: five stars light up one after another as the score counts up, with the number of reviews underneath')
def fx_rating_stars(c, e):
    U = c.U; to = float(e.o.get('to', 4.9)); lab = e.o.get('text', 'from 212 members')
    cw, ch = U * 0.7, U * 0.36; r = U * 0.05; gapx = U * 0.118; sw, sh = int(gapx * 5), int(r * 2.2)
    cx, cy, s, slot = _spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.04, NAVY + (240,)); d = ImageDraw.Draw(im); x0, y0 = int((cw - sw) / 2), int(ch * 0.12)
    off = Image.new('RGBA', (sw, sh), (0, 0, 0, 0)); on = off.copy(); do_, dn = ImageDraw.Draw(off), ImageDraw.Draw(on)
    for i in range(5):
        _star5(do_, gapx * (i + 0.5), r * 1.1, r, (255, 255, 255, 46)); k = _k(c, 0.4 + 0.16 * i, 0.5)
        if k > 0: _star5(dn, gapx * (i + 0.5), r * 1.1, r * (0.82 + 0.18 * k), ACC_L + (int(255 * k),))
    im.alpha_composite(off, (x0, y0)); im.alpha_composite(on.crop((0, 0, max(1, int(sw * to / 5)), sh)), (x0, y0))
    p = _k(c, 0.4, 1.3); la = _k(c, 0.9, 0.5); ov = _over(im); od = ImageDraw.Draw(ov)
    d.text((cw / 2, ch * 0.58), f'{to * p:.1f}', font=font('bold', ch * 0.3), fill=WHITE + (255,), anchor='mm')
    od.text((cw / 2, ch * 0.84), lab.upper(), font=_fit('uib', lab.upper(), U * 0.032, cw * 0.86), fill=ACC_L + (int(255 * la),), anchor='mm')
    im.alpha_composite(ov); _enter(c, e, im, cx, cy, s)


@effect('plan-card', 'a pricing card: the plan name, the price, what is included ticking in line by line, and a button')
def fx_plan_card(c, e):
    U = c.U; name = e.o.get('name', 'Mastermind'); price = e.o.get('price', '£97'); per = e.o.get('per', '/month'); cta = e.o.get('cta', 'Join now')
    feats = e.o.get('text', 'Weekly live calls|Every template|Private community').split('|')[:5]
    cw = U * 0.66; pad = U * 0.05; rh = U * 0.07; top = U * 0.25; bh = U * 0.09; ch = pad * 2 + top + rh * len(feats) + bh + pad * 0.5
    cx, cy, s, slot = _spot(c, e, cw, ch, ('side', 'below'), 0.75, floor=0.6)
    im = rrect(cw, ch, U * 0.045, PAPER + (252,)); d = ImageDraw.Draw(im); ov = _over(im); od = ImageDraw.Draw(ov)
    d.text((pad, pad + U * 0.02), name.upper(), font=_fit('uib', name.upper(), U * 0.034, cw - pad * 2), fill=ACC + (255,), anchor='lm')
    fp = font('bold', U * 0.13); d.text((pad, pad + U * 0.13), price, font=fp, fill=NAVY + (255,), anchor='lm')
    d.text((pad + fp.getlength(price) + U * 0.012, pad + U * 0.155), per, font=font('ui', U * 0.036), fill=MUTE + (255,), anchor='lm')
    for i, ft in enumerate(feats):
        t0 = 0.55 + 0.32 * i; k = _k(c, t0, 0.45)
        if k <= 0: continue
        y = pad + top + rh * (i + 0.5); r = rh * 0.28; A = int(255 * k); w = max(2, int(r / 3.5))
        od.ellipse([pad, y - r, pad + 2 * r, y + r], fill=ACC + (A,)); a, b, cc = (pad + r * 0.5, y + r * 0.05), (pad + r * 0.86, y + r * 0.4), (pad + r * 1.5, y - r * 0.35)
        pts = [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for u in np.linspace(0, 1, 8)] + [(b[0] + (cc[0] - b[0]) * u, b[1] + (cc[1] - b[1]) * u) for u in np.linspace(0, 1, 16)][1:]
        hand_path(od, pts, WHITE + (A,), w, ease_inout((c.lt - t0 - 0.12) / 0.4))
        od.text((pad + r * 3 + (1 - k) * U * 0.018, y), ft, font=_fit('ui', ft, U * 0.038, cw - pad * 2 - r * 3), fill=NAVY + (A,), anchor='lm')
    lit = ease_inout((c.lt - 0.75 - 0.32 * len(feats)) / 0.6)
    d.rounded_rectangle([pad, ch - pad - bh, cw - pad, ch - pad], bh / 2, fill=_mix(ACC_LL, ACC, lit) + (255,))
    d.text((cw / 2, ch - pad - bh / 2), cta, font=font('bold', U * 0.042), fill=_mix(ACC, WHITE, lit) + (255,), anchor='mm')
    im.alpha_composite(ov); _enter(c, e, im, cx, cy, s)


# ---------- pack 9: camera moves, depth and 3D panels, after the HyperFrames templates (Nov 2026) ----------
import re


DIM, GREY, SOFT = (200, 200, 225), (148, 148, 184), (243, 240, 255)


def _cnt(s, p):
    """'£7,200' at p=0.5 -> '£3,600': counts the number inside a value, keeping its prefix, suffix and commas."""
    m = re.match(r'([^\d]*)([\d.,]*\d)(.*)', str(s))
    if not m: return str(s)
    raw = m.group(2); n = raw.replace(',', ''); dec = len(n.split('.')[1]) if '.' in n else 0
    return m.group(1) + (f'{float(n) * p:,.{dec}f}' if ',' in raw else f'{float(n) * p:.{dec}f}') + m.group(3)


def _val(s):
    m = re.search(r'[\d.,]*\d', str(s)); return float(m.group(0).replace(',', '')) if m else 0.0


def _t(od, x, y, text, f, col, k, anchor='lm', dy=0):
    if k > 0: od.text((x, y + (1 - k) * dy), text, font=f, fill=tuple(col[:3]) + (int(255 * k),), anchor=anchor)


def _tickpts(x, y, r):
    a, b, cc = (x - r * 0.5, y + r * 0.05), (x - r * 0.14, y + r * 0.4), (x + r * 0.5, y - r * 0.35)
    return [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for u in np.linspace(0, 1, 8)] + [(b[0] + (cc[0] - b[0]) * u, b[1] + (cc[1] - b[1]) * u) for u in np.linspace(0, 1, 16)][1:]


def _pairs(e, key, default, n): return [(x.split('::') + [''])[:2] for x in e.o.get(key, default).split('|')][:n]


DEEP = (76, 29, 149)


def _io(c, e, tin=0.45, tout=0.4): return min(ease_inout(c.lt / tin), ease_inout((e.d - c.lt) / tout))


def _cio(c, e, t0=0.45): return min(ease_inout((c.lt - t0) / 0.4), ease_inout((e.d - 0.3 - c.lt) / 0.3))  # content inside a camera move


def _f0(c, e): return cached(e, 'f0', lambda: (float(c.fx), float(c.fy), float(c.fw)))  # where you were at the start


def _lay(c): return Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0))


def _al(im, k):
    if k >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * max(0.0, k)))); return im


def _quad(cx, cy, w, h, yaw=0.0, pitch=0.0, f=None, ox=0.0, oz=0.0):
    """Corners (TL, TR, BR, BL) of a w x h panel turned in 3D and seen in perspective."""
    f = f or max(w, h) * 2.4; cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)); out = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        X = x * cy_ + ox; Z = x * sy_ + oz; Y = y * cp - Z * sp; Z = y * sp + Z * cp; q = f / (f + Z); out.append((cx + X * q, cy + Y * q))
    return out


def _p3(c, im, quad, alpha=1.0, shade=0.0, **kw):
    a = to_np(im) if isinstance(im, Image.Image) else im; h, w = a.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    out = cv2.warpPerspective(a, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if shade: out[..., :3] *= (1 - shade)
    comp(c, out, 0, 0, alpha, **kw)


_dg = {}


def _dots(w, h, U, r=0.04, sheet=False):
    """The off-white dot-grid paper from the templates, as a rounded card (or a square-cornered sheet)."""
    k = (int(w), int(h), int(U), sheet)
    if k not in _dg:
        im = Image.new('RGBA', (int(w), int(h)), (245, 245, 243, 255)) if sheet else rrect(w, h, U * r, (245, 245, 243, 255)); d = ImageDraw.Draw(im); sp = U * 0.042; q = max(1.0, U * 0.0032); y = sp / 2
        while y < h:
            x = sp / 2
            while x < w: d.ellipse([x - q, y - q, x + q, y + q], fill=(196, 196, 204, 255)); x += sp
            y += sp
        if not sheet: m = rrect(w, h, U * r, (255, 255, 255, 255)).getchannel('A'); im.putalpha(m)
        _dg[k] = im
    return _dg[k].copy()


def _icon(d, name, x, y, s, col):
    """A small flat icon centred on (x, y), about 2s across."""
    w = max(2, int(s * 0.22)); col = tuple(col)
    if name == 'bolt': d.polygon([(x + s * 0.15, y - s), (x - s * 0.6, y + s * 0.15), (x - s * 0.05, y + s * 0.15), (x - s * 0.2, y + s), (x + s * 0.6, y - s * 0.2), (x + s * 0.05, y - s * 0.2)], fill=col)
    elif name == 'clock': d.ellipse([x - s, y - s, x + s, y + s], outline=col, width=w); d.line([(x, y - s * 0.55), (x, y), (x + s * 0.4, y + s * 0.25)], fill=col, width=w, joint='curve')
    elif name == 'chart':
        for i, hh in enumerate((0.5, 0.95, 1.5)): d.rounded_rectangle([x - s * 0.85 + i * s * 0.62, y + s * 0.75 - s * hh, x - s * 0.85 + i * s * 0.62 + s * 0.46, y + s * 0.75], s * 0.1, fill=col)
    elif name == 'play': d.polygon([(x - s * 0.6, y - s * 0.85), (x + s * 0.85, y), (x - s * 0.6, y + s * 0.85)], fill=col)
    elif name == 'chat': d.rounded_rectangle([x - s, y - s * 0.8, x + s, y + s * 0.5], s * 0.35, fill=col); d.polygon([(x - s * 0.5, y + s * 0.4), (x - s * 0.7, y + s), (x + s * 0.1, y + s * 0.45)], fill=col)
    elif name == 'user': d.ellipse([x - s * 0.42, y - s * 0.9, x + s * 0.42, y - s * 0.06], fill=col); d.pieslice([x - s * 0.9, y + s * 0.1, x + s * 0.9, y + s * 1.9], 180, 360, fill=col)
    elif name == 'doc':
        d.rounded_rectangle([x - s * 0.7, y - s, x + s * 0.7, y + s], s * 0.18, outline=col, width=w)
        for j in range(3): d.line([(x - s * 0.35, y - s * 0.45 + j * s * 0.45), (x + s * 0.35, y - s * 0.45 + j * s * 0.45)], fill=col, width=w)
    elif name == 'tick': d.line([(x - s * 0.7, y + s * 0.05), (x - s * 0.2, y + s * 0.55), (x + s * 0.75, y - s * 0.5)], fill=col, width=int(w * 1.3), joint='curve')
    elif name == 'cross': d.line([(x - s * 0.6, y - s * 0.6), (x + s * 0.6, y + s * 0.6)], fill=col, width=int(w * 1.3)); d.line([(x + s * 0.6, y - s * 0.6), (x - s * 0.6, y + s * 0.6)], fill=col, width=int(w * 1.3))
    else: d.polygon([(x, y - s), (x + s * 0.24, y - s * 0.24), (x + s, y), (x + s * 0.24, y + s * 0.24), (x, y + s), (x - s * 0.24, y + s * 0.24), (x - s, y), (x - s * 0.24, y - s * 0.24)], fill=col)  # spark


_pl = {}


def _pill(text, size, bg=PAPER, fg=NAVY, dot=None, kind='bold'):
    k = (text, int(size), bg, fg, dot, kind)
    if k not in _pl:
        f = font(kind, size); h = size * 2.1; dw = size * 1.1 if dot else 0; w = f.getlength(text) + size * 1.7 + dw; im = rrect(w, h, h / 2, tuple(bg) + (252,)); d = ImageDraw.Draw(im)
        if dot: d.ellipse([size * 0.75, h / 2 - size * 0.32, size * 1.39, h / 2 + size * 0.32], fill=tuple(dot) + (255,))
        d.text((size * 0.85 + dw, h / 2), text, font=f, fill=tuple(fg) + (255,), anchor='lm'); _pl[k] = shadowed(im, 12, 5, 100)
    return _pl[k]


def _stage(c, e, z=1.35):
    """Push the camera in and move you aside. Returns (how far in 0..1, the free space as cx, cy, w, h)."""
    fx0, fy0, fw0 = _f0(c, e); k = _io(c, e, 0.6, 0.5); wide = c.W > c.H; left = fx0 <= c.W * 0.55
    if wide: tx = fx0 + (c.W / z) * (0.22 if left else -0.22); ty = fy0 + (c.H / z) * 0.1
    else: tx = fx0; ty = fy0 + (c.H / z) * 0.22
    camera(c, 1 + (z - 1) * k, c.W / 2 + (tx - c.W / 2) * k, c.H / 2 + (ty - c.H / 2) * k)
    return k, ((c.W * (0.74 if left else 0.26), c.H * 0.5, c.W * 0.42, c.H * 0.7) if wide else (c.W / 2, c.H * 0.75, c.W * 0.88, c.H * 0.36))


@effect('zoom-stat', 'the camera pushes in and moves you to one side, and a stat badge counts up in the space it opened')
def fx_zoom_stat(c, e):
    U = c.U; to = str(e.o.get('to', '143%')); lab = e.o.get('text', 'more watch time'); k, (rx, ry, rw, rh) = _stage(c, e)
    cw, ch = U * 0.56, U * 0.4; im = _dots(cw, ch, U); d = ImageDraw.Draw(im)
    d.text((cw / 2, ch * 0.42), _cnt(to, _k(c, 0.6, 1.4)), font=_fit('bold', to, U * 0.2, cw * 0.84), fill=NAVY + (255,), anchor='mm')
    fl = _fit('uib', lab.upper(), U * 0.032, cw * 0.74); pw = fl.getlength(lab.upper()) + U * 0.06
    d.rounded_rectangle([(cw - pw) / 2, ch * 0.72, (cw + pw) / 2, ch * 0.72 + U * 0.07], U * 0.035, fill=ACC + (255,))
    d.text((cw / 2, ch * 0.72 + U * 0.035), lab.upper(), font=fl, fill=WHITE + (255,), anchor='mm')
    place(c, shadowed(im, 16, 8, 110), rx, ry, min(1, rw / cw, rh / ch), 0, _cio(c, e))


@effect('zoom-bullets', 'the camera pushes in and moves you aside, then a headline and three points appear one by one in the space')
def fx_zoom_bullets(c, e):
    U = c.U; title = e.o.get('title', 'Why it works'); pts = e.o.get('text', 'Hook in three seconds|One idea per video|A clear next step').split('|')[:4]
    k, (rx, ry, rw, rh) = _stage(c, e); a = _cio(c, e); s = min(1.0, rw / (U * 0.66)); x0 = rx - rw / 2 + (rw - U * 0.66 * s) / 2; lh = U * 0.085 * s
    ti = cached(e, 't', lambda: fit_text(title, U * 0.66 * s, 'bold', start=int(U * 0.085 * s), fill=WHITE, shadow=8))
    ims = cached(e, 'p', lambda: [fit_text(p, U * 0.58 * s, 'uib', start=int(U * 0.05 * s), fill=WHITE, shadow=7) for p in pts])
    y = ry - (ti.height + lh * len(pts)) / 2; comp(c, ti, x0, y, a * _k(c, 0.55, 0.5)); y += ti.height * 0.95
    for i, im in enumerate(ims):
        ki = _k(c, 0.85 + 0.3 * i, 0.5); r = U * 0.014 * s; cy = y + lh * (i + 0.5); dx = (1 - ki) * U * 0.025
        if ki > 0: comp(c, rrect(r * 2, r * 2, r, ACC_L + (255,)), x0 + U * 0.02 * s + dx, cy - r, a * ki); comp(c, im, x0 + U * 0.055 * s + dx, cy - im.height / 2, a * ki)


@effect('chest-number', 'one giant number counts up across your chest in front of you, with a big label under it')
def fx_chest_number(c, e):
    U = c.U; to = str(e.o.get('to', '1,000,000')); lab = e.o.get('text', 'views in 30 days'); fx0, fy0, fw0 = _f0(c, e); a = _io(c, e); m = min(c.W, c.H) * 0.04
    def size():
        S = int(U * 0.5)
        while S > 20 and font('bold', S).getlength(to) > min(c.W * 0.9, U * 1.15): S = int(S * 0.94)
        return S
    S = cached(e, 'S', size); im = text_img(_cnt(to, _k(c, 0.2, 1.7)), S, 'bold', WHITE, shadow=12); pill = _pill(lab.upper(), U * 0.05, ACC, WHITE, kind='uib')
    k = _k(c, 0.0, 0.6); x = c.W / 2
    if c.W > c.H:  # landscape: the biggest clear spot beside you
        x, cy, sc, _ = _spot(c, e, font('bold', S).getlength(to) * 1.05, S * 1.1 + pill.height * 1.3, ('side', 'below'), 0.75, floor=0.6); y = cy - pill.height * 0.6 * sc
    else: top = fy0 + fw0 * 1.6; sc = float(clamp((c.H - m - pill.height * 1.25 - top) / (S * 1.05), 0.35, 1)); y = top + S * sc * 0.52  # portrait: under your chin
    place(c, im, x, y + (1 - k) * U * 0.03, sc, 0, a * k)
    place(c, pill, x, y + S * sc * 0.62 + pill.height * 0.4 * min(1, sc * 1.4), min(1, sc * 1.4), 0, a * _k(c, 0.6, 0.5), keep=True)


def _slab(c, e, key, face, cx, cy, w, h, yaw, pitch, depth, edge, alpha, **kw):
    """A panel with real thickness: its extruded side first, then the face, all in perspective."""
    def side():
        s_ = Image.new('RGBA', face.size, tuple(edge) + (255,)); s_.putalpha(face.getchannel('A')); return s_
    sd = cached(e, key, side); n = 7
    for j in range(n, 0, -1): _p3(c, sd, _quad(cx, cy, w, h, yaw, pitch, oz=depth * j / n), alpha, shade=0.25 * j / n, **kw)
    _p3(c, face, _quad(cx, cy, w, h, yaw, pitch), alpha, **kw)


def _etile(ch, q, bg=PAPER):
    """A rounded tile carrying a colour emoji (a drawn spark where the emoji font is missing)."""
    im = rrect(q, q, q * 0.24, tuple(bg) + (255,)); d = ImageDraw.Draw(im); d.rounded_rectangle([1, 1, q - 2, q - 2], q * 0.24, outline=ACC_LL + (255,), width=max(2, int(q * 0.025))); em = emoji(ch, q * 0.56)
    if em is None: _icon(d, 'spark', q / 2, q / 2, q * 0.26, ACC + (255,))
    else: im.alpha_composite(em, (int((q - em.width) / 2), int((q - em.height) / 2)))
    return im


@effect('behind-icons-path', 'two thick 3D emoji tiles sit behind your shoulders and a dotted path draws over your head from one to the other')
def fx_behind_icons_path(c, e):
    U = c.U; ia, ib = (e.o.get('emoji', '💡|🎬').split('|') + ['✨'])[:2]; la, lb = (e.o.get('text', 'Idea|Reel').split('|') + [''])[:2]
    fx0, fy0, fw0 = _f0(c, e); a = _io(c, e); q = U * 0.26; m = min(c.W, c.H) * 0.04
    ax = max(m + q * 0.6, fx0 - fw0 * 1.55 - q * 0.25); bx = min(c.W - m - q * 0.6, fx0 + fw0 * 1.55 + q * 0.25); y = max(m + q * 0.8, fy0 - fw0 * 0.55)
    lay = _lay(c); d = ImageDraw.Draw(lay); pts = arrow_pts(ax, y - q * 0.66, bx, y - q * 0.66, bend=-0.42, n=34); n = int(len(pts) * ease_inout((c.lt - 0.7) / 1.1)); r = U * 0.009
    for px, py in pts[1:n:2]: d.ellipse([px - r, max(r, py) - r, px + r, max(r, py) + r], fill=WHITE + (255,))
    comp(c, lay, 0, 0, a, behind=True)
    for i, (x, ch, lb_) in enumerate(((ax, ia, la), (bx, ib, lb))):
        k = _k(c, 0.2 + 1.5 * i, 0.6); face = cached(e, f'face{i}', lambda ch=ch: _etile(ch, int(q)))
        _slab(c, e, f's{i}', face, x, y + (1 - k) * U * 0.03, q, q, (40 - 6 * k) * (1 if i == 0 else -1), 8, q * 0.34, ACC, a * k, behind=True)
        place(c, cached(e, f'l{i}', lambda lb_=lb_: text_img(lb_, U * 0.045, 'bold', WHITE, shadow=8)), x, y + q * 0.78, 1, 0, a * k, behind=True)


def _spline(xs, ys, n=28):
    """A smooth curve through the points (Catmull-Rom)."""
    P = list(zip(xs, ys)); P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for u in np.linspace(0, 1, n, endpoint=False):
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u * u + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u ** 3) for k in (0, 1)))
    return out + [P[-2]]


def _linepanel(c, e, w, h, U, title, items):
    """The graph panel, drawn at twice the size and scaled down so the curve stays smooth."""
    S = 2; w, h = int(w * S), int(h * S); r = U * 0.035 * S; pad = w * 0.07
    def base_():
        im = rrect(w, h, r, DEEP + (245,)); d = ImageDraw.Draw(im); d.rounded_rectangle([2, 2, w - 3, h - 3], r, outline=ACC_L + (255,), width=max(2, int(U * 0.005 * S)))
        d.text((pad, pad * 1.1), title.upper(), font=font('uib', w * 0.055), fill=ACC_LL + (255,), anchor='lm')
        for g in range(4): yy = h * 0.86 - (h * 0.56) * g / 3; d.line([(pad, yy), (w - pad, yy)], fill=(140, 110, 210, 255) if g == 0 else (104, 62, 180, 255), width=max(2, int(U * 0.003 * S)))
        return im
    im = cached(e, 'pb', base_).copy(); top, base = h * 0.3, h * 0.86; n = len(items); mx = max(_val(v) for _, v in items) or 1
    xs = [pad + (w - 2 * pad) * i / max(1, n - 1) for i in range(n)]; ys = [base - (base - top) * _val(v) / mx for _, v in items]
    pts = cached(e, 'sp', lambda: [(x, min(base, y)) for x, y in _spline(xs, ys)]); k = ease_inout((c.lt - 0.5) / 2.0); m_ = max(2, int(len(pts) * k))
    if k > 0:
        ov = _over(im); od = ImageDraw.Draw(ov); od.polygon(pts[:m_] + [(pts[m_ - 1][0], base), (pts[0][0], base)], fill=ACC_L + (70,)); im.alpha_composite(ov)
        d = ImageDraw.Draw(im); lw = max(4, int(w * 0.014)); d.line(pts[:m_], fill=WHITE + (255,), width=lw, joint='curve'); tip = pts[m_ - 1]; rr = w * 0.022
        for px, py in (pts[0], tip): d.ellipse([px - lw / 2, py - lw / 2, px + lw / 2, py + lw / 2], fill=WHITE + (255,))
        d.ellipse([tip[0] - rr, tip[1] - rr, tip[0] + rr, tip[1] + rr], fill=ACC_L + (255,), outline=WHITE + (255,), width=max(2, int(rr * 0.3)))
        d.text((min(tip[0], w - pad - w * 0.06), tip[1] - w * 0.06), _cnt(items[-1][1], (base - tip[1]) / max(1, base - ys[-1])), font=font('bold', w * 0.06), fill=WHITE + (255,), anchor='mm')
    return im.resize((w // S, h // S), Image.LANCZOS)


@effect('behind-chart', 'a tilted purple graph panel hangs in 3D behind your shoulder while a smooth curve draws upward and its value counts')
def fx_behind_chart(c, e):
    U = c.U; title = e.o.get('title', 'Followers'); items = _pairs(e, 'text', 'Jan::2K|Feb::5K|Mar::11K|Apr::19K|May::48K', 8); fx0, fy0, fw0 = _f0(c, e); a = _io(c, e)
    w, h = U * 0.62, U * 0.42; left = fx0 > c.W * 0.45; m = min(c.W, c.H) * 0.04
    if c.W > c.H: cx = c.W * (0.2 if left else 0.8); cy = c.H * 0.36
    else: cx = (m + w * 0.5) if left else (c.W - m - w * 0.5); cy = max(m + h * 0.55, fy0 - fw0 * 0.75)
    k = _k(c, 0.0, 0.7); _p3(c, _linepanel(c, e, w, h, U, title, items), _quad(cx, cy + (1 - k) * U * 0.03, w, h, 26 if left else -26, 3), a, behind=True)


@effect('icon-cluster', 'seven different emoji tiles drift in behind you from one side at different sizes, with your line on a pill')
def fx_icon_cluster(c, e):
    U = c.U; ems = e.o.get('emoji', '🤖|⚡|🎬|✍️|📈|💡|🎯').split('|'); text = e.o.get('text', 'AI does the busywork'); a = _io(c, e); fx0, fy0, fw0 = _f0(c, e)
    for i, (px, py, sz, rot) in enumerate(((0.13, 0.2, 1.0, -10), (0.86, 0.15, 0.85, 8), (0.2, 0.52, 0.7, 12), (0.84, 0.46, 1.12, -6), (0.08, 0.8, 0.8, 6), (0.92, 0.8, 0.7, -12), (0.52, 0.09, 0.75, 4))):
        k = _k(c, 0.1 + 0.11 * i, 0.9); q = int(U * 0.2 * sz)
        t = cached(e, f't{i}', lambda i=i, q=q: shadowed(_etile(ems[i % len(ems)], q, PAPER if i % 2 == 0 else ACC_LL), 14, 6, 100))
        place(c, t, px * c.W + (1 - k) * c.W * 0.22, py * c.H, 1, rot, a * k, behind=True)
    place(c, _pill(text, U * 0.044), c.W / 2, min(c.H * 0.9, fy0 + fw0 * 2.9), 1, 0, a * _k(c, 0.9, 0.5))


@effect('perspective-wall', 'a wall of your keywords on tiles runs off into the distance behind you and slides slowly past')
def fx_perspective_wall(c, e):
    U = c.U; words = e.o.get('text', 'Hooks|Scripts|Edits|Captions|Thumbnails|Ideas').split('|'); a = _io(c, e); fx0, fy0, fw0 = _f0(c, e); tw, th, gap = int(U * 0.42), int(U * 0.2), int(U * 0.03)
    def build():
        cols = 10; im = Image.new('RGBA', ((tw + gap) * cols, (th + gap) * 3), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for r in range(3):
            for q in range(cols):
                w = words[(q + r * 2) % len(words)]; bg, fg = ((PAPER, NAVY), (NAVY, WHITE), (ACC, WHITE))[(q + r) % 3]; x, y = q * (tw + gap), r * (th + gap)
                d.rounded_rectangle([x, y, x + tw, y + th], th * 0.2, fill=bg + (250,)); d.text((x + tw / 2, y + th / 2), w, font=_fit('bold', w, th * 0.36, tw * 0.84), fill=fg + (255,), anchor='mm')
        return im
    strip = cached(e, 's', build); off = int(c.lt * U * 0.06) % (tw + gap); win = strip.crop((off, 0, off + (tw + gap) * 6, strip.height))
    near_l = fx0 > c.W * 0.5; cy = fy0 - fw0 * 0.1; hn, hf = c.H * (0.62 if c.W > c.H else 0.3), c.H * (0.26 if c.W > c.H else 0.15); x0, x1 = -c.W * 0.04, c.W * 1.04
    quad = [(x0, cy - hn / 2), (x1, cy - hf / 2), (x1, cy + hf / 2), (x0, cy + hn / 2)] if near_l else [(x0, cy - hf / 2), (x1, cy - hn / 2), (x1, cy + hn / 2), (x0, cy + hf / 2)]
    _p3(c, win, quad, a * 0.96, behind=True)


def _steps(c, e, n, t0=0.5, gap=None):
    """How far through n steps we are (0..n-1), easing from one to the next."""
    gap = gap or max(0.9, (e.d - 1.0) / n); return sum(ease_inout((c.lt - (t0 + gap * (i + 1))) / 0.55) for i in range(n - 1))


@effect('card-stack', 'your points on a stack of cards tilted in 3D: the top card slides away to show the next')
def fx_card_stack(c, e):
    U = c.U; pts = e.o.get('text', 'Pick one idea|Write the hook first|Film it in one take').split('|')[:5]; n = len(pts); cw, ch = U * 0.62, U * 0.28; a = _io(c, e)
    cx, cy, s, _ = _spot(c, e, cw * 1.2, ch * 1.45, ('below', 'side'), 0.75, floor=0.6); prog = _steps(c, e, n)
    def make(i):
        im = rrect(cw, ch, U * 0.04, PAPER + (255,)); d = ImageDraw.Draw(im); q = ch * 0.2; d.rounded_rectangle([1, 1, cw - 2, ch - 2], U * 0.04, outline=ACC_LL + (255,), width=max(2, int(U * 0.005)))
        d.rounded_rectangle([ch * 0.2, ch / 2 - q, ch * 0.2 + 2 * q, ch / 2 + q], q * 0.45, fill=ACC + (255,)); d.text((ch * 0.2 + q, ch / 2), str(i + 1), font=font('bold', q * 1.2), fill=WHITE + (255,), anchor='mm')
        d.text((ch * 0.2 + q * 2.7, ch / 2), pts[i], font=_fit('bold', pts[i], U * 0.05, cw - ch * 0.4 - q * 2.9), fill=NAVY + (255,), anchor='lm'); return im
    for i in reversed(range(n)):
        j = i - prog
        if j <= -0.98 or j > 2.6: continue
        al, dx, dy, sc = (1 + j, j * cw * 0.45, 0, 1) if j < 0 else (1 - 0.3 * j, j * cw * 0.06, -j * ch * 0.2, 1 - 0.07 * j)
        _p3(c, cached(e, f'c{i}', lambda i=i: make(i)), _quad(cx + dx * s, cy + (ch * 0.14 + dy) * s, cw * s * sc, ch * s * sc, -14, 5), a * clamp(al), shade=0.12 * max(0, j))


@effect('cube-points', 'a 3D block turns a quarter turn for each of your points, one face per point')
def fx_cube_points(c, e):
    U = c.U; pts = e.o.get('text', 'Idea|Script|Record|Publish').split('|')[:6]; n = len(pts); w, h = U * 0.56, U * 0.26; a = _io(c, e)
    cx, cy, s, _ = _spot(c, e, w * 1.25, h * 1.2, ('below', 'side'), 0.75, floor=0.6); prog = _steps(c, e, n); w *= s; h *= s
    def make(i):
        im = rrect(U * 0.56, U * 0.26, U * 0.03, NAVY + (255,)); d = ImageDraw.Draw(im); H_ = U * 0.26
        d.text((H_ * 0.3, H_ / 2), f'{i + 1:02d}', font=font('bold', H_ * 0.36), fill=ACC_L + (255,), anchor='lm'); d.text((H_ * 0.95, H_ / 2), pts[i], font=_fit('bold', pts[i], H_ * 0.34, U * 0.56 - H_ * 1.2), fill=WHITE + (255,), anchor='lm'); return im
    for i in sorted(range(n), key=lambda i: -abs(i - prog)):
        ang = (i - prog) * 90
        if abs(ang) >= 89: continue
        r = w / 2; rad = math.radians(ang); _p3(c, cached(e, f'f{i}', lambda i=i: make(i)), _quad(cx, cy, w, h, ang, 0, f=w * 2.6, ox=math.sin(rad) * r, oz=(1 - math.cos(rad)) * r), a, shade=0.55 * abs(math.sin(rad)))


@effect('carousel-cards', 'your keywords on cards circle your head in 3D: across your chest in front, behind your head at the back')
def fx_carousel_cards(c, e):
    U = c.U; words = e.o.get('text', 'Hooks|Scripts|Edits|Captions|Ideas').split('|')[:7]; n = len(words); fx0, fy0, fw0 = _f0(c, e); a = _io(c, e); R = min(c.W * 0.4, fw0 * 2.4); base = c.lt * 0.6
    for z, i in sorted((math.cos(base + i * 2 * math.pi / n), i) for i in range(n)):
        ang = base + i * 2 * math.pi / n; d = (z + 1) / 2
        place(c, _pill(words[i], U * 0.042, PAPER if i % 2 else ACC, NAVY if i % 2 else WHITE), fx0 + R * math.sin(ang), fy0 + fw0 * 0.35 + z * fw0 * 1.5, 0.66 + 0.34 * d, 0, a * (0.5 + 0.5 * d), behind=z < 0, guard=z >= 0)


@effect('tilt-screen', 'a screen tilted in 3D shows your own dashboard: three numbers counting up over a row of rising bars')
def fx_tilt_screen(c, e):
    U = c.U; title = e.o.get('title', 'This month'); kp = _pairs(e, 'text', 'Views::1.2M|Followers::48K|Sales::£9,400', 3); w, h = U * 0.74, U * 0.48; a = _io(c, e)
    cx, cy, s, _ = _spot(c, e, w * 1.05, h * 1.1, ('below', 'side'), 0.75, floor=0.6)
    im = rrect(w, h, U * 0.035, PAPER + (255,)); d = ImageDraw.Draw(im); bar = h * 0.15; d.rounded_rectangle([0, 0, w - 1, bar], U * 0.035, fill=NAVY + (255,), corners=(True, True, False, False))
    for j in range(3): d.ellipse([bar * 0.4 + j * bar * 0.42, bar * 0.36, bar * 0.4 + j * bar * 0.42 + bar * 0.26, bar * 0.62], fill=(ACC_L, (120, 120, 160), (90, 90, 130))[j] + (255,))
    d.text((w / 2, bar / 2), title, font=font('uib', bar * 0.42), fill=WHITE + (255,), anchor='mm'); pad = w * 0.05; tw = (w - pad * 4) / 3
    for i, (lab, val) in enumerate(kp):
        x = pad + i * (tw + pad); d.rounded_rectangle([x, bar + pad, x + tw, bar + pad + h * 0.3], U * 0.02, fill=SOFT + (255,))
        d.text((x + tw * 0.1, bar + pad + h * 0.09), lab.upper(), font=font('uib', h * 0.05), fill=MUTE + (255,), anchor='lm')
        d.text((x + tw * 0.1, bar + pad + h * 0.2), _cnt(val, _k(c, 0.4 + 0.15 * i, 1.3)), font=_fit('bold', val, h * 0.11, tw * 0.82), fill=NAVY + (255,), anchor='lm')
    base = h - pad; top = bar + pad * 2 + h * 0.3; hs = (0.3, 0.45, 0.4, 0.6, 0.55, 0.78, 1.0); bw = (w - 2 * pad) / len(hs)
    for i, v in enumerate(hs):
        k = _k(c, 0.6 + 0.08 * i, 0.9); x = pad + bw * i
        d.rounded_rectangle([x + bw * 0.14, base - max(2, (base - top) * v * k), x + bw * 0.86, base], bw * 0.12, fill=(ACC if i == len(hs) - 1 else ACC_L) + (255,))
    _p3(c, im, _quad(cx, cy, w * s, h * s, -40 + 10 * ease_inout(c.lt / max(1, e.d)), 9, f=w * s * 1.7), a)


def _pillar(w, h, lit, idx):
    """One pillar, drawn at three times the size and scaled down: a purple gradient with a soft top highlight when lit."""
    S = 3; W_, H_ = int(w * S), int(h * S); t = np.linspace(0, 1, H_, dtype=np.float32)[:, None, None]
    top, bot = (np.float32(ACC_L), np.float32(DEEP)) if lit else (np.float32((62, 56, 104)), np.float32((34, 30, 64)))
    g = Image.fromarray(np.repeat((top * (1 - t) + bot * t).astype(np.uint8), W_, 1)).convert('RGBA'); g.putalpha(rrect(W_, H_, W_ * 0.16, (255, 255, 255, 255)).getchannel('A')); d = ImageDraw.Draw(g)
    d.rounded_rectangle([W_ * 0.08, W_ * 0.08, W_ * 0.92, W_ * 0.14], W_ * 0.03, fill=(255, 255, 255, 110 if lit else 40))
    d.text((W_ / 2, W_ * 0.42), f'{idx:02d}', font=font('bold', W_ * 0.3), fill=(255, 255, 255, 255 if lit else 120), anchor='mm')
    return g.resize((int(w), int(h)), Image.LANCZOS)


@effect('three-pillars', 'a dark full-screen hook: a glowing number, a headline, and three numbered pillars that rise and light up one by one')
def fx_three_pillars(c, e):
    U = c.U; num = str(e.o.get('to', '3')); head = e.o.get('text', 'things every video needs'); pil = e.o.get('pillars', 'Hook|Value|CTA').split('|')[:4]; n = len(pil); k = _io(c, e, 0.45, 0.45); wide = c.W > c.H
    def bg():
        yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32); t = (yy / c.H)[..., None]; g = np.float32((12, 10, 30)) * (1 - t) + np.float32((44, 22, 96)) * t
        g += np.exp(-(((xx - c.W / 2) / (c.W * 0.5)) ** 2 + ((yy - c.H * 0.8) / (c.H * 0.34)) ** 2))[..., None] * np.float32((70, 40, 150)) * 0.6
        im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert('RGBA'); d = ImageDraw.Draw(im); sp = U * 0.05; y = sp / 2
        while y < c.H:
            x = sp / 2
            while x < c.W: d.point((x, y), fill=(70, 60, 120, 255)); x += sp
            y += sp
        return im
    im = cached(e, 'bg', bg).copy(); ov = _over(im); od = ImageDraw.Draw(ov); ny = c.H * 0.19; hy = c.H * (0.4 if wide else 0.325)
    kn = _k(c, 0.3, 0.7)
    if kn > 0: ni = cached(e, 'n', lambda: text_img(num, U * 0.32, 'bold', WHITE, glow=(ACC, U * 0.03))); im.alpha_composite(_al(ni, kn), (int(c.W / 2 - ni.width / 2), int(ny - ni.height / 2 + (1 - kn) * U * 0.03)))
    _t(od, c.W / 2, hy, head.upper(), _fit('uib', head.upper(), U * 0.046, c.W * 0.86), ACC_LL, _k(c, 0.55, 0.5), 'mm', U * 0.015)
    lk = ease_inout((c.lt - 0.7) / 0.6)
    if lk > 0: od.line([(c.W / 2 - U * 0.09 * lk, hy + U * 0.05), (c.W / 2 + U * 0.09 * lk, hy + U * 0.05)], fill=ACC_L + (255,), width=max(3, int(U * 0.006)))
    pw = int(min(U * 0.24, c.W * 0.8 / n)); gap = pw * 0.3; x0 = (c.W - pw * n - gap * (n - 1)) / 2; base = c.H * 0.855; hmax = c.H * (0.3 if wide else 0.36)
    od.line([(x0 - gap, base), (x0 + pw * n + gap * n, base)], fill=(120, 100, 190, 255), width=max(2, int(U * 0.004)))
    for i, p in enumerate(pil):
        t0 = 0.9 + 0.4 * i; r = _k(c, t0, 0.9); lit = ease_inout((c.lt - t0 - 0.45) / 0.6); x = int(x0 + i * (pw + gap)); full = int(hmax * (0.62 + 0.19 * i)); hh = int(full * r)
        if hh > 6:
            a_, b_ = cached(e, f'p{i}', lambda i=i, full=full: (_pillar(pw, full, False, i + 1), _pillar(pw, full, True, i + 1)))
            if lit > 0: gl = cached(e, f'g{i}', lambda full=full: rrect(pw * 1.5, full + pw * 0.5, pw * 0.4, ACC + (120,)).filter(ImageFilter.GaussianBlur(pw * 0.3))); im.alpha_composite(_al(gl.crop((0, 0, gl.width, min(gl.height, hh + int(pw * 0.25)))), lit * 0.8), (int(x - pw * 0.25), int(base - hh - pw * 0.25)))
            im.alpha_composite(Image.blend(a_, b_, lit).crop((0, 0, pw, hh)), (x, int(base - hh)))
        _t(od, x + pw / 2, base + U * 0.05, p, _fit('bold', p, U * 0.046, pw * 1.25), WHITE, _k(c, t0 + 0.2, 0.5), 'mm')
    im.alpha_composite(ov); comp(c, im, 0, 0, k)


@effect('glass-notes-split', 'you shrink into a rounded frame while a notes panel opens beside you and ticks off your points')
def fx_glass_notes_split(c, e):
    U = c.U; title = e.o.get('title', 'In this video'); pts = e.o.get('text', 'Why hooks fail|The 3 second rule|A template to steal').split('|')[:4]; fx0, fy0, fw0 = _f0(c, e); k = _io(c, e, 0.6, 0.5); src = c.img.copy(); W, H = c.W, c.H
    bg = cv2.GaussianBlur(src, (0, 0), U * 0.03) * 0.35 + np.float32((14, 12, 32)) / 255 * 0.5; c.img = src * (1 - k) + bg * k; c.m = np.zeros_like(c.m)
    if W > H: th = H * 0.84; tw = th * 9 / 16; tx, ty = W * 0.06, H * 0.08; ch_ = H; cw_ = H * tw / th; sx = clamp(fx0 - cw_ / 2, 0, W - cw_); sy = 0; panel = (tx + tw + W * 0.05, H * 0.5 - (U * 0.2 + U * 0.11 * len(pts)) / 2, W * 0.94 - tx - tw - W * 0.05, U * 0.2 + U * 0.11 * len(pts))
    else: tw = W * 0.9; th = tw * 0.66; tx, ty = W * 0.05, H * 0.05; cw_ = W; ch_ = W * th / tw; sx = 0; sy = clamp(fy0 - ch_ * 0.42, 0, H - ch_); panel = (W * 0.05, ty + th + H * 0.035, W * 0.9, min(H * 0.9 - ty - th, U * 0.2 + U * 0.11 * len(pts)))
    L = lambda a, b: a + (b - a) * k; x0, y0, w0, h0 = int(L(0, sx)), int(L(0, sy)), int(L(W, cw_)), int(L(H, ch_)); dx, dy, dw, dh = int(L(0, tx)), int(L(0, ty)), max(2, int(L(W, tw))), max(2, int(L(H, th)))
    patch = cv2.resize(src[y0:y0 + h0, x0:x0 + w0], (dw, dh), interpolation=cv2.INTER_AREA); mask = np.asarray(rrect(dw, dh, k * U * 0.05, (255, 255, 255, 255)).getchannel('A'), np.float32) / 255
    comp(c, np.dstack([patch, mask]), dx, dy)
    a = clamp((k - 0.7) / 0.3); px, py, pw, ph = panel
    if a > 0:
        im = rrect(pw, ph, U * 0.04, (255, 255, 255, 34)); d = ImageDraw.Draw(im); d.rounded_rectangle([1, 1, pw - 2, ph - 2], U * 0.04, outline=(255, 255, 255, 90), width=max(2, int(U * 0.004))); ov = _over(im); od = ImageDraw.Draw(ov); pad = pw * 0.08; rh = min(U * 0.11, (ph - pad * 2 - U * 0.1) / max(1, len(pts)))
        od.text((pad, pad + U * 0.03), title.upper(), font=_fit('uib', title.upper(), U * 0.036, pw - pad * 2), fill=ACC_L + (255,), anchor='lm')
        for i, p in enumerate(pts):
            ki = _k(c, 1.0 + 0.3 * i, 0.5); cy = pad + U * 0.1 + rh * (i + 0.5); q = rh * 0.24
            if ki > 0:
                od.ellipse([pad, cy - q, pad + 2 * q, cy + q], fill=ACC + (int(255 * ki),)); hand_path(od, _tickpts(pad + q, cy, q * 0.95), WHITE + (int(255 * ki),), max(2, int(q / 3.5)), ease_inout((c.lt - 1.1 - 0.3 * i) / 0.4))
                od.text((pad + q * 2.9, cy), p, font=_fit('bold', p, U * 0.046, pw - pad * 2 - q * 3), fill=WHITE + (int(255 * ki),), anchor='lm')
        im.alpha_composite(ov); comp(c, im, px, py, a)


# ---------- video in/out + tracking ----------
def probe(path):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate:format=duration',
                                   '-of', 'json', path], capture_output=True, text=True, check=True).stdout)
    fr = j['streams'][0]['r_frame_rate']; num, den = fr.split('/'); fps = float(num) / float(den or 1)
    png = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True, check=True).stdout
    h, w = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR).shape[:2]
    return (fr if fps <= 30.5 else '30'), min(fps, 30.0), float(j['format']['duration']), w, h


def read_frames(path, W, H, fr):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps={fr},scale={W}:{H}:flags=bicubic,format=rgb24', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE, bufsize=10 ** 8)
    n = W * H * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n: break
            yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    finally:
        if p.poll() is None: p.kill()
        p.stdout.close(); p.wait()


def guided(I, p, r=8, eps=2e-3):
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp_ = box(I), box(p); a = (box(I * p) - mI * mp_) / (box(I * I) - mI * mI + eps); b = mp_ - a * mI
    return np.clip(box(a) * I + box(b), 0, 1)


class Tracker:
    def __init__(self, aw, ah):
        import mediapipe as mp
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.core.base_options import BaseOptions
        self.mp = mp
        self.seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=os.path.join(ROOT, 'models', 'selfie_segmenter.tflite')),
            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True, output_category_mask=False))
        self.fd = cv2.FaceDetectorYN.create(os.path.join(ROOT, 'models', 'yunet.onnx'), '', (aw, ah), 0.6, 0.3, 20)
        self.prev = None

    def __call__(self, rgb, ms):
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        ms_ = self.seg.segment_for_video(img, ms).confidence_masks
        m = ms_[-1].numpy_view().astype(np.float32); m = m.reshape(m.shape[0], m.shape[1])
        if m.shape[:2] != rgb.shape[:2]: m = cv2.resize(m, (rgb.shape[1], rgb.shape[0]))
        m = guided(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, m)
        m = np.clip((m - 0.5) * 1.6 + 0.5, 0, 1)
        if self.prev is not None: m = 0.65 * m + 0.35 * self.prev
        self.prev = m
        _, f = self.fd.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        face = None
        if f is not None and len(f):
            r = max(f, key=lambda r: r[2] * r[3] * r[-1]); face = (r[0] + r[2] / 2, r[1] + r[3] / 2, r[2])
        else:
            rows = np.where((m > 0.5).sum(1) > m.shape[1] * 0.01)[0]
            if len(rows):
                top = rows[0]; band = m[top:top + max(4, int(m.shape[0] * 0.06))] > 0.5; xs = np.where(band.any(0))[0]
                fw = max(8.0, (xs.max() - xs.min()) * 0.8); face = (float(xs.mean()), top + fw * 0.7, fw)
        return (m * 255).astype(np.uint8), face


def smooth(vals, fps, tau=0.18):
    idx = [i for i, v in enumerate(vals) if v is not None]
    if not idx: return None
    arr = np.array([vals[i] if vals[i] is not None else (np.nan,) * 3 for i in range(len(vals))], np.float64)
    for k in range(3):
        col = arr[:, k]; good = ~np.isnan(col); col[~good] = np.interp(np.where(~good)[0], np.where(good)[0], col[good]); arr[:, k] = col
    a = 1 - math.exp(-1 / (fps * tau))  # forward then backward pass, so the smoothing has no lag
    for i in range(1, len(arr)): arr[i] = arr[i - 1] + a * (arr[i] - arr[i - 1])
    for i in range(len(arr) - 2, -1, -1): arr[i] = arr[i + 1] + a * (arr[i] - arr[i + 1])
    return arr


class Ctx: pass


class Fx:
    def __init__(self, d, fps):
        self.name = d['fx']; self.start = float(d['start']); self.end = float(d['end']); self.d = max(0.05, self.end - self.start)
        self.o = {k: v for k, v in d.items() if k not in ('fx', 'start', 'end')}; self.state = {}; self.cards = []


def load_cards(folder, thumbs):
    out = []
    if folder and os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            p = os.path.join(folder, n); ext = n.lower().rsplit('.', 1)[-1]
            if ext in ('jpg', 'jpeg', 'png', 'webp'): out.append(Image.open(p).convert('RGB'))
            elif ext in ('mp4', 'mov', 'm4v', 'webm'):
                cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_MSEC, 1000); ok, fr = cap.read(); cap.release()
                if ok: out.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
    return out or thumbs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('args', nargs='*', help='[effect] input.mp4 output.mp4')
    ap.add_argument('--plan'); ap.add_argument('--start', type=float); ap.add_argument('--end', type=float)
    ap.add_argument('--text'); ap.add_argument('--images'); ap.add_argument('--opt', action='append', default=[], help='key=value')
    ap.add_argument('--still', help='comma-separated seconds: save PNG check frames instead of a video')
    ap.add_argument('--width', type=int, default=1080, help='short side of the output (1080 default, 2160 for 4K)')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    if a.list:
        for i, (k, (_, d)) in enumerate(EFFECTS.items()): print(f'{i + 1:2d}. {k:15s} {d}')
        return
    if a.plan:
        src, dst = a.args[0], a.args[1]; plan = json.load(open(a.plan))
        plan = plan.get('effects', plan) if isinstance(plan, dict) else plan
    else:
        name, src, dst = a.args[0], a.args[1], a.args[2]
        d = {'fx': name, 'start': a.start or 0.0, 'end': a.end if a.end is not None else 1e9}
        if a.text: d['text'] = a.text
        if a.images: d['images'] = a.images
        for kv in a.opt: k, v = kv.split('=', 1); d[k] = v
        plan = [d]
    for d in plan:
        d['fx'] = ALIASES.get(d['fx'].lower().lstrip('/'), d['fx'].lower().lstrip('/'))
        if d['fx'] in LOOK_NAMES: d['fx'], look = LOOK_NAMES[d['fx']]; d.setdefault('look', look)
        if d['fx'] not in EFFECTS: sys.exit(f"Unknown effect '{d['fx']}'. Run --list to see all {len(EFFECTS)}.")
    fr, fps, dur, sw, sh = probe(src)
    for d in plan: d['end'] = min(float(d['end']), dur)
    if sw <= sh: W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else: H = a.width; W = int(round(a.width * sw / sh / 2)) * 2
    aw = 540 if sw <= sh else int(round(540 * sw / sh / 2)) * 2; ah = int(round(aw * sh / sw / 2)) * 2
    fxs = [Fx(d, fps) for d in plan]
    inwin = lambda t: any(f.start - 0.5 <= t < f.end + 0.5 for f in fxs)
    print(f'Pass 1: tracking you ({len(fxs)} effect{"s" * (len(fxs) > 1)})...', flush=True)
    trk = Tracker(aw, ah); masks, faces, thumbs = {}, [], []
    n_thumb = 10; thumb_at = {int(dur * fps * (j + 0.5) / n_thumb) for j in range(n_thumb)}
    for i, fr_ in enumerate(read_frames(src, aw, ah, fr)):
        t = i / fps
        if i in thumb_at: thumbs.append(Image.fromarray(fr_.copy()))
        if inwin(t):
            m, f = trk(fr_, int(t * 1000)); masks[i] = m; faces.append(f)
        else:
            faces.append(None); trk.prev = None
    sm = smooth(faces, fps)
    if sm is None: sm = np.tile([aw / 2, ah * 0.33, aw * 0.15], (len(faces), 1))
    for f in fxs:
        if f.name in CARD_FX: f.cards = load_cards(f.o.get('images'), thumbs)
    stills = sorted({int(round(float(s) * fps)) for s in a.still.split(',')}) if a.still else None
    enc = None
    if not stills:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fr), '-i', '-',
                                '-i', src, '-map', '0:v', '-map', '1:a:0?', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
    print('Pass 2: adding the effects...', flush=True)
    sc = W / aw; total = int(dur * fps)
    for i, frame in enumerate(read_frames(src, W, H, fr)):
        t = i / fps
        act = [f for f in fxs if f.start <= t < f.end]
        if stills is not None and i not in stills:
            if i > stills[-1]: break
            continue
        if act:
            c = Ctx(); c.W, c.H, c.t, c.fps = W, H, t, fps; c.U = min(W, H * 0.75)  # size unit: the width in 9:16, a 3:4 page in 16:9
            c.img = frame.astype(np.float32) / 255.0
            m = masks.get(i)
            c.m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0 if m is not None else np.zeros((H, W), np.float32)
            fx_, fy_, fw_ = sm[min(i, len(sm) - 1)]; c.fx, c.fy, c.fw = fx_ * sc, fy_ * sc, max(fw_ * sc, W * 0.05)
            for f in act:
                c.lt = t - f.start; EFFECTS[f.name][0](c, f)
            frame = (np.clip(c.img, 0, 1) * 255 + 0.5).astype(np.uint8)
        if stills is not None:
            out = dst if len(stills) == 1 else dst.replace('.png', f'_{t:.2f}.png')
            cv2.imwrite(out, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)); print('saved', out)
        else:
            enc.stdin.write(frame.tobytes())
            if i % int(fps * 5) == 0: print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)
    if enc: enc.stdin.close(); enc.wait(); print('Done:', dst)


if __name__ == '__main__':
    main()
