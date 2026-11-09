/* Module 2 -- Lab 2 evidence in one script (student work).
 *
 *   node lab2.mjs            prints every measurement, writes out/lab2_*.ppm
 *
 * Sections
 *   [1] running triangle vs the independent reference + hand-checked pixels (A2)
 *   [2] top-left rule: fixed vs the shipped (mirrored, bottom-right) rule
 *   [3] sample-centre check (Lab 2.3 / Example E1) + a bilinear blit with and
 *       without the -1/2 offset
 *   [4] octant awareness: a 24-spoke asterisk (Lab 2.5), and the same test
 *       run on a one-octant-only line to prove it catches octant bugs
 *   [5] pitfall fixes (Lab 2.4): Wu AA line linear vs naive blend, auto-flip
 *       winding, bounding-box clamp speed-up
 */
import {
  Framebuffer, lineBresenham, edge, triangle, coverage, lineWu, triangleAnyWinding,
  triangleNoBBox, srgbToLinear, total2,
} from "./raster.mjs";
import { referencePixels } from "./ref/make_refs.mjs";
import { mkdirSync } from "node:fs";

mkdirSync("out", { recursive: true });
const log = console.log;
const key = (p) => `${p[0]},${p[1]}`;

// --------------------------------------------------------------------- [1]
export function section1() {
  const A = [1, 1], B = [6, 2], C = [3, 7];
  const mine = [];
  triangle({ w: 10, h: 10 }, A, B, C, null, { onFragment: (x, y) => mine.push([x, y]) });
  const ref = referencePixels();
  const same = mine.length === ref.length && mine.every((p, i) => key(p) === key(ref[i]));
  const fb = new Framebuffer(10, 10);
  triangle(fb, A, B, C, [255, 255, 255]);
  const R = Framebuffer.readPPM("ref/tri_ref.ppm");
  let maxd = 0;
  for (let i = 0; i < fb.data.length; i++) maxd = Math.max(maxd, Math.abs(fb.data[i] - R.data[i]));
  // hand-check three pixels: interior, on a LEFT edge, on a RIGHT edge
  const bias = (X, Y) => { const dx = Y[0] - X[0], dy = Y[1] - X[1]; return (dy === 0 && dx > 0) || dy < 0 ? 0 : -1; };
  const rows = [[3, 3], [1, 2], [3, 1]].map(([x, y]) => {
    const px = x + 0.5, py = y + 0.5;
    const eBC = edge(B[0], B[1], C[0], C[1], px, py), eCA = edge(C[0], C[1], A[0], A[1], px, py),
      eAB = edge(A[0], A[1], B[0], B[1], px, py);
    const b = [bias(B, C), bias(C, A), bias(A, B)];
    const inside = eBC + b[0] >= 0 && eCA + b[1] >= 0 && eAB + b[2] >= 0;
    const lit = mine.some((p) => p[0] === x && p[1] === y);
    return { x, y, eBC, eCA, eAB, b, inside, lit };
  });
  return { n: mine.length, same, maxd, rows, mine };
}

// --------------------------------------------------------------------- [2]
export function section2() {
  const T1 = [[2, 2], [8, 2], [8, 8]], T2 = [[2, 2], [8, 8], [2, 8]];
  const owner = (rule) => {
    const o = {};
    for (const [name, T] of [["T1", T1], ["T2", T2]])
      triangle({ w: 12, h: 12 }, ...T, null, { rule, onFragment: (x, y) => { if (x === y) o[x] = name; } });
    return [...new Set(Object.values(o))].join("+");
  };
  const quad = (rule) => {
    const lit = [];
    for (const T of [[[1.5, 1.5], [3.5, 1.5], [3.5, 3.5]], [[1.5, 1.5], [3.5, 3.5], [1.5, 3.5]]])
      triangle({ w: 8, h: 8 }, ...T, null, { rule, onFragment: (x, y) => lit.push(key([x, y])) });
    return lit.sort().join(" ");
  };
  const covTL = coverage(12, 12, [T1, T2], { rule: "top-left" });
  const covBR = coverage(12, 12, [T1, T2], { rule: "bottom-right" });
  return {
    tl: { owner: owner("top-left"), quad: quad("top-left"), once: covTL.once, twice: covTL.twice, gaps: covTL.gaps },
    br: { owner: owner("bottom-right"), quad: quad("bottom-right"), once: covBR.once, twice: covBR.twice, gaps: covBR.gaps },
  };
}

