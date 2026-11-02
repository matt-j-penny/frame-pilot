#!/usr/bin/env python3
"""Frame Pilot pipeline. Every command reads/writes files in a job folder so any stage can be re-run.

  reel.py styles                                  list styles + presets
  reel.py style-check <name>                      validate a style guide's machine block
  reel.py frames <video> <out_dir> [--every 1]    sample frames + contact sheets (style analysis)
  reel.py ingest <video> <style>                  validate input, create job -> prints job dir
  reel.py transcribe <job>                        Deepgram nova-2, word-level -> transcript.json
  reel.py sentences <job>                         numbered sentences + retake/low-confidence hints
  reel.py cut <job> [--gap 0.4] [--pad 0.12]      fillers/pauses/cuts.json -> edl.json, cut-log.md, public/cut.mp4
  reel.py render <job> [--preview]                beat-plan.json -> props.json -> output/final.mp4
  reel.py storyboard <job>                        stills of every beat + alternatives -> preview/preview.json
  reel.py verify <job> [--file final.mp4]         frames, contact sheets, loudness, spec check -> verify/
  reel.py search <query>                          Brave image search (needs BRAVE_API_KEY)
  reel.py fetch <job> <url> <name>                download an image to public/assets, log source
  reel.py shot <job> <url> <name> [--w --h]       headless Chrome screenshot to public/assets
  reel.py lib-import <folder> <music|sfx>         copy audio files into the library + stub dictionary entries
  reel.py lib-check                               list library entries missing files or descriptions
"""
import argparse
import difflib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILLERS = {"um", "uh", "uhm", "umm", "uhh", "ah", "er", "erm", "hmm", "mm", "mhm"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".aif", ".aiff"}
LAYOUTS = {"talking_head", "split", "fullscreen", "overlay"}
GRAPHICS = {"text", "stat", "list", "logo", "image", "screenshot", "icon", "quote", "compare", "notifications", "checklist", "chat", "chips", "phone", "title", "videogrid", "repo", "editor", "desktop", "comment", "badge", "code", "role", "queue", "timeline", "template"}
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def die(msg, fix=None):
    print(f"ERROR: {msg}" + (f"\nFIX: {fix}" if fix else ""), file=sys.stderr)
    sys.exit(1)


def run(*a, capture=False):
    r = subprocess.run([str(x) for x in a], capture_output=capture, text=True)
    if r.returncode < 0:  # ponytail: killed by a signal (seen: sporadic ffmpeg segfault), retry once
        r = subprocess.run([str(x) for x in a], capture_output=capture, text=True)
    if r.returncode:
        die(f"{Path(str(a[0])).name} failed (exit {r.returncode})" + (f": {r.stderr[-1500:]}" if capture else ""))
    return r


def rj(p):
    return json.loads(Path(p).read_text())


def wj(p, d):
    Path(p).write_text(json.dumps(d, indent=1))


def env_key(name):
    # An explicit project credential overrides a stale inherited environment.
    for s in [ROOT / "config.local.json", None, Path.home() / ".claude" / "settings.json"]:
        if s is None:
            value = os.environ.get(name)
            if value:
                return value.strip()
        elif s.exists():
            try:
                value = json.loads(s.read_text()).get("env", {}).get(name)
                if value:
                    return value.strip()
            except (ValueError, OSError):
                continue
    return None


def https_context():
    """Verified TLS using explicit settings, or system roots plus certifi when available."""
    cafile = env_key("SSL_CERT_FILE") or env_key("REQUESTS_CA_BUNDLE")
    capath = env_key("SSL_CERT_DIR")
    try:
        context = ssl.create_default_context(cafile=cafile, capath=capath)
        # Explicit CA settings may be intentional (for example, an organisation's CA).
        if not cafile and not capath:
            try:
                import certifi
            except ImportError:
                certifi = None
            if certifi is not None:
                context.load_verify_locations(cafile=certifi.where())
            if not context.cert_store_stats().get("x509_ca") and sys.platform != "win32":
                for bundle in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt"):
                    if Path(bundle).is_file():
                        context.load_verify_locations(cafile=bundle)
                        break
        return context
    except (OSError, ssl.SSLError):
        die("Could not load trusted HTTPS certificates.",
            "Check SSL_CERT_FILE/SSL_CERT_DIR if configured, or install/update certifi for the Python used by the server: python3 -m pip install --upgrade certifi.")


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def probe(path):
    d = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path, capture=True).stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    info = {"duration": float(d["format"].get("duration", 0)), "has_audio": bool(a)}
    if v:
        num, den = v.get("avg_frame_rate", "0/1").split("/")
        rot = next((abs(int(x.get("rotation", 0))) for x in v.get("side_data_list", []) if "rotation" in x), 0)
        w, h = v["width"], v["height"]
        info.update(width=h if rot in (90, 270) else w, height=w if rot in (90, 270) else h,
                    fps=round(int(num) / int(den), 3) if int(den) else 0, codec=v["codec_name"])
    return info


# ---------- styles ----------

def style_dirs():
    return [d for base in (ROOT / "styles", ROOT / "presets") if base.exists()
            for d in sorted(base.iterdir()) if (d / "style-guide.md").exists()]


def find_style(name):
    return next((d for d in style_dirs() if d.name == name), None)


def load_style(d):
    m = re.search(r"```json reel-style\s*\n(.*?)\n```", (d / "style-guide.md").read_text(), re.S)
    if not m:
        die(f"{d.name}/style-guide.md has no ```json reel-style block", "Add the machine-readable block (see references/style-schema.md).")
    try:
        s = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        die(f"{d.name} style block is not valid JSON: {e}")
    problems = []
    for key in ("canvas", "fonts", "colors", "background", "layouts", "pacing", "motion", "captions", "cards", "transitions", "audio"):
        if key not in s:
            problems.append(f"missing '{key}'")
    for role, f in s.get("fonts", {}).items():
        if not (d / "assets" / f.get("file", "")).is_file():
            problems.append(f"font '{role}' file not found: assets/{f.get('file')}")
    bg = s.get("background", {}).get("file")
    if bg and not (d / "assets" / bg).is_file():
        problems.append(f"background file not found: assets/{bg}")
    if abs(sum(s.get("layouts", {}).values()) - 1) > 0.05:
        problems.append("layouts frequencies should sum to 1.0")
    if problems:
        die(f"style '{d.name}' is invalid: " + "; ".join(problems), "Fix the reel-style block or add the missing asset files.")
    return s


