# Install Frame Pilot

These steps are written for an AI coding agent (Claude Code recommended, Codex also works) running in an empty folder the user created for Frame Pilot. Do each step in order, tell the user what you are doing, and ask before installing anything system-wide.

## 1. Check the tools Frame Pilot needs

Run these and note any that are missing:

```bash
git --version
node --version     # 18 or newer
python3 --version  # 3.9 or newer
ffmpeg -version
```

On macOS, install anything missing with Homebrew (`brew install git node python ffmpeg`). If Homebrew itself is missing, point the user to https://brew.sh and wait for them to install it. On Windows or Linux, tell the user which packages to install for their system.

## 2. Download Frame Pilot into this folder

If the current folder is empty:

```bash
git clone https://github.com/matt-j-penny/frame-pilot.git .
```

If it is not empty, stop and ask the user whether to clone into a `frame-pilot` subfolder instead, then work from inside that subfolder for the remaining steps.

## 3. Install the video renderer

```bash
cd remotion && npm install && cd ..
```

## 4. Add API keys

Frame Pilot uses Deepgram to transcribe footage (required) and Brave Search to find real-world images (optional). Create `config.local.json` in the project folder with:

```json
{
  "env": {
    "DEEPGRAM_API_KEY": "",
    "BRAVE_API_KEY": ""
  }
}
```

Then tell the user to open that file and paste their own keys between the quotes. Never ask for keys in chat and never print them. Keys come from:

- Deepgram: https://console.deepgram.com (free credit on sign-up)
- Brave Search: https://api-dashboard.search.brave.com (optional; without it Frame Pilot uses graphics instead of real-world images)

`config.local.json` is git-ignored, so the keys stay on the user's computer.

## 5. Check the install

```bash
node --test app/tests/*.test.mjs
python3 scripts/reel.py lib-check
```

The tests use mock processes and make no model calls. `lib-check` listing SFX files as missing is expected: the sound-effect files aren't in the repo, so edits render without sound effects until the user adds them to `sfx/`.

## 6. Finish

Tell the user Frame Pilot is installed and that they can start it any time by running `/framepilot` in this folder (or `node app/server.mjs`, then opening http://localhost:4321). If they use Claude Code, it must be reopened in this folder once for `/framepilot` to appear.
