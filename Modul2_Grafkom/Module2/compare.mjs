/* Module 2 -- compare two rasters (PPM; PNG if `pngjs` is installed).
 *   node compare.mjs A.ppm B.ppm [--diff out/diff.ppm --scale 6]
 * Prints size, identical-pixel count, PSNR, SSIM, max |diff|; optionally
 * writes an amplified difference image. A missing decoder is reported, never
 * counted as a match. */
import { Framebuffer } from "./raster.mjs";
import { psnr, ssim, pixelStats } from "./metrics.mjs";
import { readFileSync } from "node:fs";

async function load(path) {
  const lp = path.toLowerCase();
  if (lp.endsWith(".ppm")) return Framebuffer.readPPM(path);
  if (lp.endsWith(".png")) {
    let PNG;
    try { ({ PNG } = await import("pngjs")); } catch { PNG = null; }
    if (!PNG) {
      console.error(`(!) ${path} is a PNG and no PNG decoder is installed ` +
        `(run \`npm i pngjs\`), or export the library render as PPM.`);
      process.exit(2);
    }
    const png = PNG.sync.read(readFileSync(path));
    const fb = new Framebuffer(png.width, png.height);
    for (let p = 0; p < png.width * png.height; p++) {
      fb.data[p * 3] = png.data[p * 4];
      fb.data[p * 3 + 1] = png.data[p * 4 + 1];
      fb.data[p * 3 + 2] = png.data[p * 4 + 2];
    }
    return fb;
  }
  throw new Error(`unsupported file type: ${path}`);
}

const files = process.argv.slice(2).filter((s) => !s.startsWith("--"));
if (files.length < 2) {
  console.error("usage: node compare.mjs A B [--diff out.ppm --scale N]");
  process.exit(1);
}
const A = await load(files[0]);
const B = await load(files[1]);
if (A.w !== B.w || A.h !== B.h) {
  console.error(`size mismatch: ${A.w}x${A.h} vs ${B.w}x${B.h} -- ` +
    `set renderer.setPixelRatio(1) and an explicit size before exporting.`);
  process.exit(2);
}
const st = pixelStats(A, B);
const p = psnr(A, B);
console.log(`same size ${A.w}x${A.h}   identical pixels: ${st.identical}/${st.total}   ` +
  `PSNR: ${p === Infinity ? "inf" : p.toFixed(1)} dB   SSIM: ${ssim(A, B).toFixed(3)}   ` +
  `max |diff|: ${st.maxAbs}`);

const di = process.argv.indexOf("--diff");
if (di >= 0) {
  const si = process.argv.indexOf("--scale");
  const scale = si >= 0 ? +process.argv[si + 1] : 6;
  const D = new Framebuffer(A.w, A.h);
  for (let i = 0; i < D.data.length; i++)
    D.data[i] = Math.min(255, Math.abs(A.data[i] - B.data[i]) * scale);
  D.writePPM(process.argv[di + 1]);
  console.log(`wrote ${process.argv[di + 1]} (|A-B| x${scale})`);
}