// --------------------------------------------------------------------- [3]
export function section3() {
  const fill = (test) => {
    const lit = [];
    for (let y = 0; y < 6; y++) for (let x = 0; x < 6; x++) if (test(x, y)) lit.push([x, y]);
    return lit;
  };
  const inH = (v, a, b) => v >= a && v < b, inC = (v, a, b) => v >= a && v <= b;
  const r = {
    centre: fill((x, y) => inH(x + 0.5, 1, 3) && inH(y + 0.5, 1, 3)),
    cornerClosed: fill((x, y) => inC(x, 1, 3) && inC(y, 1, 3)),
    cornerHalfOpen: fill((x, y) => inH(x, 1, 3) && inH(y, 1, 3)),
    halfCentre: fill((x, y) => inH(x + 0.5, 1.5, 3.5) && inH(y + 0.5, 1.5, 3.5)),
    halfCorner: fill((x, y) => inH(x, 1.5, 3.5) && inH(y, 1.5, 3.5)),
  };
  // bilinear blit of a 4x4 black/white checker texture to (1,1) in an 6x6 target.
  // texel i has its centre at i+0.5 (same convention as the framebuffer).
  const tex = (i, j) => (((i + j) & 1) ? 255 : 0);
  const sample = (u, v) => {           // u,v in texel space
    const x = u - 0.5, y = v - 0.5, x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
    const t = (i, j) => tex(Math.min(3, Math.max(0, i)), Math.min(3, Math.max(0, j)));
    let n = 0;
    for (const w of [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]) if (w > 1e-12) n++;
    const v_ = (1 - fx) * (1 - fy) * t(x0, y0) + fx * (1 - fy) * t(x0 + 1, y0) + (1 - fx) * fy * t(x0, y0 + 1) + fx * fy * t(x0 + 1, y0 + 1);
    return [v_, n];
  };
  const blit = (corner) => {          // corner=true: sample at the pixel CORNER (D3D9 without -1/2)
    const vals = [], taps = new Set();
    for (let y = 1; y < 5; y++) for (let x = 1; x < 5; x++) {
      const [v, n] = corner ? sample(x - 1, y - 1) : sample(x + 0.5 - 1, y + 0.5 - 1);
      vals.push(Math.round(v)); taps.add(n);
    }
    return { vals, taps: [...taps] };
  };
  r.blitCentre = blit(false);
  r.blitCorner = blit(true);
  return r;
}

// --------------------------------------------------------------------- [4]
/** The module's Listing 1: ONLY the shallow-rising octant (0 <= dy <= dx). */
export function lineOneOctant(x0, y0, x1, y1) {
  const dx = x1 - x0, dy = y1 - y0, pts = [];
  let D = 2 * dy - dx, y = y0;
  for (let x = x0; x <= x1; x++) { pts.push([x, y]); if (D > 0) { y++; D += 2 * (dy - dx); } else D += 2 * dy; }
  return pts;
}

export function asterisk(lineFn, R = 40, cx = 50, cy = 50) {
  const res = [];
  for (let k = 0; k < 24; k++) {
    const th = (k * 15 * Math.PI) / 180;
    const ex = cx + Math.round(R * Math.cos(th)), ey = cy + Math.round(R * Math.sin(th));
    const pts = lineFn(cx, cy, ex, ey);
    const want = Math.max(Math.abs(ex - cx), Math.abs(ey - cy)) + 1;
    const last = pts[pts.length - 1] || [NaN, NaN];
    let connected = true, maxDev = 0;
    const L = Math.hypot(ex - cx, ey - cy);
    for (let i = 0; i < pts.length; i++) {
      if (i && (Math.max(Math.abs(pts[i][0] - pts[i - 1][0]), Math.abs(pts[i][1] - pts[i - 1][1])) !== 1)) connected = false;
      const dev = Math.abs((ex - cx) * (pts[i][1] - cy) - (ey - cy) * (pts[i][0] - cx)) / (L || 1);
      maxDev = Math.max(maxDev, dev);
    }
    const reach = Math.hypot(last[0] - cx, last[1] - cy);
    const ok = pts.length === want && last[0] === ex && last[1] === ey && connected &&
      maxDev <= 0.5 + 1e-9 && Math.abs(reach - R) <= 1;
    res.push({ deg: k * 15, n: pts.length, want, reach, maxDev, ok, pts });
  }
  return res;
}