def cmd_styles(a):
    rows = style_dirs()
    if not rows:
        print("No styles yet. Create one with: create style <name>")
    for d in rows:
        m = re.search(r"```json reel-style\s*\n(.*?)\n```", (d / "style-guide.md").read_text(), re.S)
        s = json.loads(m.group(1)) if m else {}
        print(f"{d.name:24} {d.parent.name[:-1]:7} {'locked' if s.get('locked') else 'draft ':7} {s.get('description', '')}")


def cmd_style_check(a):
    d = find_style(a.name) or die(f"unknown style '{a.name}'")
    s = load_style(d)
    print(json.dumps({"style": d.name, "dir": str(d), "locked": s.get("locked", False),
                      "fonts": {k: v["family"] for k, v in s["fonts"].items()}, "colors": s["colors"]}, indent=1))


# ---------- frames / contact sheets ----------

def sheets(video, times, out_dir, w, h, fps, safe=None):
    """One ffmpeg pass: grab frames nearest each time, tile 4x2. Returns [(sheet, [times])]."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.png"):
        old.unlink()
    frames = sorted({round(t * fps) for t in times})
    times = [n / fps for n in frames]
    steps = {b - a for a, b in zip(frames, frames[1:])}
    if frames and frames[0] == 0 and len(steps) == 1:
        # ponytail: long eq() chains overflow ffmpeg's expression parser (~100+ terms)
        expr = f"not(mod(n,{steps.pop()}))*lte(n,{frames[-1]})"
    else:
        expr = "+".join(f"eq(n,{n})" for n in frames)
    vf = f"select='{expr}',scale={w}:{h}"
    if safe:
        top, bottom, right = safe
        vf += (f",drawbox=x=0:y=0:w=iw:h={top * h / 1920:.0f}:color=red@0.22:t=fill"
               f",drawbox=x=0:y={h - bottom * h / 1920:.0f}:w=iw:h={bottom * h / 1920:.0f}:color=red@0.22:t=fill"
               f",drawbox=x={w - right * w / 1080:.0f}:y=0:w={right * w / 1080:.0f}:h=ih:color=red@0.12:t=fill")
    vf += ",tile=4x2:padding=6:color=white"
    exprfile = out_dir / "select.txt"
    exprfile.write_text(vf)
    run("ffmpeg", "-v", "error", "-y", "-i", video, "-/vf", exprfile, "-fps_mode", "vfr", out_dir / "sheet_%02d.png")
    exprfile.unlink()
    files = sorted(out_dir.glob("sheet_*.png"))
    return [(str(f), [round(t, 2) for t in times[i * 8:(i + 1) * 8]]) for i, f in enumerate(files)]


def cmd_frames(a):
    info = probe(a.video)
    times = [i * a.every for i in range(int(info["duration"] / a.every))]
    w = 360 if info.get("height", 1) >= info.get("width", 1) else 640
    h = round(w * info["height"] / info["width"] / 2) * 2
    res = sheets(a.video, times, a.out_dir, w, h, info["fps"] or 30)
    wj(Path(a.out_dir) / "sheets.json", [{"sheet": s, "times": t} for s, t in res])
    print(json.dumps({"video": info, "sheets": len(res), "index": str(Path(a.out_dir) / "sheets.json")}))


# ---------- ingest / transcribe ----------

def job_dir(p):
    p = Path(p).expanduser().resolve()
    if not (p / "job.json").exists():
        p = ROOT / "jobs" / p.name
    return p if (p / "job.json").exists() else die(f"not a job folder: {p}")


def cmd_ingest(a):
    src = Path(a.video).expanduser().resolve()
    if not src.is_file():
        die(f"file not found: {src}")
    unstyled = getattr(a, "no_style", False) or not a.style
    d = ROOT / "presets" / "clean-minimal" if unstyled else find_style(a.style)
    if not d:
        names = ", ".join(x.name for x in style_dirs()) or "none"
        die(f"unknown style '{a.style}'. Available: {names}", "Pick one of the listed styles or create it first.")
    style = load_style(d)
    if unstyled:
        # Reuse bundled font assets and the renderer schema, without preset editorial rules.
        style.update(name="", description="Job-local render settings; no saved style", locked=False)
        style["layouts"] = {"talking_head": .25, "overlay": .25, "split": .25, "fullscreen": .25}
        style["colors"].update(primary="#FFFFFF", secondary="#E5E7EB", accent="#FFFFFF", text="#FFFFFF", muted="#9CA3AF", highlight="#FFFFFF", background="#111111")
        style["background"] = {"color": "#111111", "file": None}
        style["cards"].update(background="#222222", text="#FFFFFF", shadow="none", border="none")
        style["captions"].update(emphasis_color="#FFFFFF", emphasis_scale=1.0, highlight={"type": "color", "color": "#FFFFFF"})
        style["pacing"].update(punch_in_scale=1.0)
        style["transitions"]["allowed"] = ["cut", "zoom", "slide", "whip"]
    info = probe(src)
    if "width" not in info:
        die("file has no video stream", "Pass the raw video file, not an audio file.")
    if not info["has_audio"]:
        die("video has no audio track", "Re-export the clip with its audio, or record with the mic enabled.")
    job = ROOT / "jobs" / (a.id or f"{datetime.now():%Y%m%d-%H%M%S}-{re.sub(r'[^a-z0-9]+', '-', src.stem.lower()).strip('-')[:40]}")
    if (job / "job.json").exists():
        die(f"job {job.name} already exists", "Use a new --id, or keep working in the existing job folder.")
    for sub in ("input", "public/assets", "public/music", "public/sfx", "output", "verify"):
        (job / sub).mkdir(parents=True, exist_ok=True)
    (job / "input" / f"source{src.suffix.lower()}").symlink_to(src)
    if (d / "assets").exists():
        shutil.copytree(d / "assets", job / "public" / "style", dirs_exist_ok=True)
    settings = rj(job / "ui.json") if (job / "ui.json").exists() else {}
    aspect = settings.get("aspectRatio")
    if aspect in ("9:16", "16:9"):
        style["canvas"].update(width=1920 if aspect == "16:9" else 1080, height=1080 if aspect == "16:9" else 1920)
        if aspect == "16:9":
            style["safe_zone"] = {"top": 60, "bottom": 100, "right": 80}
    wj(job / "style.json", style)
    wj(job / "job.json", {"source": str(src), "style": "" if unstyled else d.name, "style_dir": None if unstyled else str(d), "probe": info,
                          "created": datetime.now().isoformat(timespec="seconds")})
    print(json.dumps({"job": str(job), "probe": info, "style": "" if unstyled else d.name, "canvas": style["canvas"]}))


def cmd_transcribe(a):
    job = job_dir(a.job)
    key = env_key("DEEPGRAM_API_KEY") or die("DEEPGRAM_API_KEY not set", "Set it in your environment or the env block of config.local.json.")
    src = next(p for p in (job / "input").iterdir() if p.name.startswith("source"))
    mp3 = job / "input" / "audio.mp3"
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-b:a", "96k", mp3)
    params = "model=nova-2&smart_format=true&punctuate=true&paragraphs=true&utterances=true&words=true&filler_words=true"
    req = urllib.request.Request(f"https://api.deepgram.com/v1/listen?{params}", data=mp3.read_bytes(),
                                 headers={"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=600, context=https_context()) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            die("Deepgram rejected DEEPGRAM_API_KEY (HTTP 401)", "Update DEEPGRAM_API_KEY in config.local.json. Project config overrides the environment; Codex/Claude login does not fix Deepgram credentials.")
        if e.code == 429:
            die("The transcription service is temporarily rate-limited (HTTP 429).", "Wait a moment and try Transcribe video again.")
        die(f"The transcription service returned HTTP {e.code}.", "Check the Deepgram account's access and available credits, then try again.")
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(e.reason):
            die("Could not verify the transcription service's HTTPS certificate.",
                "Update certifi for the Python used by the server: python3 -m pip install --upgrade certifi. If your network uses a custom certificate authority, set SSL_CERT_FILE to its trusted CA bundle in config.local.json or the server environment.")
        die("Could not connect to the transcription service.", "Check your internet connection, VPN or proxy, then try Transcribe video again.")
    except ssl.SSLError:
        die("A secure connection to the transcription service could not be established.", "Check the trusted certificate bundle and your network, then try again.")
    except TimeoutError:
        die("The transcription request timed out.", "Try Transcribe video again when the service and connection are available.")
    wj(job / "deepgram.json", res)
    alt = res["results"]["channels"][0]["alternatives"][0]
    words = [{"i": i, "word": w.get("punctuated_word", w["word"]), "start": w["start"], "end": w["end"],
              "conf": round(w.get("confidence", 1), 3)} for i, w in enumerate(alt["words"])]
    if not words:
        die("transcription returned no words", "Check the audio track actually contains speech.")
    wj(job / "transcript.json", {"duration": res["metadata"]["duration"], "words": words})
    print(json.dumps({"words": len(words), "duration": res["metadata"]["duration"], "fillers": sum(norm(w["word"]) in FILLERS for w in words)}))


# ---------- rough cut ----------

def split_sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"][-1:] in ".?!" or w is words[-1]:
            out.append(cur)
            cur = []
    return out


def cmd_sentences(a):
    job = job_dir(a.job)
    words = rj(job / "transcript.json")["words"]
    sents = split_sentences(words)
    rows = []
    for n, s in enumerate(sents):
        text = " ".join(w["word"] for w in s)
        low = [f"{w['word']}@{w['i']}" for w in s if w["conf"] < 0.6]
        rows.append({"s": n, "from": s[0]["i"], "to": s[-1]["i"], "start": s[0]["start"], "end": s[-1]["end"], "text": text, "low_conf": low})
    for r in rows:
        key = [norm(x) for x in r["text"].split() if norm(x) not in FILLERS]
        r["similar_later"] = []
        for o in rows[r["s"] + 1:r["s"] + 5]:
            okey = [norm(x) for x in o["text"].split() if norm(x) not in FILLERS]
            ratio = difflib.SequenceMatcher(None, key, okey).ratio()
            same_open = len(key) >= 3 and key[:3] == okey[:3]
            if ratio >= 0.5 or same_open:
                r["similar_later"].append({"s": o["s"], "ratio": round(ratio, 2)})
        r["no_end_punct"] = r["text"][-1:] not in ".?!"
    wj(job / "sentences.json", rows)
    for r in rows:
        flags = []
        if r["similar_later"]:
            flags.append("RETAKE? -> " + ",".join(f"s{x['s']}({x['ratio']})" for x in r["similar_later"]))
        if r["low_conf"]:
            flags.append("LOWCONF " + " ".join(r["low_conf"]))
        if r["no_end_punct"]:
            flags.append("TRAILS OFF")
        print(f"s{r['s']} [w{r['from']}-{r['to']}] {r['start']:.2f}-{r['end']:.2f}: {r['text']}" + (f"   <<{' | '.join(flags)}>>" if flags else ""))


def plan_cut(words, duration, manual, gap, pad, remove_fillers=True):
    removed = {}
    for w in words:
        if remove_fillers and norm(w["word"]) in FILLERS:
            removed[w["i"]] = "filler"
    for c in manual:
        for i in range(c["from"], c["to"] + 1):
            removed[i] = c.get("reason", "manual")
    segs, pauses = [], []
    prev = None
    for w in words:
        if w["i"] in removed:
            continue
        if prev and w["i"] == prev["i"] + 1 and w["start"] - prev["end"] <= gap:
            segs[-1][1] = w
        else:
            if prev and w["i"] == prev["i"] + 1:
                pauses.append((prev["end"], w["start"]))
            segs.append([w, w])
        prev = w
    edl, out_t = [], 0.0
    for first, last in segs:
        before = words[first["i"] - 1]["end"] if first["i"] > 0 else 0.0
        after = words[last["i"] + 1]["start"] if last["i"] + 1 < len(words) else duration
        s = max(first["start"] - pad, (before + first["start"]) / 2 if first["i"] > 0 else 0.0)
        e = min(last["end"] + pad, (last["end"] + after) / 2 if last["i"] + 1 < len(words) else duration)
        if not remove_fillers:
            if first["i"] == 0:
                s = 0.0
            if last["i"] == len(words) - 1:
                e = duration
        edl.append({"src_start": round(s, 3), "src_end": round(e, 3), "out_start": round(out_t, 3),
                    "words": [first["i"], last["i"]]})
        out_t += e - s
    return removed, pauses, edl, out_t


def cmd_cut(a):
    job = job_dir(a.job)
    t = rj(job / "transcript.json")
    words = t["words"]
    manual = rj(job / "cuts.json") if (job / "cuts.json").exists() else []
    settings = rj(job / "ui.json") if (job / "ui.json").exists() else {}
    rough = settings.get("features", {}).get("roughCut", True)
    removed, pauses, edl, total = plan_cut(words, t["duration"], manual, a.gap if rough else float("inf"), a.pad, remove_fillers=rough)
    if not rough and not manual:
        removed, pauses, total = {}, [], t["duration"]
        edl = [{"src_start": 0, "src_end": total, "out_start": 0, "words": [words[0]["i"], words[-1]["i"]]}] if words else []
    if not edl:
        die("every word was cut", "Check cuts.json ranges.")
    seg_of = {}
    for seg in edl:
        for i in range(seg["words"][0], seg["words"][1] + 1):
            seg_of[i] = seg
    cut_words = []
    for w in words:
        if w["i"] in seg_of:
            seg = seg_of[w["i"]]
            off = seg["out_start"] - seg["src_start"]
            cut_words.append({**w, "start": round(w["start"] + off, 3), "end": round(w["end"] + off, 3)})
    wj(job / "edl.json", {"gap": a.gap, "pad": a.pad, "source_duration": t["duration"], "duration": round(total, 3), "segments": edl})
    wj(job / "transcript-cut.json", {"duration": round(total, 3), "words": cut_words})

    log = [f"# Cut log\n", f"- Source: {t['duration']:.2f}s -> cut: {total:.2f}s ({t['duration'] - total:.2f}s removed)",
           f"- Segments kept: {len(edl)} (cuts: {len(edl) - 1})",
           f"- Fillers removed: {sum(r == 'filler' for r in removed.values())}",
           f"- Words removed by cuts.json: {sum(r != 'filler' for r in removed.values())}",
           f"- Pauses > {a.gap}s trimmed: {len(pauses)}\n", "## Removed words"]
    run_start, reason, buf = None, None, []
    for w in words + [None]:
        r = removed.get(w["i"]) if w else None
        if buf and r != reason:
            log.append(f"- {run_start:.2f}s [{reason}] {' '.join(buf)}")
            buf = []
        if r:
            if not buf:
                run_start, reason = w["start"], r
            buf.append(w["word"])
    log.append("\n## Pauses trimmed")
    log += [f"- {s:.2f}-{e:.2f} ({e - s:.2f}s)" for s, e in pauses]
    (job / "cut-log.md").write_text("\n".join(log) + "\n")

    c = rj(job / "style.json")["canvas"]
    W, H, F = c["width"], c["height"], c["fps"]
    src = next(p for p in (job / "input").iterdir() if p.name.startswith("source"))
    parts = []
    for n, s in enumerate(edl):
        d = s["src_end"] - s["src_start"]
        o = a.av_offset  # seconds the picture lags the sound in the source
        parts.append(f"[0:v]trim=start={s['src_start'] + o}:end={s['src_end'] + o},setpts=PTS-STARTPTS[v{n}];"
                     f"[0:a]atrim=start={s['src_start']}:end={s['src_end']},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.012,afade=t=out:st={max(d - 0.012, 0):.3f}:d=0.012[a{n}];")
    graph = "".join(parts) + "".join(f"[v{n}][a{n}]" for n in range(len(edl))) + \
        f"concat=n={len(edl)}:v=1:a=1[v][a];" \
        f"[v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={F},setsar=1{',eq=' + a.eq if a.eq else ''},format=yuv420p[vo];" \
        f"[a]speechnorm=e=4:c=6:p=0.95,aresample=48000[ao]"
    gf = job / "cut-filter.txt"
    gf.write_text(graph)
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-/filter_complex", gf, "-map", "[vo]", "-map", "[ao]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-b:a", "256k", job / "public" / "cut.mp4")
    print(json.dumps({"source": t["duration"], "cut": round(total, 2), "segments": len(edl),
                      "fillers": sum(r == "filler" for r in removed.values()), "pauses": len(pauses), "log": str(job / "cut-log.md")}))


# ---------- render ----------

def validate_plan(job, plan, style, duration):
    errs = []
    beats = plan.get("beats", [])
    if not beats:
        errs.append("no beats")
    allowed = {k for k, v in style["layouts"].items() if v > 0}
    for i, b in enumerate(beats):
        tag = f"beat {b.get('id', i)}"
        if b["layout"] not in LAYOUTS:
            errs.append(f"{tag}: unknown layout {b['layout']}")
        elif b["layout"] not in allowed and (b.get("graphic") or {}).get("type") != "template":
            errs.append(f"{tag}: layout {b['layout']} not allowed by style")
        if b["end"] <= b["start"]:
            errs.append(f"{tag}: end <= start")
        if i and abs(b["start"] - beats[i - 1]["end"]) > 0.05:
            errs.append(f"{tag}: gap/overlap with previous beat ({beats[i - 1]['end']} -> {b['start']})")
        g = b.get("graphic")
        if b["layout"] != "talking_head" and not g:
            errs.append(f"{tag}: layout {b['layout']} needs a graphic")
        if g:
            if g.get("type") not in GRAPHICS:
                errs.append(f"{tag}: unknown graphic type {g.get('type')}")
            if g.get("src") and not (job / "public" / g["src"]).is_file():
                errs.append(f"{tag}: asset missing public/{g['src']}")
        for s in b.get("sfx", []):
            if not (ROOT / "sfx" / s["file"]).is_file():
                errs.append(f"{tag}: sfx not in library: {s['file']}")
    if beats and (beats[0]["start"] > 0.05 or abs(beats[-1]["end"] - duration) > 0.1):
        errs.append(f"beats must cover 0 -> {duration:.2f}s (got {beats[0]['start']} -> {beats[-1]['end']})")
    m = plan.get("music")
    if m and not (ROOT / "music" / m["file"]).is_file():
        errs.append(f"music not in library: {m['file']}")
    return errs


def finish(raw, final, lufs):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(raw), "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']},aresample=48000")
    run("ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart", final)


def delegate(job, body):
    # A sandboxed agent delegates browser launch to the local editor server.
    service = os.environ.get("REEL_RENDER_SERVICE_URL")
    if not service:
        return False
    req = urllib.request.Request(f"{service}/api/jobs/{job.name}/render", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("REEL_RENDER_TOKEN", "")})
    try:
        with urllib.request.urlopen(req, timeout=1800) as response:
            result = json.load(response)
        print(json.dumps(result))
    except urllib.error.HTTPError as error:
        try:
            message = json.load(error).get("error", "Render service failed")
        except (ValueError, OSError):
            message = "Render service failed"
        die(message, "Check the local editor server render output and retry.")
    return True


def pick_idea(beat, k):
    """Beat with preview idea k applied (0 = the beat's own fields, k = alternatives[k-1])."""
    out = {key: v for key, v in beat.items() if key != "alternatives"}
    if k:
        out.update(beat["alternatives"][k - 1])
    out.pop("label", None)
    return out


def build_props(job, plan, style, tc):
    style = json.loads(json.dumps(style))
    plan = json.loads(json.dumps(plan))
    settings = rj(job / "ui.json") if (job / "ui.json").exists() else {}
    features = settings.get("features", {})
    if features.get("subtitles") is False:
        style["captions"]["enabled"] = False
    if features.get("music") is False:
        plan["music"] = None
    for beat in plan["beats"]:
        if features.get("sfx") is False:
            beat["sfx"] = []
        if features.get("motionGraphics") is False:
            beat.update(layout="talking_head", zoom=1, transition="cut")
            beat.pop("graphic", None)
    errs = validate_plan(job, plan, style, tc["duration"])
    if errs:
        die("beat-plan.json invalid:\n  " + "\n  ".join(errs), "Fix beat-plan.json and re-run.")
    for b in plan["beats"]:
        for s in b.get("sfx", []):
            shutil.copy2(ROOT / "sfx" / s["file"], job / "public" / "sfx" / s["file"])
    if plan.get("music"):
        shutil.copy2(ROOT / "music" / plan["music"]["file"], job / "public" / "music" / plan["music"]["file"])
    return {"style": style, "beats": plan["beats"], "music": plan.get("music"), "words": tc["words"], "duration": tc["duration"]}


def cmd_render(a):
    job = job_dir(a.job)
    if delegate(job, {"preview": bool(a.preview)}):
        return
    plan = rj(job / "beat-plan.json")
    if any(b.get("alternatives") for b in plan["beats"]):
        die("beat-plan.json still has preview alternatives", "Merge the chosen ideas into each beat and remove `alternatives` first.")
    props = build_props(job, plan, rj(job / "style.json"), rj(job / "transcript-cut.json"))
    wj(job / "props.json", props)
    raw = job / "output" / ("preview.mp4" if a.preview else "raw.mp4")
    cmd = ["npx", "remotion", "render", "src/index.ts", "Reel", str(raw), f"--props={job / 'props.json'}",
           f"--public-dir={job / 'public'}", "--codec=h264", "--crf=18", "--log=error", "--gl=angle"]
    if a.preview:
        cmd.append("--scale=0.5")
    r = subprocess.run(cmd, cwd=ROOT / "remotion")
    if r.returncode:
        die("Remotion render failed", "Read the error above; run `npx remotion studio src/index.ts` in remotion/ with the same props to debug.")
    if a.preview:
        print(json.dumps({"preview": str(raw)}))
        return
    final = job / "output" / "final.mp4"
    finish(raw, final, props["style"]["audio"].get("lufs", -14))
    print(json.dumps({"final": str(final)}))


def cmd_storyboard(a):
    """Static stills of every beat (and every alternative idea) -> preview/preview.json for the UI to choose from."""
    job = job_dir(a.job)
    if delegate(job, {"stills": True}):
        return
    plan, style, tc = rj(job / "beat-plan.json"), rj(job / "style.json"), rj(job / "transcript-cut.json")
    beats = plan["beats"]
    ideas = 1 + max(len(b.get("alternatives", [])) for b in beats)
    out = job / "preview"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    fps, last = style["canvas"]["fps"], max(0, round(tc["duration"] * style["canvas"]["fps"]) - 1)
    # ponytail: one still at 75% through each beat, after entrances settle; a burst per beat if one frame misleads
    frame = lambda b: min(last, round((b["start"] + 0.75 * (b["end"] - b["start"])) * fps))
    spec, board = [], [{"id": b["id"], "start": b["start"], "end": b["end"], "text": b.get("text", ""), "ideas": []} for b in beats]
    for k in range(ideas):
        variant = {**plan, "beats": [pick_idea(b, k if k <= len(b.get("alternatives", [])) else 0) for b in beats]}
        frames = []
        for i, b in enumerate(beats):
            if k > len(b.get("alternatives", [])):
                continue
            idea, still = ({**b, **b["alternatives"][k - 1]} if k else b), f"preview/b{b['id']}-{k + 1}.jpg"
            frames.append({"frame": frame(b), "out": str(job / still)})
            board[i]["ideas"].append({"label": idea.get("label", ""), "layout": idea["layout"], "type": (idea.get("graphic") or {}).get("type"), "still": still})
        spec.append({"props": build_props(job, variant, style, tc), "frames": frames})
    wj(out / "spec.json", spec)
    r = subprocess.run(["node", "stills.mjs", str(job / "public"), str(out / "spec.json")], cwd=ROOT / "remotion")
    if r.returncode:
        die("Still render failed", "Read the error above and fix beat-plan.json.")
    (out / "spec.json").unlink()
    wj(out / "preview.json", {"ideas": ideas, "beats": board})
    print(json.dumps({"preview": str(out / "preview.json"), "stills": sum(len(b["ideas"]) for b in board)}))


def cmd_graphics(a):
    """One still of every built-in graphic type in a style -> <out>/<type>.jpg, for the UI's Graphics library."""
    d = find_style(a.style) or die(f"unknown style '{a.style}'")
    style, lib = load_style(d), rj(ROOT / "app" / "graphics-library.json")
    style["captions"]["enabled"] = False
    if a.aspect == "16:9":
        style["canvas"].update(width=1920, height=1080)
        style["safe_zone"] = {"top": 60, "bottom": 100, "right": 80}
    out = Path(a.out).resolve()
    shutil.rmtree(out, ignore_errors=True)
    pub = out / "public"
    (pub / "style").mkdir(parents=True)
    if (d / "assets").exists():
        shutil.copytree(d / "assets", pub / "style", dirs_exist_ok=True)
    w, h = style["canvas"]["width"], style["canvas"]["height"]
    run("ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"gradients=s={w}x{h}:d=5:speed=0.02:c0=0x3b4a6b:c1=0x8a7fb8", "-pix_fmt", "yuv420p", pub / "sample.mp4")
    run("ffmpeg", "-v", "error", "-ss", "1", "-i", pub / "sample.mp4", "-frames:v", "1", pub / "sample.png")
    shutil.copy2(pub / "sample.mp4", pub / "cut.mp4")
    (pub / "assets").mkdir()
    for n in (1, 3, 6):  # editor and timeline scenes read these
        run("ffmpeg", "-v", "error", "-ss", str(n / 2), "-i", pub / "sample.mp4", "-frames:v", "1", pub / "assets" / f"still_{n}.jpg")
    fps, length = style["canvas"]["fps"], 3
    beats = [{"id": i + 1, "start": i * length, "end": (i + 1) * length - 0.0001, "text": "", "layout": g.get("layout", "fullscreen"),
              "transition": "cut", "graphic": g["graphic"], "captions": False} for i, g in enumerate(lib)]
    props = {"style": style, "beats": beats, "words": [], "music": None, "duration": len(beats) * length}
    # ponytail: still 2.6s into each 3s beat, after entrances and marks settle
    frames = [{"frame": round((b["start"] + 2.6) * fps), "out": str(out / f"{g['type']}.jpg")} for b, g in zip(beats, lib)]
    wj(out / "spec.json", [{"props": props, "frames": frames}])
    r = subprocess.run(["node", "stills.mjs", str(pub), str(out / "spec.json")], cwd=ROOT / "remotion")
    shutil.rmtree(pub)
    if r.returncode:
        die("Still render failed", "Read the error above.")
    print(json.dumps({"stills": len(frames), "out": str(out)}))


HF = ROOT / "hyperframes"
HF_CLI = ["npx", "--yes", "hyperframes@0.6.70"]


def hf_templates():
    """Every HyperFrames template Frame Pilot knows: imported, captured and user-made. Paths are relative to hyperframes/."""
    index = rj(HF / "templates" / "templates.json") if (HF / "templates" / "templates.json").exists() else {}
    out = [{**t, "path": "templates/" + t["path"].removeprefix("templates/")} for k in ("templates", "mg-templates") for t in index.get(k, [])]
    for name, extra in (("captured-templates.json", {"captured": True}), ("custom-templates.json", {"custom": True})):
        for t in (rj(HF / name) if (HF / name).exists() else []):
            out.append({**t, **extra, "description": t.get("description") or t.get("desc", ""),
                        "path": "templates/" + t["path"].removeprefix("Assets/").removeprefix("templates/")})
    return out


def cmd_template(a):
    """Copy a HyperFrames template into <job>/hf/<name>/ for one moment of the cut, ready for its copy to be edited."""
    job = job_dir(a.job)
    t = next((t for t in hf_templates() if t["id"] == a.template), None) or die(f"unknown template {a.template}", "List them in hyperframes/templates/templates.json or custom-templates.json.")
    canvas = rj(job / "style.json")["canvas"]
    tech = t.get("technical") or {}
    if ((tech.get("height", 1080) > tech.get("width", 1920)) != (canvas["height"] > canvas["width"])):
        die(f"template {a.template} is {tech.get('width')}x{tech.get('height')} but this job is {canvas['width']}x{canvas['height']}", "Pick a template made for this format.")
    if not re.fullmatch(r"[a-z0-9-]+", a.name):
        die("name must be lowercase letters, digits and dashes")
    src, d, dur = HF / t["path"], job / "hf" / a.name, round(a.end - a.start, 3)
    shutil.rmtree(d, ignore_errors=True)
    (d / "assets").mkdir(parents=True)
    html = src.read_text()
    html = re.sub(r"assets/placeholder-video\.mp4", "assets/footage.mp4", html)
    html = re.sub(r"\s+poster=([\"'])assets/talking-head-(placeholder|cutout)\.png\1", "", html)
    html = re.sub(r"\s*<img\b[^>]*\bdata-preview-only\b[^>]*/?>", "", html)
    html = re.sub(r"([\"'(])(?:\.\./)+Icons/", r"\1assets/icons/", html)
    html = re.sub(r"([\"'(])(?:\.\./)*vendor/gsap\.min\.js", r"\1vendor/gsap.min.js", html)
    html = re.sub(r"(?:\.\./)+assets/", "assets/", html)
    html = re.sub(r"\s*<audio\b[^>]*\bsrc=[\"']assets/footage\.mp4[\"'][^>]*>\s*</audio>", "", html)  # dialogue comes from the main track
    html = re.sub(r"\s*<!--\s*hf-autoplay\s*-->\s*<script\b[^>]*>[\s\S]*?</script>", "", html)
    html = re.sub(r"(<[^>]*\bdata-composition-id=[\"'][^\"']+[\"'][^>]*\bdata-duration=[\"'])[\d.]+", rf"\g<1>{dur}", html)
    html = re.sub(r"(<video\b[^>]*\bsrc=[\"']assets/footage\.mp4[\"'][^>]*\bdata-duration=[\"'])[\d.]+", rf"\g<1>{dur}", html)
    (d / "index.html").write_text(html)
    shutil.copytree(HF / "templates" / "vendor", d / "vendor")
    asset_dirs = [(HF / "templates" / "assets", d / "assets"), (HF / "Icons", d / "assets" / "icons")]
    if "News Scenes" in t["path"]:
        asset_dirs.append((HF / "templates" / "News Scenes" / "assets", d / "assets"))
    for s_dir, d_dir in asset_dirs:
        if s_dir.exists():
            shutil.copytree(s_dir, d_dir, dirs_exist_ok=True, copy_function=os.link)
    if "assets/footage.mp4" in html:
        (d / "assets" / "footage.mp4").unlink(missing_ok=True)
        w, h = tech.get("width", canvas["width"]), tech.get("height", canvas["height"])
        run("ffmpeg", "-v", "error", "-y", "-ss", a.start, "-t", dur, "-i", job / "public" / "cut.mp4", "-an",
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "30", d / "assets" / "footage.mp4")
    (d / "TEMPLATE.md").write_text("\n".join([
        f"# {a.name} · {t['name']} ({t['id']})", "",
        f"Plays {a.start}s -> {a.end}s of the cut ({dur}s). {t.get('description', '')}", "",
        "Edit ONLY these slots in index.html; keep structure, CSS and GSAP as shipped:", *[f"- {r}" for r in t.get("replace") or ["on-screen copy"]], "",
        f"Retime entrance/exit so everything has animated out by {dur}s. assets/footage.mp4 (if used) is already this moment of the cut.",
        f"Then: reel.py template-render <job> {a.name}, and use graphic {{\"type\": \"template\", \"src\": \"assets/tpl-{a.name}.mov\"}} on a beat spanning exactly {a.start}-{a.end}.",
        "Layout: \"overlay\" if the template is transparent over the speaker (lower thirds, captions), \"fullscreen\" if it fills the frame.",
    ]))
    print(json.dumps({"dir": str(d), "duration": dur, "template": t["id"]}))


def cmd_template_render(a):
    """Render <job>/hf/<name>/ to public/assets/tpl-<name>.mov (ProRes 4444, alpha kept) for a `template` graphic."""
    job = job_dir(a.job)
    if delegate(job, {"template": a.name}):
        return
    d, out = job / "hf" / a.name, job / "public" / "assets" / f"tpl-{a.name}.mov"
    if not (d / "index.html").is_file():
        die(f"no prepared template {a.name}", f"Run reel.py template <job> <template-id> {a.name} <start> <end> first.")
    r = subprocess.run([*HF_CLI, "render", str(d), "--format", "mov", "--quality", "high", "-o", str(out)], cwd=d)
    if r.returncode or not out.is_file():
        die("HyperFrames render failed", f"Run `npx hyperframes lint` in {d} and fix index.html.")
    print(json.dumps({"src": f"assets/tpl-{a.name}.mov"}))


GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"


def cmd_hf_import(a):
    """Copy HyperFrames templates (and the files they reference outside the folder) into hyperframes/, so they work without the source."""
    src, dst = Path(a.source).expanduser() / "Assets", ROOT / "hyperframes"
    if not (src / "templates" / "templates.json").is_file():
        die(f"no templates.json under {src / 'templates'}", "Pass the Hyperframes project folder, e.g. ~/Documents/CC/Hyperframes.")
    index = dst / "templates" / "templates.json"
    old = rj(index) if index.exists() else {}
    # ponytail: copies over existing files and never deletes, so templates removed from the source stay here
    shutil.copytree(src / "templates", dst / "templates", dirs_exist_ok=True)
    new = rj(index)
    for k, rows in old.items():
        if isinstance(rows, list) and isinstance(new.get(k), list):
            ids = {t.get("id") for t in new[k]}
            new[k] += [t for t in rows if t.get("id") not in ids]
    wj(index, new)
    pages = [f for f in (dst / "templates").rglob("*.html")]
    outside = set()
    for f in pages:
        for ref in re.findall(r"[\"'(](\.\./[^\"')]+)", f.read_text(errors="ignore")):
            target = (f.parent / ref).resolve()
            if not target.is_relative_to(dst / "templates"):
                outside.add(target.relative_to(dst.resolve()))
    for rel in outside:
        if (src / rel).is_file():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, dst / rel)
    vendor = dst / "templates" / "vendor" / "gsap.min.js"
    if not vendor.exists():
        vendor.parent.mkdir(exist_ok=True)
        with urllib.request.urlopen(GSAP_CDN, context=https_context()) as r:
            vendor.write_bytes(r.read())
    for f in pages:
        t = f.read_text(errors="ignore")
        if GSAP_CDN in t:
            f.write_text(t.replace(GSAP_CDN, os.path.relpath(vendor, f.parent)))
    captured = Path(a.source).expanduser() / "captures" / "captured-templates.json"
    if captured.is_file():
        old = {t["id"]: t for t in (rj(dst / "captured-templates.json") if (dst / "captured-templates.json").exists() else [])}
        wj(dst / "captured-templates.json", list({**old, **{t["id"]: t for t in rj(captured)}}.values()))
    print(json.dumps({"pages": len(pages), "outside_files": len(outside), "dir": str(dst)}))


# ---------- verify ----------

def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    grab = lambda label: float(re.search(label + r":\s+(-?[\d.]+|-inf)", summary).group(1).replace("-inf", "-99"))
    return {"integrated_lufs": grab(r"I"), "lra": grab(r"LRA"), "true_peak_dbtp": grab(r"Peak")}


def cmd_verify(a):
    job = job_dir(a.job)
    video = job / "output" / a.file
    if not video.exists():
        die(f"{video} not found", "Run render first.")
    style = rj(job / "style.json")
    beats = rj(job / "beat-plan.json")["beats"]
    info = probe(video)
    times = {round(t * a.every, 2) for t in range(int(info["duration"] / a.every))}
    for b in beats:
        times |= {round(b["start"] + 0.25, 2), round((b["start"] + b["end"]) / 2, 2), round(max(b["end"] - 0.2, b["start"]), 2)}
    times = sorted(t for t in times if t < info["duration"] - 0.05)
    deduped = [t for i, t in enumerate(times) if i == 0 or t - times[i - 1] >= 0.2]
    safe = style.get("safe_zone", {"top": 220, "bottom": 420, "right": 130})
    c = style["canvas"]
    res = sheets(video, deduped, job / "verify", 360, 640, c["fps"], (safe["top"], safe["bottom"], safe["right"]))
    issues = []
    if (info.get("width"), info.get("height")) != (c["width"], c["height"]):
        issues.append(f"resolution {info.get('width')}x{info.get('height')} != {c['width']}x{c['height']}")
    if abs(info.get("fps", 0) - c["fps"]) > 0.01:
        issues.append(f"fps {info.get('fps')} != {c['fps']}")
    if info.get("codec") != "h264":
        issues.append(f"codec {info.get('codec')} != h264")
    expected = rj(job / "transcript-cut.json")["duration"]
    if abs(info["duration"] - expected) > 0.25:
        issues.append(f"duration {info['duration']:.2f}s != expected {expected:.2f}s")
    loud = loudness(video)
    target = style["audio"].get("lufs", -14)
    if abs(loud["integrated_lufs"] - target) > 1.5:
        issues.append(f"loudness {loud['integrated_lufs']} LUFS, target {target}")
    if loud["true_peak_dbtp"] > -0.5:
        issues.append(f"true peak {loud['true_peak_dbtp']} dBTP (clipping risk)")
    report = {"file": str(video), "probe": info, "loudness": loud, "auto_issues": issues,
              "sheets": [{"sheet": s, "times": t} for s, t in res],
              "beat_index": [{"id": b.get("id"), "start": b["start"], "end": b["end"], "layout": b["layout"],
                              "graphic": (b.get("graphic") or {}).get("type")} for b in beats]}
    wj(job / "verify" / "report.json", report)
    print(json.dumps({"auto_issues": issues, "loudness": loud, "sheets": len(res), "report": str(job / "verify" / "report.json")}, indent=1))


# ---------- assets ----------

def cmd_search(a):
    key = env_key("BRAVE_API_KEY") or die("BRAVE_API_KEY not set", "Set it in your environment or the env block of config.local.json.")
    q = urllib.parse.urlencode({"q": a.query, "count": a.count, "safesearch": "strict"})
    req = urllib.request.Request(f"https://api.search.brave.com/res/v1/images/search?{q}",
                                 headers={"X-Subscription-Token": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30, context=https_context()) as r:
        res = json.load(r)
    rows = [{"title": x.get("title"), "url": x.get("properties", {}).get("url"), "page": x.get("url"),
             "w": x.get("properties", {}).get("width") or x.get("width"), "h": x.get("properties", {}).get("height") or x.get("height")}
            for x in res.get("results", [])]
    print(json.dumps(rows, indent=1))


def log_asset(job, name, source):
    p = job / "public" / "assets" / "sources.json"
    log = rj(p) if p.exists() else {}
    log[name] = source
    wj(p, log)


def cmd_fetch(a):
    job = job_dir(a.job)
    req = urllib.request.Request(a.url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=https_context()) as r:
        ctype, data = r.headers.get("Content-Type", ""), r.read()
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/svg+xml": ".svg", "image/gif": ".gif"}
    e = next((v for k, v in ext.items() if ctype.startswith(k)), None)
    if not e:
        die(f"not an image ({ctype or 'no content-type'}): {a.url}", "Pick a direct image URL from the search results.")
    if len(data) < 1500:
        die(f"image too small ({len(data)} bytes)", "Pick a higher-resolution result.")
    name = Path(a.name).stem + e
    (job / "public" / "assets" / name).write_bytes(data)
    log_asset(job, name, a.url)
    dims = {}
    if e != ".svg":
        p = probe(job / "public" / "assets" / name)
        dims = {"w": p.get("width"), "h": p.get("height")}
    print(json.dumps({"src": f"assets/{name}", **dims}))


def cmd_shot(a):
    job = job_dir(a.job)
    if not Path(CHROME).exists():
        die("Google Chrome not found", "Install Chrome, or capture the screenshot with the Playwright MCP and save it into public/assets.")
    name = Path(a.name).stem + ".png"
    out = job / "public" / "assets" / name
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={a.w},{a.h}",
                        "--timeout=12000", f"--screenshot={out}", a.url], capture_output=True, timeout=45)
    except subprocess.TimeoutExpired:
        pass
    if not out.exists():
        die(f"screenshot of {a.url} failed or timed out", "Capture it with the Playwright MCP and save it into public/assets.")
    log_asset(job, name, a.url)
    print(json.dumps({"src": f"assets/{name}", "w": a.w, "h": a.h}))


