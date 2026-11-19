/* Module 2 -- run every from-scratch check. `npm test` / `node tests.mjs`.
 * Exit 0 iff all pass. Covers the hand-checkable invariants of Examples
 * E1-E5, watertightness (top-left rule), and the reference raster match. */
import {
  Framebuffer, lineDDA, lineBresenham, edge, triangle, barycentric, coverage,
} from "./raster.mjs";
import { makeWorldToScreen, loadPlan } from "./plan.mjs";
import { pixelStats } from "./metrics.mjs";
import { existsSync, mkdirSync } from "node:fs";
import { legendCheck } from "./legend_check.mjs";

let pass = 0, fail = 0;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function check(name, fn) {
  try { fn(); console.log("OK   " + name); pass++; }
  catch (e) { console.log("FAIL " + name + "\n     " + e.message); fail++; }
}
const assert = (c, m) => { if (!c) throw new Error(m || "assertion failed"); };

const RUNLINE = [[2, 1], [3, 2], [4, 2], [5, 3], [6, 3], [7, 4], [8, 4], [9, 5]];

check("E2 -- lineDDA (2,1)->(9,5) gives the 8-pixel staircase", () => {
  assert(eq(lineDDA(2, 1, 9, 5), RUNLINE), "DDA pixel list mismatch");
});

check("E3 -- lineBresenham (2,1)->(9,5) matches DDA, integers only", () => {
  assert(eq(lineBresenham(2, 1, 9, 5), RUNLINE), "Bresenham pixel list mismatch");
});

check("lines -- all 8 octants: the reflected segment has the same length", () => {
  const base = lineBresenham(0, 0, 9, 4).length; // 10
  for (const [sx, sy] of [[1, 1], [-1, 1], [1, -1], [-1, -1]])
    for (const [a, b] of [[9, 4], [4, 9]]) {
      const n = lineBresenham(0, 0, sx * a, sy * b).length;
      assert(n === Math.max(a, b) + 1, `octant ${sx},${sy},${a},${b}: ${n}`);
    }
  assert(base === 10, "baseline length");
});

check("E4 -- edge-function signs for A(1,1) B(6,2) C(3,7)", () => {
  const A = [1, 1], B = [6, 2], C = [3, 7];
  const total = edge(A[0], A[1], B[0], B[1], C[0], C[1]);
  assert(total === 28, `total ${total} != 28`);
  const E = (P) => [
    edge(A[0], A[1], B[0], B[1], P[0], P[1]),
    edge(B[0], B[1], C[0], C[1], P[0], P[1]),
    edge(C[0], C[1], A[0], A[1], P[0], P[1]),
  ];
  assert(eq(E([3, 3]), [8, 12, 8]), "P1 (3,3) edge values");
  assert(E([5, 5]).some((v) => v < 0), "P2 (5,5) should be outside");
  assert(E([1, 4]).some((v) => v < 0), "P3 (1,4) should be outside");
  assert(E([3, 3]).every((v) => v >= 0), "P1 (3,3) should be inside");
});

check("E5 -- barycentric interpolation 10/20/40 at (.5,.25,.25) = 20", () => {
  const A = [0, 0], B = [4, 0], C = [0, 4];
  // point with barycentric (0.5, 0.25, 0.25): P = .5A + .25B + .25C = (1,1)
  const [la, lb, lc] = barycentric(A, B, C, [1, 1]);
  assert(Math.abs(la + lb + lc - 1) < 1e-12, "weights sum to 1");
  assert(Math.abs(la - 0.5) < 1e-12 && Math.abs(lb - 0.25) < 1e-12 && Math.abs(lc - 0.25) < 1e-12,
    `weights ${la},${lb},${lc}`);
  const v = la * 10 + lb * 20 + lc * 40;
  assert(Math.abs(v - 20) < 1e-12, `interp ${v} != 20`);
});

check("top-left rule -- 6x6 square split on y=x: every pixel covered once", () => {
  const T1 = [[2, 2], [8, 2], [8, 8]], T2 = [[2, 2], [8, 8], [2, 8]];
  const c = coverage(12, 12, [T1, T2], { topLeft: true });
  assert(c.once === 36 && c.twice === 0 && c.gaps === 0,
    `once=${c.once} twice=${c.twice} gaps=${c.gaps}`);
});

check("no top-left rule -- same square shows the seam (>=0: doubles; >0: gaps)", () => {
  const T1 = [[2, 2], [8, 2], [8, 8]], T2 = [[2, 2], [8, 8], [2, 8]];
  const dbl = coverage(12, 12, [T1, T2], { topLeft: false });
  const crk = coverage(12, 12, [T1, T2], { topLeft: false, strictGreater: true });
  assert(dbl.twice === 6 && dbl.gaps === 0, `>=0: twice=${dbl.twice} gaps=${dbl.gaps}`);
  assert(crk.twice === 0 && crk.gaps === 6, `>0: twice=${crk.twice} gaps=${crk.gaps}`);
});