// --------------------------------------------------------------------- [5]
export function wuDemo() {
  const W = 48, H = 20, bg = [18, 18, 22], ink = [255, 255, 255];
  const out = {};
  for (const mode of ["bresenham", "wu-naive", "wu-linear"]) {
    const fb = new Framebuffer(W, H, bg);
    if (mode === "bresenham") lineBresenham(2, 3, 45, 16, fb, ink);
    else lineWu(2, 3, 45, 16, fb, ink, { linear: mode === "wu-linear" });
    // light per column ABOVE the background, in linear light, averaged over columns 5..40
    const bgL = srgbToLinear(bg[0] / 255);
    let tot = 0;
    for (let x = 5; x <= 40; x++)
      for (let y = 0; y < H; y++) tot += srgbToLinear(fb.data[(y * W + x) * 3] / 255) - bgL;
    out[mode] = { fb, lightPerCol: tot / 36 };
  }
  return out;
}

export function windingDemo() {
  const A = [1, 1], B = [6, 2], C = [3, 7];
  let plain = 0, flipped = 0;
  triangle({ w: 10, h: 10 }, A, C, B, null, { onFragment: () => plain++ });          // reversed order
  const fb = { w: 10, h: 10, set: () => flipped++ };
  const dir = triangleAnyWinding(fb, A, C, B, [1, 1, 1]);
  // watertight with one triangle of the square reversed
  const counts = new Int32Array(144);
  const cnt = { w: 12, h: 12, set: (x, y) => counts[y * 12 + x]++ };
  triangleAnyWinding(cnt, [2, 2], [8, 2], [8, 8], [1, 1, 1]);
  triangleAnyWinding(cnt, [2, 2], [2, 8], [8, 8], [1, 1, 1]);     // T2 given counter-clockwise
  let once = 0, twice = 0;
  for (const c of counts) { if (c === 1) once++; if (c > 1) twice++; }
  return { total: total2(A, C, B), plain, flipped, dir, once, twice };
}

export function bboxDemo(iters = 200) {
  const fb = new Framebuffer(1920, 1080);
  const T = [[900, 500], [906, 501], [903, 506]];
  const time = (fn) => {
    fn(); const t0 = performance.now();
    for (let i = 0; i < iters; i++) fn();
    return (performance.now() - t0) / iters;
  };
  let a = 0, b = 0;
  triangle({ w: 1920, h: 1080 }, ...T, null, { onFragment: () => a++ });
  const cntFb = { w: 1920, h: 1080, set: () => b++ };
  triangleNoBBox(cntFb, ...T, [1, 1, 1]);
  const tB = time(() => triangle(fb, ...T, [255, 255, 255]));
  const tN = time(() => triangleNoBBox(fb, ...T, [255, 255, 255]));
  return { pixelsBBox: a, pixelsFull: b, msBBox: tB, msFull: tN, tested: { bbox: (906 - 900 + 1) * (506 - 500 + 1), full: 1920 * 1080 } };
}

// ------------------------------------------------------------------- main
function up(fb, s) {           // nearest-neighbour upscale for viewing
  const o = new Framebuffer(fb.w * s, fb.h * s);
  for (let y = 0; y < o.h; y++) for (let x = 0; x < o.w; x++) o.set(x, y, fb.get((x / s) | 0, (y / s) | 0));
  return o;
}

