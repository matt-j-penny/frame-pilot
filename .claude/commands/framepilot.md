---
description: Start the Frame Pilot editor and open it in the browser
---

Start Frame Pilot for the user:

1. If http://localhost:4321 already responds, Frame Pilot is running: skip to step 3.
2. From the project folder, run `node app/server.mjs` in the background and wait until http://localhost:4321 responds. If it fails, show the error and the likely fix (missing install steps are in INSTALL.md).
3. Open http://localhost:4321 in the user's browser (`open` on macOS, `start` on Windows, `xdg-open` on Linux) and tell them Frame Pilot is ready. On first launch, the Setup dialog checks that Claude or Codex is installed and signed in.
