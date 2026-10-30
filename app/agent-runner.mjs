import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { spawnTask as spawn } from "./process-control.mjs";
const TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "WebFetch", "mcp__brave-search__brave_image_search"];
const HEADLESS = "You are running headless behind the Frame Pilot web UI. Nobody can answer questions: never ask the user anything, never wait for input. " +
  "Where the reel-editor skill says to ask, choose the best option yourself and list what you assumed in your final summary. " +
  "Keep your final message to a short plain-text summary (no markdown tables).";

function runClaude({ prompt, model, effort, sessionId, resume, root, environment = {}, onSession = () => {}, onLog, onDone }) {
  if (!sessionId) { sessionId = randomUUID(); resume = false; onSession(sessionId); }
  const args = ["-p", "--model", modelConfig(model).cliModel ?? model, ...(effort ? ["--effort", effort] : []), "--output-format", "stream-json", "--verbose", "--append-system-prompt", HEADLESS,
    ...(resume ? ["--resume", sessionId] : ["--session-id", sessionId]), "--allowedTools", ...TOOLS];
  // Drop variables inherited from any parent Claude session: they make the child skip the user's own CLI login.
  const env = Object.fromEntries(Object.entries({ ...process.env, ...environment }).filter(([k]) => !/^(CLAUDE|ANTHROPIC_BASE_URL$)/.test(k)));
  const child = spawn("claude", args, { cwd: root, env, stdio: ["pipe", "pipe", "pipe"] });
  child.stdin.on("error", () => {});
  child.stdin.end(prompt);
  let buf = "", result = null, err = "";
  child.stdout.on("data", (chunk) => {
    buf += chunk;
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i);
      buf = buf.slice(i + 1);
      let ev;
      try { ev = JSON.parse(line); } catch { continue; }
      if (ev.type === "assistant") {
        for (const c of ev.message?.content ?? []) {
          if (c.type === "text" && c.text.trim()) onLog({ t: "say", text: c.text.trim() });
          if (c.type === "tool_use") onLog({ t: "tool", text: c.input?.description || c.input?.command?.slice(0, 140) || c.input?.file_path || c.name });
        }
      }
      if (ev.type === "result") result = ev;
    }
  });
  child.stderr.on("data", (c) => (err += c));
  child.on("error", (error) => { err = `Could not start Claude CLI: ${error.message}. Install Claude CLI and sign in with claude.`; });
  onFinish(child, "claude", (code) => {
    if (buf.trim()) {
      try { const ev = JSON.parse(buf); if (ev.type === "result") result = ev; } catch {}
    }
    // A clean exit whose final message was lost still counts; the server checks the render itself.
    const ok = code === 0 && (!result || (!result.is_error && !/Failed to authenticate|OAuth/i.test(result.result ?? "")));
    let summary = result?.result ?? (code === 0 ? "Claude finished, but its final message didn't reach Frame Pilot." : err.trim().slice(-800) || `claude exited with code ${code}`);
    if (/Failed to authenticate|OAuth|not logged in/i.test(summary)) summary += "\n\nFix: open Terminal, run `claude`, type /login and sign in. Then start the edit again.";
    onDone({ ok, summary });
  });
  return child;
}


