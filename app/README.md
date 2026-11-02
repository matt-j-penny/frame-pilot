# Frame Pilot

Start with `node app/server.mjs` from the project folder, then open http://localhost:4321.

On startup, Setup checks whether your selected CLI is installed and signed in. If it needs attention, the setup dialog shows install and login commands for both providers. Choose either one, complete the commands in Terminal, then click **Check again** and **Use** your provider. Reopen this dialog anytime with **Setup** in the sidebar. New agent runs check readiness before entering the queue. Checks read local CLI status and never return credentials to the browser.

The Model menu selects the agent for new edits, revisions, style creation, and style refinement:

- **Claude · Opus 5.5 / Sonnet 5.5 / Haiku 5.5** uses the Claude CLI and its login, with explicit versioned model IDs. Fable 5.1, Opus 5 and Sonnet 5 are also selectable.
- **ChatGPT model choices** use `codex exec --model` with the selected model for edits, revisions, and style operations. The list comes from the visible models in your local Codex CLI catalog (`$CODEX_HOME/models_cache.json`, default `~/.codex/models_cache.json`). Run Codex once after login to populate or refresh this catalog if only **ChatGPT · CLI default** appears. The default option keeps your CLI model configuration. Install with `npm install -g @openai/codex`, then run `codex login` and sign in with ChatGPT before starting the server. This integrates Codex CLI, rather than automating the ChatGPT website.

Existing jobs keep their selected model. Revisions can switch providers; switching starts a fresh agent session with the job folder and revision request as context. Revisions on the same provider resume that job's session. Codex runs with workspace-write sandboxing and network access for transcription and asset downloads; operations outside that scope can fail and appear in the run summary.

Set `DEEPGRAM_API_KEY` and optionally `BRAVE_API_KEY` in the server's environment, or in the `env` object of a private `config.local.json` in the project root. Credential precedence is project `config.local.json`, then process environment, then legacy `~/.claude/settings.json`; legacy keys work with either provider. Do not commit credentials.

Run adapter tests with `node --test app/tests/*.test.mjs`. These use mock CLI processes without making model calls or rendering videos.

Codex execution reference: https://developers.openai.com/codex/noninteractive

Failed style analysis or refinement runs offer **Continue** with a model selector in their progress dialog. Same-provider continuations resume the saved CLI session; switching providers starts a fresh session with the original task, previous progress, failure, and saved style/reference files. Older failed runs without a saved prompt recover context from their session and existing files. Previous attempt logs are retained in the style-run record.

When launched by this UI, agents delegate `reel.py render` to an authenticated local server endpoint so Chromium launches outside the agent sandbox. The endpoint only renders existing editor jobs, serializes renders per job, and accepts a preview flag. Direct terminal renders still run locally.


The new-video form provides a source upload, editing brief, model, style and output format. Portrait **9:16** is selected by default; landscape **16:9** renders at 1920×1080. The job preview follows the selected format.

**Advanced options** adds one inspiration video, multiple reference images/videos, and switches for Rough cut, Subtitles, Motion graphics, SFX and Music. All switches start enabled. Inspiration guides the treatment; reference files are available to the editing agent as assets. Settings apply to this job only. Rough cut off preserves the original duration unless you explicitly request cuts; the render step enforces the other disabled features.

**Preview before building** (Advanced options) plans the edit, then stops at a storyboard instead of rendering: one still per beat, showing the footage, layout, captions and motion graphic as they will look once settled. **Ideas per beat** (1-3) gives each graphic beat that many different treatments to pick from; with 1 you simply review the plan. Click a card to pick an idea, then **Build video** to merge the picks into `beat-plan.json` and render, verify and deliver as usual. Picks are saved in `preview-choices.json`. Native editor only, and Motion graphics must be on. Stills come from `reel.py storyboard <job>`, which bundles Remotion once and renders all frames with `remotion/stills.mjs`.

**Edit by transcript → Transcribe video** runs the existing Deepgram transcription directly, without starting an AI edit. It requires `DEEPGRAM_API_KEY`. Select a passage by dragging across words or clicking a word and Shift-clicking another, type a request and click **Add instruction**. You can add or remove multiple instructions before starting the edit. Replacing/removing the source clears its transcript and instructions. Completed transcripts are reused by the editing pipeline; instructions retain original word indices and timestamps and are saved in the job's `transcript-edits.json`. Transcription data lives in `app/transcripts/`.

Restart `node app/server.mjs` after updating the server, then reload the page. The source pipeline still expects video with an audio track; the brief directs an edit of uploaded footage.

Choose **No style** in the Style selector to follow the brief and references without a saved style. The choice persists, and new users start with no style. These jobs use neutral, editable job-local rendering settings and can be approved without saving style examples or learning. The CLI equivalent is `reel.py ingest <video> --no-style`.


