// Learning loop: approved edits become examples, reviewed lessons update the style, every change is versioned.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const rj = (p, d = null) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return d; } };
const wj = (p, d) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(d, null, 1)); };
const stamp = () => new Date().toISOString().replace(/[:.]/g, "-");

// ---------- style history ----------

export function snapshotStyle(dir, reason) {
  const guide = path.join(dir, "style-guide.md");
  if (!fs.existsSync(guide)) return null;
  const file = `${stamp()}.md`;
  fs.mkdirSync(path.join(dir, "history"), { recursive: true });
  fs.copyFileSync(guide, path.join(dir, "history", file));
  const index = rj(path.join(dir, "history", "index.json"), []);
  index.unshift({ file, at: Date.now(), reason });
  wj(path.join(dir, "history", "index.json"), index.slice(0, 100));
  return file;
}

export const listHistory = (dir) => rj(path.join(dir, "history", "index.json"), []).filter((h) => fs.existsSync(path.join(dir, "history", h.file)));

export function restoreHistory(dir, file) {
  const entry = listHistory(dir).find((h) => h.file === file);
  if (!entry) return "That version no longer exists.";
  snapshotStyle(dir, `Before restoring the version from ${new Date(entry.at).toLocaleString()}`);
  fs.copyFileSync(path.join(dir, "history", file), path.join(dir, "style-guide.md"));
  return null;
}

// ---------- lessons ----------

const getAt = (obj, p) => p.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
function setAt(obj, p, v) {
  const keys = p.split(".");
  const last = keys.pop();
  const parent = keys.reduce((o, k) => (o == null ? undefined : o[k]), obj);
  if (parent == null || typeof parent !== "object" || !(last in parent)) return false;
  parent[last] = v;
  return true;
}

