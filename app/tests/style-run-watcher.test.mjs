import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const source = html.slice(html.indexOf('function createStyleRunWatcher('), html.indexOf('const styleRunWatcher ='));
const { createStyleRunWatcher } = vm.runInNewContext(`${source}; ({ createStyleRunWatcher })`);
const flush = () => new Promise(resolve => setImmediate(resolve));

test('popup follows queued -> running -> error and stops polling at completion', async () => {
  const states = ['queued', 'running', 'error'], rendered = [];
  let pending;
  const watcher = createStyleRunWatcher({
    fetchRun: async name => ({ name, run: { status: states.shift() } }),
    render: s => rendered.push(s.run.status), onError: e => assert.fail(e.message), isOpen: () => true,
    schedule: callback => { pending = callback; return 1; }, cancel: () => { pending = null; },
  });
  watcher.watch('cai-test'); await flush();
  const first = pending; pending = null; await first();
  const second = pending; pending = null; await second();
  assert.deepEqual(rendered, ['queued', 'running', 'error']);
  assert.equal(pending, null);
});

test('closed or replaced popups ignore in-flight responses', async () => {
  let resolve, open = true;
  const rendered = [];
  const watcher = createStyleRunWatcher({ fetchRun: () => new Promise(r => resolve = r),
    render: s => rendered.push(s), onError: assert.fail, isOpen: () => open,
    schedule: () => assert.fail('must not schedule'), cancel: () => {} });
  watcher.watch('old'); watcher.stop();
  resolve({ run: { status: 'running' } }); await flush();
  assert.equal(rendered.length, 0);
  watcher.watch('new'); open = false;
  resolve({ run: { status: 'done' } }); await flush();
  assert.equal(rendered.length, 0);
});

test('failed status requests show an error and retry instead of silently staying running', async () => {
  let pending, fail = true;
  const errors = [], rendered = [];
  const watcher = createStyleRunWatcher({ fetchRun: async () => {
    if (fail) throw new Error('Server unavailable');
    return { run: { status: 'done' } };
  }, render: s => rendered.push(s.run.status), onError: e => errors.push(e.message), isOpen: () => true,
    schedule: callback => { pending = callback; return 1; }, cancel: () => {} });
  watcher.watch('cai-test'); await flush();
  assert.deepEqual(errors, ['Server unavailable']);
  fail = false; await pending();
  assert.deepEqual(rendered, ['done']);
});
