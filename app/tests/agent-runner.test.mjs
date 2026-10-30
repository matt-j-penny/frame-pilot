import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { runAgent, modelConfig } from '../agent-runner.mjs';

test('CLI routing, streamed logs, session resume, and failure recovery', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'reel-runner-'));
  const previousPath = process.env.PATH;
  const fixture = `#!${process.execPath}
let prompt = '';
process.stdin.on('data', c => prompt += c);
process.stdin.on('end', () => {
 const args = process.argv.slice(2);
 const claude = process.argv[1].endsWith('claude');
 const events = claude ? [
  {type:'assistant',message:{content:[{type:'text',text:'Working'}]}},
  {type:'result',result:'Claude done'}
 ] : prompt.includes('FAIL_RUN') ? [{type:'turn.failed',error:{message:'Authentication expired'}}] : [
  {type:'thread.started',thread_id:'test-thread'},
  {type:'item.started',item:{type:'command_execution',command:'python3 scripts/reel.py styles'}},
  {type:'item.completed',item:{type:'agent_message',text:JSON.stringify({args,prompt})}},
  {type:'turn.completed'}
 ];
 process.stdout.write(events.map(e=>JSON.stringify(e)).join('\\n')); // no trailing newline
});
`;
  try {
    for (const cli of ['claude', 'codex']) fs.writeFileSync(path.join(dir, cli), fixture, { mode: 0o755 });
    process.env.PATH = dir + path.delimiter + previousPath;
    const execute = (options) => new Promise(resolve => {
      const logs = [], sessions = [];
      runAgent({ root: dir, prompt: 'Edit', onLog: e => logs.push(e), onSession: id => sessions.push(id),
        ...options, onDone: result => resolve({ ...result, logs, sessions }) });
    });
    const first = await execute({ model: 'codex' });
    assert.equal(first.ok, true);
    assert.deepEqual(first.sessions, ['test-thread']);
    assert.equal(first.logs[0].t, 'tool');
    const payload = JSON.parse(first.summary);
    assert.ok(payload.prompt.includes('Read SKILL.md'));
    assert.ok(payload.args.includes('workspace-write'));
    assert.ok(!payload.args.includes('resume'));
    const revision = await execute({ model: 'codex', resume: true, sessionId: first.sessions[0] });
    assert.ok(JSON.parse(revision.summary).args.join(' ').includes('resume test-thread'));
    const chosen = await execute({ model: 'codex:gpt-6-sol' });
    const chosenArgs = JSON.parse(chosen.summary).args;
    assert.equal(chosenArgs[chosenArgs.indexOf('--model') + 1], 'gpt-6-sol');
    const resumedModel = await execute({ model: 'codex:gpt-6-luna', resume: true, sessionId: 'test-thread' });
    assert.ok(JSON.parse(resumedModel.summary).args.join(' ').includes('--model gpt-6-luna'));
    assert.ok(!payload.args.includes('--model'));
    const failure = await execute({ model: 'codex', prompt: 'FAIL_RUN' });
    assert.equal(failure.ok, false);
    assert.match(failure.summary, /codex login/);
    const claude = await execute({ model: 'opus' });
    assert.equal(claude.ok, true);
    assert.equal(claude.summary, "Claude done");
    assert.equal(claude.sessions.length, 1);
    assert.throws(() => modelConfig('unknown'), /supported model/);
    process.env.PATH = dir;
    fs.unlinkSync(path.join(dir, 'codex'));
    const missing = await execute({ model: 'codex' });
    assert.equal(missing.ok, false);
    assert.match(missing.summary, /Could not start Codex CLI/);
  } finally {
    process.env.PATH = previousPath;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a run finishes when the CLI exits even if a leftover process holds its output open', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'reel-runner-'));
  const previousPath = process.env.PATH;
  // The CLI prints its result, leaves a background process that inherits stdout, then exits.
  fs.writeFileSync(path.join(dir, 'claude'), `#!${process.execPath}
process.stdin.resume();
process.stdin.on('end', () => {
 require('node:child_process').spawn('sleep', ['30'], { stdio: ['ignore', 'inherit', 'inherit'] });
 process.stdout.write(JSON.stringify({ type: 'result', result: 'Claude done' }) + '\\n', () => process.exit(0));
});
`, { mode: 0o755 });
  try {
    process.env.PATH = dir + path.delimiter + previousPath;
    const started = Date.now();
    const result = await new Promise(resolve => runAgent({ root: dir, prompt: 'Edit', model: 'opus', onLog: () => {}, onDone: resolve }));
    assert.equal(result.ok, true);
    assert.equal(result.summary, 'Claude done');
    assert.ok(Date.now() - started < 15000);
  } finally {
    process.env.PATH = previousPath;
    spawnSync('pkill', ['-f', 'sleep 30']);
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
