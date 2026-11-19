/* Module 2 -- DIAGNOSE-AND-FIX: shared-edge cracks / double-draws.
 *
 * The bug artifact: a quad drawn as two triangles WITHOUT the top-left rule.
 * Your Lab 2 task -- from the rendered pixels only, before reading the fix:
 *   1. show which pixels are covered twice (or missing) and count them;
 *   2. state the cause;
 *   3. switch to the top-left rule;
 *   4. prove 0 doubles and 0 gaps.
 *
 *   node triangle_gap_bug.mjs            # runs all three modes, prints evidence
 */
import { Framebuffer, triangle, coverage } from "./raster.mjs";
import { mkdirSync } from "node:fs";

mkdirSync("out", { recursive: true });

// same 6x6 square + diagonal as the Fully Worked Example
const T1 = [[2, 2], [8, 2], [8, 8]];
const T2 = [[2, 2], [8, 8], [2, 8]];
const W = 12, H = 12;

function run(label, opts) {
  const fb = new Framebuffer(W, H);
  triangle(fb, T1[0], T1[1], T1[2], [230, 120, 40], opts);
  triangle(fb, T2[0], T2[1], T2[2], [40, 130, 180], opts);
  const cov = coverage(W, H, [T1, T2], opts);
  console.log(
    `${label.padEnd(26)} once=${cov.once}  twice=${cov.twice}  gaps=${cov.gaps}`
  );
  return { fb, cov };
}

console.log("== evidence: two triangles tiling a 6x6 quad along y = x ==");
const buggy = run("naive >=0 (no rule)", { topLeft: false });
const cracks = run("strict >0 (no rule)", { topLeft: false, strictGreater: true });
const fixed = run("top-left rule", { topLeft: true });

// evidence from the rendered pixels: list them
const where = (cov, pred) => {
  const out = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (pred(cov.counts[y * W + x], x, y)) out.push(`(${x},${y})`);
  return out.join(" ");
};
// pixels inside the exact union (every centre strictly or exactly inside the quad)
const inQuad = (x, y) => x >= 2 && x < 8 && y >= 2 && y < 8;
console.log(`\ncovered TWICE with >=0 : ${where(buggy.cov, (c) => c >= 2)}`);
console.log(`MISSING with >0       : ${where(cracks.cov, (c, x, y) => c === 0 && inQuad(x, y))}`);
console.log("-> all lie on x = y, i.e. their centre (x+.5, y+.5) is ON the shared edge (2,2)-(8,8):");
console.log("   edge((2,2),(8,8), (x+.5,x+.5)) = 6*(x+.5-2) - 6*(x+.5-2) = 0 for BOTH triangles.");

// coverage images: red = twice, grey = once, cyan = missing (inside the quad, 0 times)
function covImage(cov, path) {
  const img = new Framebuffer(W, H);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const c = cov.counts[y * W + x];
      img.set(x, y, c >= 2 ? [220, 30, 30] : c === 1 ? [120, 120, 120] : inQuad(x, y) ? [0, 220, 230] : [0, 0, 0]);
    }
  img.writePPM(path);
}
covImage(buggy.cov, "out/gap_coverage_buggy.ppm");
covImage(cracks.cov, "out/gap_coverage_cracks.ppm");
covImage(fixed.cov, "out/gap_coverage_fixed.ppm");
fixed.fb.writePPM("out/gap_fixed.ppm");

console.log("\nroot cause : pixels whose centre lies exactly on the shared edge");
console.log("             have an edge function == 0 in BOTH triangles.");
console.log("the fix    : per-edge top-left bias -- 0 for a top/left edge,");
console.log("             -1 otherwise -- so each on-edge pixel is claimed once.");
console.log(`proof      : top-left rule -> twice=${fixed.cov.twice}, gaps=${fixed.cov.gaps}`);
console.log("wrote out/gap_coverage_{buggy,cracks,fixed}.ppm (red = double, cyan = missing, grey = once), out/gap_fixed.ppm");
if (!(fixed.cov.twice === 0 && fixed.cov.gaps === 0))
  throw new Error("top-left rule did not produce a watertight fill");
