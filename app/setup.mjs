import { execFile } from 'node:child_process';
import { editorStatuses } from './editor-connections.mjs';
import { modelConfig } from './agent-runner.mjs';

export const PROVIDERS = [
  { id: 'claude', label: 'Claude', install: 'npm install -g @anthropic-ai/claude-code', login: 'claude auth login', model: 'opus' },
  { id: 'codex', label: 'Codex / ChatGPT', install: 'npm install -g @openai/codex', login: 'codex login', model: 'codex' },
];
function command(file, args) {
  return new Promise(resolve => execFile(file, args, { timeout: 8000, maxBuffer: 128 * 1024 }, (error, stdout, stderr) => {
    resolve({ ok: !error, missing: error?.code === 'ENOENT', timedOut: !!error?.killed, stdout, stderr });
  }));
}
export async function checkProvider(id, run = command) {
  const provider = PROVIDERS.find(p => p.id === id);
  if (!provider) throw new Error('Unknown provider.');
  const version = await run(id, ['--version']);
  if (!version.ok) return { ...provider, status: version.missing ? 'missing' : 'error', ready: false,
    message: version.missing ? 'CLI is not installed or is not on the server PATH.' : 'Could not run the CLI. Try its version command in Terminal.' };
  const auth = await run(id, id === 'claude' ? ['auth', 'status', '--json'] : ['login', 'status']);
  let ready = auth.ok;
  if (id === 'claude') {
    try { ready = auth.ok && JSON.parse(auth.stdout).loggedIn === true; } catch { ready = false; }
  }
  return { ...provider, status: ready ? 'ready' : auth.timedOut ? 'error' : 'login', ready,
    message: ready ? 'Installed and signed in.' : auth.timedOut ? 'Sign-in check timed out. Try again.' : 'Sign in to this CLI in Terminal, then check again.' };
}
export async function setupStatus() {
  const providers = await Promise.all(PROVIDERS.map(p => checkProvider(p.id)));
  return { providers, editors: editorStatuses(), ready: providers.some(p => p.ready) };
}
export async function requireProvider(model) {
  const provider = await checkProvider(modelConfig(model).provider);
  if (!provider.ready) {
    const error = new Error(`${provider.label} needs setup. Open Setup to install it or sign in, then try again.`);
    error.status = 409;
    throw error;
  }
}
