import test from 'node:test';
import assert from 'node:assert/strict';
import { creationSettings, settingsPrompt } from '../creation.mjs';

test('existing jobs retain portrait and all editing features by default', () => {
  const s = creationSettings({});
  assert.equal(s.aspectRatio, '9:16');
  assert.ok(Object.values(s.features).every(Boolean));
  assert.deepEqual(s.transcriptEdits, []);
});
test('landscape, disabled features, references and source-word instructions survive normalization', () => {
  const body = { aspectRatio: '16:9', features: {roughCut:false,subtitles:false,motionGraphics:false,sfx:false,music:false}, inspiration:'/inspiration.mp4', references:['/ref.png','/ref.mp4'], transcriptEdits:[{from:3,to:6,instruction:'  Show a diagram  '}] };
  const s = creationSettings(body);
  assert.deepEqual(s.features, body.features);
  assert.deepEqual(s.references, body.references);
  assert.equal(s.transcriptEdits[0].instruction, 'Show a diagram');
  const prompt = settingsPrompt(body);
  assert.match(prompt, /1920×1080 landscape/);
  assert.match(prompt, /Rough cut OFF/);
  assert.match(prompt, /ORIGINAL source word indices/);
  assert.match(prompt, /inspiration.mp4/);
});
test('rejects malformed formats, feature flags and transcript ranges', () => {
  for (const body of [{aspectRatio:'1:1'}, {features:{music:'false'}}, {references:'file'}, {transcriptEdits:[{from:5,to:2,instruction:'remove'}]}, {transcriptEdits:[{from:0,to:2,instruction:''}]}]) assert.throws(() => creationSettings(body));
});
test('a transcript instruction can name a HyperFrames template without text', () => {
  const s = creationSettings({ transcriptEdits: [{ from: 1, to: 4, template: 'mg-wrong-stamp' }, { from: 6, to: 7, instruction: 'cut this' }] });
  assert.deepEqual(s.transcriptEdits[0], { from: 1, to: 4, instruction: '', template: 'mg-wrong-stamp' });
  assert.equal(s.transcriptEdits[1].template, undefined);
  assert.match(settingsPrompt({ transcriptEdits: s.transcriptEdits }), /HyperFrames templates/);
  assert.doesNotMatch(settingsPrompt({ transcriptEdits: [{ from: 1, to: 2, instruction: 'x' }] }), /HyperFrames templates/);
  assert.throws(() => creationSettings({ transcriptEdits: [{ from: 1, to: 2, template: '../etc' }] }));
});
