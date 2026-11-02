---
name: framepilot
description: Open the Frame Pilot UI. Use when the user says "/framepilot", "open frame pilot", or "open the UI".
---

Start and open the Frame Pilot UI (`node app/server.mjs`, http://localhost:4321).

1. If the built-in browser preview tools are available, call `preview_start` with `{ "name": "frame-pilot" }` (defined in `.claude/launch.json`). It reuses the server if it is already running.
2. Otherwise, check whether port 4321 is already serving (`curl -s -o /dev/null -w '%{http_code}' http://localhost:4321`). If not, start `node app/server.mjs` from the repo root in the background. Then run `open http://localhost:4321`.

Reply with one line saying the UI is open at http://localhost:4321.
