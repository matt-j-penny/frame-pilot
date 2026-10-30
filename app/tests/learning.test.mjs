import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { applyLessonsToGuide, snapshotStyle, listHistory, restoreHistory, recordLearning, learningStats } from "../learning.mjs";

const prose = "# Style\n\n## Subtitles\nWhite.\n\n## Machine block\n<<SETTINGS>>\n\n## Changelog\n- 2026-01-01: Created.\n";
const config = { captions: { y: { split: 0.5 } }, fonts: { caption: { size: 64 } } };

test("applies setting changes and learned rules, logs them in the changelog", () => {
  const out = applyLessonsToGuide(prose, config, [
    { id: "l1", title: "Smaller captions", setting: { path: "fonts.caption.size", from: 64, to: 56 } },
    { id: "l2", title: "No graphic on the hook", rule: "Keep the first beat as plain talking head." },
  ], '"clip.mov" (v2)', "2026-10-17");
  assert.equal(out.config.fonts.caption.size, 56);
  assert.equal(config.fonts.caption.size, 64, "input config is not mutated");
  assert.match(out.prose, /## Learned rules\n.*\n- Keep the first beat as plain talking head\. _\(learned from "clip\.mov" \(v2\)\)_/);
  assert.ok(out.prose.indexOf("## Learned rules") < out.prose.indexOf("## Machine block"));
  assert.match(out.prose, /## Changelog\n- 2026-10-17: Lessons from "clip\.mov" \(v2\): fonts\.caption\.size 64 → 56; rule: Keep the first beat/);
  assert.deepEqual(out.errors, []);
});

test("rejects unknown setting paths without applying them", () => {
  const out = applyLessonsToGuide(prose, config, [{ id: "l1", title: "Bad", setting: { path: "captions.nope", from: 1, to: 2 } }], "x", "2026-10-17");
  assert.equal(out.applied.length, 0);
  assert.equal(out.errors.length, 1);
  assert.equal(out.prose, prose);
});

test("second learned rule appends to the existing section", () => {
  const first = applyLessonsToGuide(prose, config, [{ id: "a", title: "A", rule: "Rule A." }], "one", "2026-10-17");
  const second = applyLessonsToGuide(first.prose, first.config, [{ id: "b", title: "B", rule: "Rule B." }], "two", "2026-10-18");
  assert.equal(second.prose.match(/## Learned rules/g).length, 1);
  assert.match(second.prose, /## Learned rules\nRules learned[^\n]*\n- Rule A\.[^\n]*\n- Rule B\.[^\n]*\n\n## Machine block/);
  assert.match(second.prose, /Lessons from two: rule: Rule B\.\n/);
});

test("snapshots and restores the style guide", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "style-"));
  fs.writeFileSync(path.join(dir, "style-guide.md"), "v1");
  const file = snapshotStyle(dir, "Before change");
  fs.writeFileSync(path.join(dir, "style-guide.md"), "v2");
  assert.equal(listHistory(dir)[0].reason, "Before change");
  assert.equal(restoreHistory(dir, file), null);
  assert.equal(fs.readFileSync(path.join(dir, "style-guide.md"), "utf8"), "v1");
  assert.equal(listHistory(dir).length, 2, "restoring snapshots the current version first");
});

test("observations count across approved videos", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "style-"));
  recordLearning(dir, { job: "a", title: "A", revisions: 3, applied: [], observations: [{ key: "smaller-captions", title: "Smaller captions" }] });
  recordLearning(dir, { job: "b", title: "B", revisions: 1, applied: [], observations: [{ key: "smaller-captions", title: "Smaller captions" }] });
  const stats = learningStats(dir);
  assert.equal(stats.approved, 2);
  assert.equal(stats.avgChanges, 2);
  assert.equal(stats.observations[0].count, 2);
});