# ---------- audio library ----------

def cmd_lib_import(a):
    src, lib = Path(a.folder).expanduser(), ROOT / a.kind
    dpath = lib / "dictionary.json"
    dic = rj(dpath) if dpath.exists() else []
    known = {e["file"] for e in dic}
    added = 0
    for f in sorted(src.rglob("*")):
        if f.suffix.lower() in AUDIO_EXT and f.name not in known:
            shutil.copy2(f, lib / f.name)
            dur = float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f, capture=True).stdout.strip() or 0)
            entry = {"file": f.name, "duration": round(dur, 2), "tags": [], "mood": "", "energy": "", "use": ""}
            if a.kind == "music":
                entry["tempo"] = ""
            dic.append(entry)
            added += 1
    wj(dpath, dic)
    print(json.dumps({"added": added, "total": len(dic), "dictionary": str(dpath)}))


def cmd_lib_check(a):
    for kind in ("music", "sfx"):
        p = ROOT / kind / "dictionary.json"
        dic = rj(p) if p.exists() else []
        missing = [e["file"] for e in dic if not (ROOT / kind / e["file"]).is_file()]
        blank = [e["file"] for e in dic if not (e.get("mood") and e.get("use"))]
        print(json.dumps({kind: len(dic), "missing_files": missing, "undescribed": blank}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("styles").set_defaults(f=cmd_styles)
    x = sp.add_parser("style-check"); x.add_argument("name"); x.set_defaults(f=cmd_style_check)
    x = sp.add_parser("frames"); x.add_argument("video"); x.add_argument("out_dir"); x.add_argument("--every", type=float, default=1.0); x.set_defaults(f=cmd_frames)
    x = sp.add_parser("ingest"); x.add_argument("video"); x.add_argument("style", nargs="?", default=""); x.add_argument("--no-style", action="store_true"); x.add_argument("--id"); x.set_defaults(f=cmd_ingest)
    x = sp.add_parser("transcribe"); x.add_argument("job"); x.set_defaults(f=cmd_transcribe)
    x = sp.add_parser("sentences"); x.add_argument("job"); x.set_defaults(f=cmd_sentences)
    x = sp.add_parser("cut"); x.add_argument("job"); x.add_argument("--gap", type=float, default=0.4); x.add_argument("--pad", type=float, default=0.12)
    x.add_argument("--av-offset", type=float, default=0.0, help="seconds the source picture lags its audio (fixes lip sync)")
    x.add_argument("--eq", default="", help="ffmpeg eq params for the speaker, e.g. brightness=0.05:gamma=1.1"); x.set_defaults(f=cmd_cut)
    x = sp.add_parser("render"); x.add_argument("job"); x.add_argument("--preview", action="store_true"); x.set_defaults(f=cmd_render)
    x = sp.add_parser("storyboard"); x.add_argument("job"); x.set_defaults(f=cmd_storyboard)
    x = sp.add_parser("graphics"); x.add_argument("style"); x.add_argument("out"); x.add_argument("--aspect", choices=["9:16", "16:9"], default="9:16"); x.set_defaults(f=cmd_graphics)
    x = sp.add_parser("template"); x.add_argument("job"); x.add_argument("template"); x.add_argument("name"); x.add_argument("start", type=float); x.add_argument("end", type=float); x.set_defaults(f=cmd_template)
    x = sp.add_parser("template-render"); x.add_argument("job"); x.add_argument("name"); x.set_defaults(f=cmd_template_render)
    x = sp.add_parser("hf-import"); x.add_argument("source", nargs="?", default=str(ROOT.parent / "Hyperframes")); x.set_defaults(f=cmd_hf_import)
    x = sp.add_parser("verify"); x.add_argument("job"); x.add_argument("--file", default="final.mp4"); x.add_argument("--every", type=float, default=1.5); x.set_defaults(f=cmd_verify)
    x = sp.add_parser("search"); x.add_argument("query"); x.add_argument("--count", type=int, default=8); x.set_defaults(f=cmd_search)
    x = sp.add_parser("fetch"); x.add_argument("job"); x.add_argument("url"); x.add_argument("name"); x.set_defaults(f=cmd_fetch)
    x = sp.add_parser("shot"); x.add_argument("job"); x.add_argument("url"); x.add_argument("name"); x.add_argument("--w", type=int, default=1080); x.add_argument("--h", type=int, default=1350); x.set_defaults(f=cmd_shot)
    x = sp.add_parser("lib-import"); x.add_argument("folder"); x.add_argument("kind", choices=["music", "sfx"]); x.set_defaults(f=cmd_lib_import)
    sp.add_parser("lib-check").set_defaults(f=cmd_lib_check)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
