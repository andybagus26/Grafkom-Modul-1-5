/* Module 2 -- build the committed reference rasters with an INDEPENDENT
 * implementation (not raster.mjs):
 *   ref/tri_ref.ppm          running triangle A(1,1) B(6,2) C(3,7), white on black, 10x10
 *   ref/square_fill_ref.ppm  Fully Worked Example square split on y=x, 12x12
 * Independent, so the reference is not raster.mjs
 * checking itself:
 *   - exact integers only: every coordinate is doubled, so the sample centre
 *     (x+0.5, y+0.5) becomes (2x+1, 2y+1) and no float ever appears;
 *   - no bounding box: every pixel of the 10x10 grid is tested;
 *   - the top-left rule as an explicit tie-break branch (E == 0 and the edge
 *     is top or left), not as a -1 bias.
 * It also prints the covered pixel list, row by row, for the report.
 *
 *   node ref/make_refs.mjs        (run from the Module2 folder)
 */
import { writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const W = 10, H = 10;
const d = (p) => [2 * p[0], 2 * p[1]];

const E2 = (X, Y, P) => (Y[0] - X[0]) * (P[1] - X[1]) - (Y[1] - X[1]) * (P[0] - X[0]);
const isTopOrLeft = (X, Y) => {
  const dx = Y[0] - X[0], dy = Y[1] - X[1];
  // y-down, total > 0  =>  interior on the VISUAL RIGHT, triangle walked clockwise
  if (dy < 0) return true;              // left edge: walks UP the screen
  if (dy === 0 && dx > 0) return true;  // top edge: horizontal, walks EAST
  return false;
};
const ownsSample = (X, Y, P) => {
  const e = E2(X, Y, P);
  return e > 0 || (e === 0 && isTopOrLeft(X, Y));
};

export function referencePixels(A = [1, 1], B = [6, 2], C = [3, 7], w = W, h = H) {
  const [A2, B2, C2] = [A, B, C].map(d);
  if (E2(A2, B2, C2) <= 0) throw new Error("winding: total must be > 0");
  const lit = [];
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const P = [2 * x + 1, 2 * y + 1];
      if (ownsSample(B2, C2, P) && ownsSample(C2, A2, P) && ownsSample(A2, B2, P)) lit.push([x, y]);
    }
  return lit;
}

function writePPM(name, w, h, layers) {
  const body = new Uint8Array(w * h * 3);
  for (const [pix, rgb] of layers)
    for (const [x, y] of pix) body.set(rgb, (y * w + x) * 3);
  writeFileSync(new URL(name, import.meta.url),
    Buffer.concat([Buffer.from(`P6\n${w} ${h}\n255\n`), Buffer.from(body)]));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const lit = referencePixels();
  writePPM("./tri_ref.ppm", W, H, [[lit, [255, 255, 255]]]);
  console.log(`running triangle A(1,1) B(6,2) C(3,7): ${lit.length} pixels`);
  for (let y = 0; y < H; y++) {
    const row = lit.filter((p) => p[1] === y).map((p) => p[0]);
    if (row.length) console.log(`  y=${y}: x = ${row.join(",")}`);
  }
  console.log("wrote ref/tri_ref.ppm");
  // square: T1 drawn first (orange), then T2 (blue) -- same draw order as draw_square.mjs
  const t1 = referencePixels([2, 2], [8, 2], [8, 8], 12, 12);
  const t2 = referencePixels([2, 2], [8, 8], [2, 8], 12, 12);
  writePPM("./square_fill_ref.ppm", 12, 12, [[t1, [230, 120, 40]], [t2, [40, 130, 180]]]);
  const diag = t1.filter(([x, y]) => x === y).length;
  console.log(`square: T1 ${t1.length} px (incl. ${diag} diagonal), T2 ${t2.length} px -> wrote ref/square_fill_ref.ppm`);
}