// Keep the legacy codex id as the CLI-default choice for existing jobs.
const CLAUDE_EFFORTS = ["low", "medium", "high", "xhigh", "max"];
export const MODELS = [
  { id: "opus", provider: "claude", cliModel: "claude-opus-5-5", label: "Claude · Opus 5.5", note: "claude-opus-5-5", efforts: CLAUDE_EFFORTS, defaultEffort: "medium" },
  { id: "sonnet", provider: "claude", cliModel: "claude-sonnet-5-5", label: "Claude · Sonnet 5.5", note: "claude-sonnet-5-5", efforts: CLAUDE_EFFORTS, defaultEffort: "medium" },
  { id: "haiku", provider: "claude", cliModel: "claude-haiku-5-5", label: "Claude · Haiku 5.5", note: "claude-haiku-5-5", efforts: CLAUDE_EFFORTS, defaultEffort: "medium" },
  { id: "fable-5-1", provider: "claude", cliModel: "claude-fable-5-1", label: "Claude · Fable 5.1", note: "claude-fable-5-1", efforts: CLAUDE_EFFORTS, defaultEffort: "high" },
  { id: "opus-5", provider: "claude", cliModel: "claude-opus-5", label: "Claude · Opus 5", note: "claude-opus-5", efforts: CLAUDE_EFFORTS, defaultEffort: "high" },
  { id: "sonnet-5", provider: "claude", cliModel: "claude-sonnet-5", label: "Claude · Sonnet 5", note: "claude-sonnet-5", efforts: CLAUDE_EFFORTS, defaultEffort: "high" },
  { id: "codex", provider: "codex", label: "ChatGPT · CLI default", note: "Uses your Codex CLI model setting", efforts: [] },
];
export function availableModels() {
  try {
    const home = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
    const cache = JSON.parse(fs.readFileSync(path.join(home, "models_cache.json"), "utf8"));
    const models = (cache.models ?? []).filter(m => m.visibility === "list" && /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$/.test(m.slug));
    return [...MODELS, ...models.map(m => ({ id: `codex:${m.slug}`, provider: "codex", cliModel: m.slug,
      label: `ChatGPT · ${m.display_name || m.slug}`, note: m.description || "Codex model",
      efforts: (m.supported_reasoning_levels ?? []).map(level => level.effort).filter(level => ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"].includes(level)), defaultEffort: m.default_reasoning_level }))];
  } catch { return MODELS; }
}
export function modelConfig(id = "opus") {
  // Persisted model selections remain usable if the CLI cache later changes.
  if (/^codex:[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$/.test(id))
    return { id, provider: "codex", cliModel: id.slice(6) };
  const model = MODELS.find((m) => m.id === id);
  if (!model) throw new Error("Choose a supported model.");
  return model;
}

export function normalizeEffort(model, effort) {
  modelConfig(model);
  const config = availableModels().find(m => m.id === model);
  if (effort === "default") return config?.defaultEffort ?? null;
  if (effort == null || effort === "") return null;
  if (!config?.efforts?.includes(effort)) {
    const error = new Error("Choose a supported effort level for this model."); error.status = 400; throw error;
  }
  return effort;
}

// 'close' waits for every stdio pipe to close, which can never happen if a pipe stalls or a descendant holds it.
// Finish on whichever comes first: close, exit (after a grace period for remaining output), or the process vanishing.
function onFinish(child, label, finish) {
  let done = false;
  const once = (code, why) => {
    if (done) return;
    done = true;
    clearInterval(watch);
    console.error(`[${label}] pid ${child.pid} finished via ${why} (code ${code})`);
    finish(code);
  };
  child.on("close", (code) => once(code, "close"));
  child.on("exit", (code) => setTimeout(() => once(code, "exit"), 5000));
  const watch = setInterval(() => {
    try { process.kill(child.pid, 0); } catch (error) { if (error.code === "ESRCH") once(child.exitCode, "process gone"); }
  }, 30000);
}

const safeLog = (label, onLog) => (entry) => {
  try { onLog(entry); } catch (error) { console.error(`[${label}] could not record log entry:`, error); }
};

export function runAgent(options) {
  options = { ...options, effort: normalizeEffort(options.model, options.effort), onLog: safeLog(options.model, options.onLog) };
  return modelConfig(options.model).provider === "codex" ? runCodex(options) : runClaude(options);
}

function runCodex({ prompt, model, effort, sessionId, resume, root, environment = {}, onSession = () => {}, onLog, onDone }) {
  // Keep writes scoped to the project; network access is needed by the media pipeline.
  const args = ["exec", "--sandbox", "workspace-write", "-c", "sandbox_workspace_write.network_access=true",
    ...(effort ? ["-c", `model_reasoning_effort="${effort}"`] : []),
    ...(resume && sessionId ? ["resume", sessionId] : []), "--skip-git-repo-check", "--json", ...(modelConfig(model).cliModel ? ["--model", modelConfig(model).cliModel] : []), "-"];
  const child = spawn("codex", args, { cwd: root, env: { ...process.env, ...environment }, stdio: ["pipe", "pipe", "pipe"] });
  let buffer = "", stderr = "", summary = "", failure = "", completed = false;
  function event(line) {
    let ev;
    try { ev = JSON.parse(line); } catch { return; }
    if (ev.type === "thread.started" && ev.thread_id) onSession(ev.thread_id);
    const item = ev.item;
    if (ev.type === "item.completed" && item?.type === "agent_message") {
      summary = item.text ?? "";
      if (summary.trim()) onLog({ t: "say", text: summary.trim() });
    }
    if (ev.type === "item.started" && item?.type === "command_execution")
      onLog({ t: "tool", text: (item.command ?? "Run command").slice(0, 140) });
    if (ev.type === "item.completed" && item?.type === "file_change")
      onLog({ t: "tool", text: (item.changes ?? []).map((c) => c.path).join(", ") });
    if (ev.type === "turn.completed") {
      completed = true;
      // Reconnection events can be emitted before a successful retry.
      if (/stream disconnected|websocket closed|Reconnecting\.\.\./i.test(failure)) failure = "";
    }
    if (ev.type === "turn.failed" || ev.type === "error") failure = ev.error?.message ?? ev.message ?? "Codex run failed";
  }
  child.stdout.on("data", (chunk) => {
    buffer += chunk;
    let i;
    while ((i = buffer.indexOf("\n")) >= 0) { event(buffer.slice(0, i)); buffer = buffer.slice(i + 1); }
  });
  child.stderr.on("data", (chunk) => { stderr = (stderr + chunk).slice(-8000); });
  child.stdin.on("error", () => {});
  child.on("error", (error) => { failure = `Could not start Codex CLI: ${error.message}. Install it with npm install -g @openai/codex, then run codex login.`; });
  onFinish(child, "codex", (code) => {
    if (buffer.trim()) event(buffer);
    const ok = code === 0 && completed && !failure;
    let text = failure || (ok ? summary : stderr.trim().slice(-1200)) || summary || `Codex exited with code ${code}`;
    if (!ok && !/deepgram|brave/i.test(text) && /unauthorized|authentication|not logged in|401|token.*expired/i.test(text))
      text += "\n\nFix: open Terminal, run codex login, and sign in with ChatGPT. Then try again.";
    onDone({ ok, summary: text });
  });
  child.stdin.end(`${HEADLESS}\n\nRead SKILL.md in the working folder and follow its referenced workflow files. Use your available shell and image-viewing tools for the pipeline and visual verification.\n\n${prompt}`);
  return child;
}
