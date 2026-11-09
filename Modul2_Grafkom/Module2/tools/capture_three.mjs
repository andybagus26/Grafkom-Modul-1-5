/* Module 2 -- capture the Three.js render headlessly so it can be diffed
 * against the from-scratch raster with compare.mjs (Lab 3.1 / 3.2).
 *
 *   node tools/capture_three.mjs [--chrome PATH] [--plan ../pusaka_plan.json]
 *
 * 1. serves the Module2 folder with node:http (no dependencies);
 * 2. opens web/index.html?dump=1&... in headless Chrome (--dump-dom), once
 *    per variant (line offset 0.5 / 0, MSAA on / off, fill on);
 * 3. pulls the base64 PPM out of <pre id="dump"> and writes
 *    out/plan_three_<variant>.ppm, plus the WebGL renderer string.
 *
 * Needs Google Chrome / Chromium and network access to cdn.jsdelivr.net
 * (three@0.160.0 is loaded from the CDN, exactly like on GitHub Pages).
 */
import { createServer } from "node:http";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf(k); return i >= 0 ? process.argv[i + 1] : d; };
const CANDIDATES = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
];
const CHROME = arg("--chrome", process.env.CHROME || CANDIDATES.find((p) => existsSync(p)));
const PLAN = arg("--plan", "../pusaka_plan.json");
if (!CHROME) { console.error("no Chrome/Chromium found; pass --chrome PATH"); process.exit(2); }

const TYPES = { ".html": "text/html", ".mjs": "text/javascript", ".js": "text/javascript",
  ".json": "application/json", ".css": "text/css" };
const server = createServer((req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^([/\\])+/, "");
  const file = join(ROOT, path.endsWith("/") || path === "" ? join(path, "index.html") : path);
  if (!file.startsWith(ROOT) || !existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;

const VARIANTS = [
  ["offset05_aa", "offset=0.5&aa=1"],
  ["offset0_aa", "offset=0&aa=1"],
  ["offset05_noaa", "offset=0.5&aa=0"],
  ["offset0_noaa", "offset=0&aa=0"],
];
mkdirSync(join(ROOT, "out"), { recursive: true });
const run = (url) => new Promise((resolve, reject) => {
  // execFileSync would block the event loop that serves the files -> run async
  import("node:child_process").then(({ execFile }) =>
    execFile(CHROME, ["--headless=new", "--disable-gpu-sandbox", "--use-angle=swiftshader",
      "--enable-unsafe-swiftshader", "--virtual-time-budget=15000", "--dump-dom", url],
    { maxBuffer: 64 << 20 }, (err, stdout) => (err ? reject(err) : resolve(stdout))));
});
for (const [name, qs] of VARIANTS) {
  const url = `http://127.0.0.1:${port}/web/index.html?dump=1&fill=1&plan=${encodeURIComponent(PLAN)}&${qs}`;
  const dom = await run(url);
  const m = dom.match(/<pre id="dump" data-three="([^"]*)" data-renderer="([^"]*)">([^<]+)<\/pre>/);
  if (!m) { console.error(`${name}: no <pre id="dump"> in the page (did three.js load?)`); process.exitCode = 1; continue; }
  const out = join(ROOT, "out", `plan_three_${name}.ppm`);
  writeFileSync(out, Buffer.from(m[3], "base64"));
  console.log(`${name.padEnd(14)} three r${m[1]}  renderer "${m[2]}"  -> out/plan_three_${name}.ppm`);
}
server.close();
void execFileSync;