if (process.argv[1] && process.argv[1].endsWith("lab2.mjs") && !process.env.LAB2_NO_MAIN) {
  const s1 = section1();
  log("[1] running triangle A(1,1) B(6,2) C(3,7)");
  log(`    triangle() lights ${s1.n} px; same list as independent ref/make_refs.mjs: ${s1.same}; ` +
      `max|diff| vs ref/tri_ref.ppm = ${s1.maxd}`);
  log("    pixel   centre      E_BC   E_CA   E_AB   bias(BC,CA,AB)  inside?  lit by code");
  for (const r of s1.rows)
    log(`    (${r.x},${r.y})   (${r.x + 0.5},${r.y + 0.5})  ${String(r.eBC).padStart(5)}  ${String(r.eCA).padStart(5)}  ` +
        `${String(r.eAB).padStart(5)}   (${r.b.join(",")})${" ".repeat(9)}${r.inside}     ${r.lit}`);

  const s2 = section2();
  log("\n[2] top-left rule, fixed vs shipped");
  for (const [n, r] of [["fixed top-left    ", s2.tl], ["shipped (mirrored)", s2.br]])
    log(`    ${n}: square once=${r.once} twice=${r.twice} gaps=${r.gaps}; diagonal owned by ${r.owner}; ` +
        `quad [1.5,3.5)^2 lights {${r.quad}}`);

  const s3 = section3();
  const f = (l) => l.map(key).join(" ");
  log("\n[3] sample-centre, 2x2 rect at (1,1) in a 6x6 framebuffer");
  log(`    centre rule [1,3)        : ${s3.centre.length} px  {${f(s3.centre)}}`);
  log(`    corner, closed [1,3]     : ${s3.cornerClosed.length} px  {${f(s3.cornerClosed)}}`);
  log(`    corner, half-open [1,3)  : ${s3.cornerHalfOpen.length} px  (same as centre for integer edges)`);
  log(`    rect at (1.5,1.5), centre: {${f(s3.halfCentre)}}`);
  log(`    rect at (1.5,1.5), corner: {${f(s3.halfCorner)}}   <- shifted one pixel right/down`);
  log(`    bilinear blit of a 1-texel checker, centre (x+1/2) : taps ${s3.blitCentre.taps}, values {${[...new Set(s3.blitCentre.vals)]}}`);
  log(`    bilinear blit, corner (D3D9, no -1/2 offset)       : taps ${s3.blitCorner.taps}, values {${[...new Set(s3.blitCorner.vals)]}}`);

  const good = asterisk(lineBresenham), bad = asterisk(lineOneOctant);
  log("\n[4] 24-spoke asterisk, radius 40");
  log(`    lineBresenham  : ${good.filter((r) => r.ok).length}/24 spokes pass (count, endpoint, 8-connected, deviation <= 0.5 px, reach R+-1)`);
  log(`                     reach ${Math.min(...good.map((r) => r.reach)).toFixed(2)}..${Math.max(...good.map((r) => r.reach)).toFixed(2)} px, ` +
      `max deviation ${Math.max(...good.map((r) => r.maxDev)).toFixed(3)} px`);
  log(`    one-octant line: ${bad.filter((r) => r.ok).length}/24 pass; failing angles: ${bad.filter((r) => !r.ok).map((r) => r.deg).join(",")}`);
  const ast = new Framebuffer(101, 101);
  for (const r of good) for (const [x, y] of r.pts) ast.set(x, y, [255, 255, 255]);
  up(ast, 3).writePPM("out/lab2_asterisk.ppm");

  const wu = wuDemo();
  log("\n[5a] line (2,3)->(45,16): light per column above background (linear units; 1.0 = one full white pixel)");
  for (const [m, r] of Object.entries(wu)) {
    log(`    ${m.padEnd(10)}: ${r.lightPerCol.toFixed(3)}`);
    up(r.fb, 6).writePPM(`out/lab2_line_${m}.ppm`);
  }
  const wd = windingDemo();
  log(`\n[5b] reversed winding (A,C,B): total ${wd.total}; triangle() lights ${wd.plain} px; ` +
      `triangleAnyWinding lights ${wd.flipped} px (flipped=${wd.dir === -1}); square with T2 reversed: once=${wd.once} twice=${wd.twice}`);
  const bb = bboxDemo();
  log(`[5c] 14-px triangle in a 1920x1080 framebuffer: clamped bbox ${bb.msBBox.toFixed(4)} ms (${bb.tested.bbox} samples) vs ` +
      `whole framebuffer ${bb.msFull.toFixed(3)} ms (${bb.tested.full.toLocaleString()} samples) -> ` +
      `${(bb.msFull / bb.msBBox).toFixed(0)}x faster; same pixels: ${bb.pixelsBBox === bb.pixelsFull} (${bb.pixelsBBox})`);
  log("\nwrote out/lab2_asterisk.ppm, out/lab2_line_*.ppm");
}
