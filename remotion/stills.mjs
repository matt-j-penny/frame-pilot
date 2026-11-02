// node stills.mjs <public-dir> <spec.json>
// spec: [{props, frames: [{frame, out}]}]. Bundles once, then renders every still.
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const [publicDir, specFile] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specFile, "utf8"));
const serveUrl = await bundle({ entryPoint: path.join(path.dirname(fileURLToPath(import.meta.url)), "src/index.ts"), publicDir });
for (const { props, frames } of spec) {
  const composition = await selectComposition({ serveUrl, id: "Reel", inputProps: props, chromiumOptions: { gl: "angle" } });
  for (const { frame, out } of frames)
    await renderStill({ serveUrl, composition, inputProps: props, frame, output: out, imageFormat: "jpeg", jpegQuality: 80, scale: 0.5, chromiumOptions: { gl: "angle" } });
}
