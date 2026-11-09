/* Module 2 -- Fully Worked Example: a 6x6 square, outline then filled.
 *
 * Square corners (2,2) and (8,8), y-down. Split along the main diagonal
 * y = x, which passes exactly through the 6 pixel centres (2.5,2.5)..(7.5,7.5)
 * -- the pixels the top-left rule has to arbitrate.
 *
 *   node draw_square.mjs --mode outline
 *   node draw_square.mjs --mode fill                 # top-left rule ON
 *   node draw_square.mjs --mode fill --no-top-left   # 6 double-drawn
 *   node draw_square.mjs --mode fill --strict-greater # 6 cracks
 */
import { Framebuffer, lineBresenham, triangle, coverage } from "./raster.mjs";
import { mkdirSync } from "node:fs";

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i >= 0 ? (process.argv[i + 1]?.startsWith("--") || i + 1 >= process.argv.length ? true : process.argv[i + 1]) : d;
};
const mode = arg("--mode", "fill");
const noTopLeft = process.argv.includes("--no-top-left");
const strictGreater = process.argv.includes("--strict-greater");
const W = 12, H = 12;
mkdirSync("out", { recursive: true });

const corners = [[2, 2], [8, 2], [8, 8], [2, 8]];
const T1 = [[2, 2], [8, 2], [8, 8]];
const T2 = [[2, 2], [8, 8], [2, 8]];

if (mode === "outline") {
  const fb = new Framebuffer(W, H);
  const lit = new Set();
  for (let i = 0; i < 4; i++) {
    const a = corners[i], b = corners[(i + 1) % 4];
    for (const [x, y] of lineBresenham(a[0], a[1], b[0], b[1], fb, [255, 255, 255]))
      lit.add(`${x},${y}`);
  }
  console.log("4 segments (top, right, bottom, left) via lineBresenham()");
  console.log(`pixels lit: ${lit.size}     wrote out/square_outline.ppm`);
  fb.writePPM("out/square_outline.ppm");
} else {
  const fb = new Framebuffer(W, H);
  const opts = { topLeft: !noTopLeft, strictGreater };
  triangle(fb, T1[0], T1[1], T1[2], [230, 120, 40], opts);
  triangle(fb, T2[0], T2[1], T2[2], [40, 130, 180], opts);
  const cov = coverage(W, H, [T1, T2], opts);
  const tag = noTopLeft ? " --no-top-left" : strictGreater ? " --strict-greater" : "";
  console.log(`2 triangles, edge functions${noTopLeft || strictGreater ? " (rule OFF)" : " + top-left rule"}${tag}`);
  console.log(
    `coverage: ${cov.once + cov.twice} pixels, once = ${cov.once}, twice = ${cov.twice}, gaps = ${cov.gaps}`
  );
  fb.writePPM("out/square_fill.ppm");
  console.log("wrote out/square_fill.ppm");
}