// Pure: apply accepted lessons to a style's rules text and settings.
export function applyLessonsToGuide(prose, config, lessons, source, date) {
  const cfg = JSON.parse(JSON.stringify(config));
  const applied = [], errors = [], rules = [];
  for (const l of lessons) {
    if (l.setting?.path) {
      if (getAt(cfg, l.setting.path) === undefined) { errors.push(`${l.title}: unknown setting ${l.setting.path}`); continue; }
      const from = getAt(cfg, l.setting.path);
      if (!setAt(cfg, l.setting.path, l.setting.to)) { errors.push(`${l.title}: couldn't set ${l.setting.path}`); continue; }
      applied.push(`${l.setting.path} ${JSON.stringify(from)} → ${JSON.stringify(l.setting.to)}`);
    }
    if (l.rule?.trim()) { rules.push(l.rule.trim()); if (!l.setting?.path) applied.push(`rule: ${l.rule.trim().replace(/\.$/, "")}`); }
  }
  let out = prose;
  if (rules.length) {
    const bullets = rules.map((r) => `- ${r} _(learned from ${source})_`).join("\n");
    const start = out.search(/^## Learned rules\s*$/m);
    if (start >= 0) {
      const next = out.slice(start + 1).search(/^## /m);
      const end = next >= 0 ? start + 1 + next : out.length;
      const section = out.slice(start, end).trimEnd();
      out = `${out.slice(0, start)}${section}\n${bullets}\n\n${out.slice(end)}`;
    } else {
      const section = `## Learned rules\nRules learned from approved edits. They override older rules above where they conflict.\n${bullets}\n\n`;
      const at = out.search(/^## Machine block/m);
      out = at >= 0 ? out.slice(0, at) + section + out.slice(at) : `${out.trimEnd()}\n\n${section}`;
    }
  }
  if (applied.length) {
    const line = `- ${date}: Lessons from ${source}: ${applied.join("; ")}.\n`;
    out = /^## Changelog\s*$/m.test(out) ? out.replace(/^## Changelog\s*\n/m, (h) => h + line) : `${out.trimEnd()}\n\n## Changelog\n${line}`;
  }
  return { prose: out, config: cfg, applied, errors };
}

// ---------- examples & learning log ----------

export function saveExample(styleDir, jobDir, job, version) {
  const dest = path.join(styleDir, "examples", job.id);
  fs.mkdirSync(dest, { recursive: true });
  for (const f of ["beat-plan.json", "cut-log.md"]) if (fs.existsSync(path.join(jobDir, f))) fs.copyFileSync(path.join(jobDir, f), path.join(dest, f));
  const video = path.join(jobDir, version.file);
  spawnSync("ffmpeg", ["-v", "error", "-y", "-ss", "1.5", "-i", video, "-frames:v", "1", "-vf", "scale=270:-2", path.join(dest, "poster.jpg")]);
  const revisions = job.runs.filter((r) => r.kind === "revise" && r.status === "done").map((r) => r.note);
  fs.writeFileSync(path.join(dest, "notes.md"), `# Approved example: ${job.title}

- Approved: ${new Date().toISOString().slice(0, 10)}, version v${version.n}
- Director's notes: ${job.direction?.trim() || "none"}
- Changes requested before approval (${revisions.length}): ${revisions.length ? revisions.map((r) => `"${r}"`).join("; ") : "none, the first edit was approved as-is"}

The user approved this edit for this style. \`beat-plan.json\` is the final plan (times are on that video's cut timeline).
`);
  const index = rj(path.join(styleDir, "examples", "index.json"), []).filter((e) => e.job !== job.id);
  index.unshift({ job: job.id, title: job.title, version: version.n, revisions: revisions.length, at: Date.now() });
  wj(path.join(styleDir, "examples", "index.json"), index);
  return revisions.length;
}

export const listExamples = (styleDir) => rj(path.join(styleDir, "examples", "index.json"), []).filter((e) => fs.existsSync(path.join(styleDir, "examples", e.job)));

export function removeExample(styleDir, jobId) {
  fs.rmSync(path.join(styleDir, "examples", jobId), { recursive: true, force: true });
  wj(path.join(styleDir, "examples", "index.json"), rj(path.join(styleDir, "examples", "index.json"), []).filter((e) => e.job !== jobId));
}

export const readLearning = (styleDir) => rj(path.join(styleDir, "learning.json"), { approvals: [], observations: [] });

export function recordLearning(styleDir, { job, title, revisions, applied, observations }) {
  const log = readLearning(styleDir);
  log.approvals = [{ job, title, revisions, applied, at: Date.now() }, ...log.approvals.filter((a) => a.job !== job)];
  for (const o of observations) {
    const found = log.observations.find((x) => x.key === o.key);
    if (found) { if (!found.jobs.includes(job)) { found.jobs.push(job); found.count = found.jobs.length; } found.title = o.title; found.last = Date.now(); }
    else log.observations.push({ key: o.key, title: o.title, why: o.why, count: 1, jobs: [job], first: Date.now(), last: Date.now() });
  }
  wj(path.join(styleDir, "learning.json"), log);
  return log;
}

export function dropObservations(styleDir, keys) {
  const log = readLearning(styleDir);
  log.observations = log.observations.filter((o) => !keys.includes(o.key));
  wj(path.join(styleDir, "learning.json"), log);
}

export function learningStats(styleDir) {
  const log = readLearning(styleDir);
  const a = log.approvals;
  const avg = (xs) => (xs.length ? Math.round((xs.reduce((s, x) => s + x.revisions, 0) / xs.length) * 10) / 10 : null);
  return { approved: a.length, avgChanges: avg(a), recentAvgChanges: avg(a.slice(0, 5)), observations: log.observations.sort((x, y) => y.count - x.count) };
}

export function lessonsPrompt({ job, jobDir, styleName, styleDir, version, learning }) {
  const revisions = job.runs.filter((r) => r.kind === "revise" && r.status === "done").map((r, i) => `${i + 1}. "${r.note}"`);
  const obs = learning.observations.map((o) => `- key "${o.key}" (seen ${o.count}x): ${o.title}`);
  return `The user approved version v${version} of this Frame Pilot job: ${jobDir}
Style: ${styleName} (folder ${styleDir}, settings in the \`\`\`json reel-style block of style-guide.md).

Work out what this edit teaches about the style, so the next video needs fewer changes. Do NOT modify any file except writing ${path.join(jobDir, "lessons.json")}. Do not re-render.

Evidence to read:
- Director's notes for this video: ${job.direction?.trim() || "none"}
- The user's change requests, in order:
${revisions.length ? revisions.join("\n") : "(none: the first edit was approved as-is)"}
- versions/v1/ holds the first version's beat-plan.json and style.json (if present); compare with the approved beat-plan.json and style.json in the job folder.
- Differences between the job's style.json and the saved style's settings are per-video overrides made during this edit.
- ui.json run summaries and verify/report.json show what verification had to fix by itself.
- Observations from earlier approved videos of this style:
${obs.length ? obs.join("\n") : "(none yet)"}

Classify every lesson:
- "style": a general preference that should apply to every future video in this style.
- "observation": might be a real preference, might be a one-off. If it matches an earlier observation, reuse its key. An observation seen before (count >= 1) that shows up again should be promoted to "style".
- "specific": only about this video's content (a particular logo, sentence, timestamp).

Write ${path.join(jobDir, "lessons.json")} as:
{"summary": "one or two sentences", "lessons": [{"id": "l1", "kind": "style|observation|specific", "key": "short-kebab-key", "title": "plain-English one-liner", "why": "the evidence", "setting": {"path": "dotted.path.in.reel-style.json", "from": <current saved value>, "to": <new value>} or null, "rule": "one sentence for the style's written rules" or null}]}

For "style" lessons give a setting change whenever it maps to a reel-style value (the path must already exist; "from" must equal the saved value), and/or a rule sentence for judgement calls. Keep "specific" lessons short. If nothing needed changing, return an empty lessons list and say the style worked as-is. End with a one-sentence summary.`;
}