The **Effort** selector sits beside Model and remembers a choice per model. Claude supports Low, Medium, High, Extra high and Max via `--effort`; **Default (Medium)** explicitly uses Medium for the Claude 5.5 models. Codex choices advertise their supported effort levels from the local model catalog and pass the selection with `model_reasoning_effort`. Choose an explicit Codex model to select its effort; the CLI-default model leaves effort to the CLI configuration. Model access remains subject to your provider account.

Effort is saved with each job and run, and is also selectable for revisions, style creation, style refinement and failed style continuations. No global CLI configuration is changed.


Choose **Editor → Native / CapCut / Palmier Pro / DaVinci Resolve** before starting an edit. Native is the default. External editors require a connection in **Setup → Editing app → Save & connect**; the selector remembers your choice, and revisions retain the job's editor.

Connections are discovered from local Claude MCP settings and the project's `.mcp.json`, with project-scoped overrides inherited from parent folders. Local overrides are saved in private `app/editor-connections.json`. Setup only returns connection fields, never inherited environment values or authentication headers. No global Claude/Codex configuration is modified.

- **CapCut:** choose an installed `capcut-bridge.py` and `uv`. The bridge and desktop installation are checked; Accessibility access and live export are exercised only when editing. Structural operations can close/reopen CapCut. The adapter stages the job's EDL in the bridge's expected layout, preserves source clips and applies the selected canvas. Revisions must preserve existing manual edits.
- **Palmier Pro:** connect its local HTTP MCP endpoint (default `http://127.0.0.1:19789/mcp`). Keep the app and its MCP server running. Connection checks list projects without modifying them.
- **DaVinci Resolve:** use its installed MCP Python command/server arguments, or a local HTTP MCP endpoint. Open Resolve and enable its local scripting connection as required by your installation. Connection checks read the product version.

The agent controls external editors through the authenticated `editor-bridge.mjs` CLI and the app's persistent MCP sessions, so both AI providers use the same editor connection. It discovers live tool schemas before making editor calls. Jobs only succeed after using the editor bridge, saving a verified `editor-project.json`, and exporting `output/final.mp4`. They do not silently fall back to a flattened Native edit. Each exported version snapshots the editor project record. A connection failure is reported before a job enters the queue.

Cancellation stops local CapCut bridge processes and sends MCP cancellation notifications to Palmier/Resolve. Whether an already-started remote operation can be interrupted depends on the editor's tool; finished versions are preserved. No editing permissions are granted by merely selecting an unconnected editor.


The **Styles +** button and **New style** menu now open a three-path style builder:

- **Upload a document:** drag in PDF, DOCX, TXT or Markdown brand/style guides. Text is extracted before guide creation. PDFs need `pypdf`; if it is not installed, the server can run it through `uv run --with pypdf`. DOCX uses Python's standard ZIP/XML modules. Scanned PDFs without text show a useful error and can instead be supplied as reference images. Documents are limited to 25 MB and 120,000 extracted characters.
- **Reference videos or images:** drag in multiple videos/images and/or paste HTTP(S) reference links. Still images inform visual design; timing and audio are inferred only from actual video evidence or explicitly recorded assumptions.
- **Ask me questions:** a seven-step guided interview covers audience, personality, branding, pacing/layouts, captions, graphics/audio, and preferences. Answers can be revised on a review screen before building. Questions run locally; the selected model turns the completed brief into a reusable style guide.

All paths support a style name, notes, an optional starting preset, and model/effort selection. The builder retains its inputs when moving between steps and reuses uploaded files after a failed submission. Source content and interview answers are kept in the style run's saved creation prompt. No sample edit is automatically run.


HTTPS requests in the Python pipeline keep certificate and hostname verification enabled. They honor `SSL_CERT_FILE` (or `REQUESTS_CA_BUNDLE`) and `SSL_CERT_DIR` from the server environment or private project config. Without explicit overrides, the pipeline loads Python's default trust store and the installed `certifi` CA bundle; standard system PEM bundles are a fallback when no roots are available. This avoids the missing-root-certificate issue with some python.org macOS installations. If needed, update the bundle with `python3 -m pip install --upgrade certifi` for the same Python used by the server. Transcription connection, certificate, HTTP and timeout failures are reported as short actionable messages.


Revision requests support multiple image/video attachments through **Attach images or videos** or by dropping files onto the revision composer. Thumbnails, progress, and remove controls are shown before applying. Text and/or attachments can be submitted; Apply waits until uploads finish. Completed uploads are retained per job in session storage across navigation/reload and are kept when submission fails.

The server validates media uploads, copies them into `public/assets/revisions/`, records them on the revision run, and gives the agent absolute paths plus job-relative asset paths. This works for Native and external-editor revisions. The original source stays unchanged unless the request explicitly replaces it. Submitted attachments are linked above the revision composer. Previous attachments remain in the job for later revisions.
