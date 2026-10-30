import { test } from 'node:test';
import assert from 'node:assert/strict';
import { styleOutcome } from '../style-outcome.mjs';
test('connection loss after a completed, saved, validated style does not discard successful output', () => {
  const input = { ok: false, summary: 'Reconnecting... 5/5 (stream disconnected before completion)', changed: true, validated: true, lastMessage: 'Completed reference analysis, style guide and settings.' };
  const recovered = styleOutcome(input);
  assert.equal(recovered.status, 'done');
  assert.equal(recovered.summary, input.lastMessage);
  assert.match(recovered.warning, /connection interrupted/);
  for (const overrides of [{ validated: false }, { changed: false }, { lastMessage: 'Still analyzing' }, { summary: 'Session limit reached' }])
    assert.equal(styleOutcome({ ...input, ...overrides }).status, 'error');
});
