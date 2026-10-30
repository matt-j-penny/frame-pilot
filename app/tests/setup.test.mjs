import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkProvider, setupStatus } from '../setup.mjs';

test('setup distinguishes missing CLI, failed checks, signed-out and signed-in providers', async () => {
  assert.equal((await checkProvider('codex', async () => ({ missing: true }))).status, 'missing');
  assert.equal((await checkProvider('codex', async () => ({ ok: false }))).status, 'error');
  const mock = auth => async (_file, args) => args[0] === '--version' ? { ok: true } : auth;
  assert.equal((await checkProvider('codex', mock({ ok: false }))).status, 'login');
  assert.equal((await checkProvider('codex', mock({ ok: true }))).ready, true);
  assert.equal((await checkProvider('claude', mock({ ok: true, stdout: '{"loggedIn":false}' }))).ready, false);
  assert.equal((await checkProvider('claude', mock({ ok: true, stdout: '{"loggedIn":true,"secret":"never returned"}' }))).ready, true);
  assert.equal((await checkProvider('claude', mock({ ok: true, stdout: 'invalid' }))).ready, false);
  const timeout = await checkProvider('codex', mock({ timedOut: true }));
  assert.equal(timeout.status, 'error');
  assert.ok(!JSON.stringify(timeout).includes('stdout'));
  await assert.rejects(() => checkProvider('invalid'), /Unknown provider/);
});
