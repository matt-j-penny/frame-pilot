import { spawn } from 'node:child_process';

// Give each task its own POSIX process group so cancellation reaches its descendants.
export function spawnTask(command, args, options) {
  return spawn(command, args, { ...options, detached: process.platform !== 'win32' });
}
export function stopTask(child) {
  if (!child?.pid) return;
  if (process.platform === 'win32') {
    const killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
    killer.on('error', () => child.kill('SIGTERM'));
    return;
  }
  const signalGroup = signal => {
    try { process.kill(-child.pid, signal); }
    catch (error) { if (error.code !== 'ESRCH') child.kill(signal); }
  };
  signalGroup('SIGTERM');
  // A child may ignore TERM or outlive the CLI; force-stop the same process group.
  const timer = setTimeout(() => signalGroup('SIGKILL'), 5000);
  timer.unref();
}
