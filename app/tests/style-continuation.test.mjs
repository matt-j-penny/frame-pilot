import { test } from 'node:test';
import assert from 'node:assert/strict';
import { styleContinuation } from '../style-continuation.mjs';

test('continuation resumes the same provider and transfers saved context across providers', () => {
  const previous = { name: 'cai-test', kind: 'create', status: 'error', model: 'opus', sessionId: 'claude-session',
    prompt: 'Analyze reference https://example.com/reference', log: [{ text: 'Contact sheets extracted' }], summary: 'Session limit reached' };
  const same = styleContinuation(previous, 'sonnet', '/project');
  assert.equal(same.resume, true);
  assert.equal(same.sessionId, 'claude-session');
  const switched = styleContinuation(previous, 'codex:gpt-6-sol', '/project');
  assert.equal(switched.resume, false);
  assert.equal(switched.sessionId, null);
  assert.match(switched.prompt, /Contact sheets extracted/);
  assert.match(switched.prompt, /https:\/\/example.com\/reference/);
  assert.match(switched.prompt, /Reuse completed work/);
  const legacy = styleContinuation({ ...previous, prompt: undefined }, 'codex', '/project');
  assert.match(legacy.prompt, /older run did not save/);
  assert.throws(() => styleContinuation({ ...previous, status: 'running' }, 'opus', '/project'), /Only failed/);
  assert.throws(() => styleContinuation(previous, 'invalid', '/project'), /supported model/);
});