check("E1 -- sample-centre: a 2x2 rect at (1,1) lights exactly (1,1),(2,1),(1,2),(2,2)", () => {
  const fb = new Framebuffer(6, 6);
  // fill x in [1,3), y in [1,3) by centre rule
  const lit = [];
  for (let y = 0; y < 6; y++)
    for (let x = 0; x < 6; x++) {
      const cx = x + 0.5, cy = y + 0.5;
      if (cx >= 1 && cx < 3 && cy >= 1 && cy < 3) { fb.set(x, y, [255, 255, 255]); lit.push([x, y]); }
    }
  assert(eq(lit, [[1, 1], [2, 1], [1, 2], [2, 2]]), `lit ${JSON.stringify(lit)}`);
});

check("plan -- worldToScreen flips y once and is invertible on a known point", () => {
  const plan = loadPlan("pusaka_plan.json");
  const H = 600;
  const w2s = makeWorldToScreen(plan, H);
  const s = plan.scale_px_per_m, [ox, oy] = plan.origin_m;
  const p = w2s([0, 0]);
  assert(p[0] === Math.round(ox * s), `x ${p[0]}`);
  assert(p[1] === Math.round(H - 1 - oy * s), `y ${p[1]}`);
  // moving +y in world moves UP on screen (smaller y)
  assert(w2s([0, 5])[1] < w2s([0, 0])[1], "y not flipped");
});

check("reference raster -- draw_square fill is byte-identical to ref/square_fill_ref.ppm", () => {
  if (!existsSync("ref/square_fill_ref.ppm")) {
    console.log("     (ref missing -- generating it now; commit ref/ after first run)");
    mkdirSync("ref", { recursive: true });
    const g = new Framebuffer(12, 12);
    triangle(g, [2, 2], [8, 2], [8, 8], [230, 120, 40]);
    triangle(g, [2, 2], [8, 8], [2, 8], [40, 130, 180]);
    g.writePPM("ref/square_fill_ref.ppm");
  }
  const fb = new Framebuffer(12, 12);
  triangle(fb, [2, 2], [8, 2], [8, 8], [230, 120, 40]);
  triangle(fb, [2, 2], [8, 8], [2, 8], [40, 130, 180]);
  const ref = Framebuffer.readPPM("ref/square_fill_ref.ppm");
  const st = pixelStats(fb, ref);
  assert(st.identical === st.total && st.maxAbs === 0,
    `identical ${st.identical}/${st.total}, max|diff| ${st.maxAbs}`);
});

// ------------------------------------------------------------ student checks
const L2 = await import("./lab2.mjs");

check("running triangle == independent reference (ref/make_refs.mjs, ref/tri_ref.ppm), max|diff| = 0", () => {
  const r = L2.section1();
  assert(r.same && r.maxd === 0 && r.n === 14, `same=${r.same} maxd=${r.maxd} n=${r.n}`);
  assert(r.rows.every((q) => q.inside === q.lit), "hand-checked pixels disagree with triangle()");
});

check("top-left rule is really TOP-LEFT: quad [1.5,3.5)^2 -> pixels 1..2 (half-open, section 14.3)", () => {
  const r = L2.section2();
  assert(r.tl.quad === "1,1 1,2 2,1 2,2", `quad lit {${r.tl.quad}}`);
  assert(r.tl.owner === "T1", `diagonal owned by ${r.tl.owner}; y=x is the LEFT edge of T1`);
  assert(r.tl.once === 36 && r.tl.twice === 0 && r.tl.gaps === 0, "not watertight");
});

check("E1 sample-centre: centre 2x2, closed corner test 3x3, corner sampling shifts a half-integer rect", () => {
  const r = L2.section3();
  assert(r.centre.length === 4 && r.cornerClosed.length === 9, `${r.centre.length} / ${r.cornerClosed.length}`);
  assert(JSON.stringify(r.halfCorner) !== JSON.stringify(r.halfCentre), "corner sampling should shift");
  assert(r.blitCentre.taps.join() === "1" && r.blitCorner.taps.join() === "4", "blit tap counts");
});

check("octants: 24-spoke asterisk passes; the one-octant line is caught", () => {
  assert(L2.asterisk(lineBresenham).every((q) => q.ok), "Bresenham spoke failed");
  assert(L2.asterisk(L2.lineOneOctant).filter((q) => q.ok).length < 24, "test did not catch octant bug");
});

check("pitfall fixes: Wu linear keeps line energy, naive loses it; auto-winding; bbox same pixels", () => {
  const w = L2.wuDemo();
  assert(Math.abs(w["wu-linear"].lightPerCol - w.bresenham.lightPerCol) < 0.02, "Wu linear energy");
  assert(w["wu-naive"].lightPerCol < 0.8 * w["wu-linear"].lightPerCol, "naive blend should be darker");
  const wd = L2.windingDemo();
  assert(wd.plain === 0 && wd.flipped === 14 && wd.once === 36 && wd.twice === 0, JSON.stringify(wd));
  const bb = L2.bboxDemo(3);
  assert(bb.pixelsBBox === bb.pixelsFull, "bbox changed coverage");
});

check("legend: 5 viridis categories stay distinct under deuteranopia/protanopia/grayscale (linear RGB)", () => {
  const r = legendCheck();
  assert(r.every((q) => q.min >= 20), JSON.stringify(r));
});

console.log(`\n${fail === 0 ? "ALL CHECKS PASSED" : fail + " CHECK(S) FAILED"}  (${pass} ok, ${fail} fail)`);
process.exit(fail === 0 ? 0 : 1);
