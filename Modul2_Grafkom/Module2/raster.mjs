/* Module 2 -- from-scratch 2D rasteriser. Plain JavaScript, no framework,
 * no <canvas>: the framebuffer is a typed array. The SAME functions drive a
 * browser <canvas> via ctx.putImageData(new ImageData(fb.rgba(), w, h)).
 *
 * CONVENTION (stated once, never mixed):
 *   - y is DOWN (screen / image row order).
 *   - a pixel (x,y) is a POINT SAMPLE at (x+0.5, y+0.5).
 *   - triangle vertices are passed so the total edge(A,B,C) > 0.
 *   - "inside" = all three edge functions >= 0; the top-left rule decides
 *     the exactly-on-edge (== 0) case.
 *
 * Reproduces:
 *   Example E2 / E3 : lineDDA and lineBresenham on (2,1)->(9,5) give
 *     [(2,1),(3,2),(4,2),(5,3),(6,3),(7,4),(8,4),(9,5)]
 *   Example E4      : edgeFn signs for A(1,1) B(6,2) C(3,7)
 *   Example E5      : barycentric interpolation 10/20/40 at (.5,.25,.25) -> 20
 */
import { readFileSync, writeFileSync } from "node:fs";

// ---------------------------------------------------------------- Framebuffer
export class Framebuffer {
  constructor(w, h, bg = [0, 0, 0]) {
    this.w = w;
    this.h = h;
    this.data = new Uint8ClampedArray(w * h * 3);
    if (bg[0] || bg[1] || bg[2]) this.clear(bg);
  }
  clear(rgb) {
    for (let i = 0; i < this.data.length; i += 3) {
      this.data[i] = rgb[0]; this.data[i + 1] = rgb[1]; this.data[i + 2] = rgb[2];
    }
  }
  inside(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h; }
  set(x, y, rgb) {
    if (!this.inside(x, y)) return;
    const i = (y * this.w + x) * 3;
    this.data[i] = rgb[0]; this.data[i + 1] = rgb[1]; this.data[i + 2] = rgb[2];
  }
  get(x, y) {
    const i = (y * this.w + x) * 3;
    return [this.data[i], this.data[i + 1], this.data[i + 2]];
  }
  // P6 binary PPM: text header then raw RGB bytes (same family as Module 1)
  writePPM(path) {
    const header = Buffer.from(`P6\n${this.w} ${this.h}\n255\n`, "ascii");
    writeFileSync(path, Buffer.concat([header, Buffer.from(this.data.buffer, 0, this.data.length)]));
    return header.length + this.data.length;
  }
  static readPPM(path) {
    const buf = readFileSync(path);
    let p = 0;
    const tok = () => {
      while (p < buf.length && /\s/.test(String.fromCharCode(buf[p]))) p++;
      let s = "";
      while (p < buf.length && !/\s/.test(String.fromCharCode(buf[p]))) s += String.fromCharCode(buf[p++]);
      return s;
    };
    const magic = tok();
    if (magic !== "P6") throw new Error(`${path}: not a P6 PPM (got ${magic})`);
    const w = +tok(), h = +tok(), maxv = +tok();
    if (maxv !== 255) throw new Error(`${path}: maxval ${maxv} != 255`);
    p++; // single whitespace after maxval
    const fb = new Framebuffer(w, h);
    fb.data.set(buf.subarray(p, p + w * h * 3));
    return fb;
  }
}

// --------------------------------------------------------------------- lines
/** DDA line. Returns the list of pixels; also plots into fb if given. */
export function lineDDA(x0, y0, x1, y1, fb = null, rgb = [255, 255, 255]) {
  const dx = x1 - x0, dy = y1 - y0;
  const steps = Math.max(Math.abs(dx), Math.abs(dy));
  const pts = [];
  if (steps === 0) { pts.push([x0, y0]); if (fb) fb.set(x0, y0, rgb); return pts; }
  const xi = dx / steps, yi = dy / steps;
  let x = x0, y = y0;
  for (let k = 0; k <= steps; k++) {
    const px = Math.round(x), py = Math.round(y);
    pts.push([px, py]);
    if (fb) fb.set(px, py, rgb);
    x += xi; y += yi;
  }
  return pts;
}

/** Integer Bresenham, all 8 octants (Zingl form: add / compare only). */
export function lineBresenham(x0, y0, x1, y1, fb = null, rgb = [255, 255, 255]) {
  x0 |= 0; y0 |= 0; x1 |= 0; y1 |= 0;
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  const pts = [];
  for (;;) {
    pts.push([x0, y0]);
    if (fb) fb.set(x0, y0, rgb);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
  return pts;
}

export function polyline(fb, pts, rgb, close = false) {
  for (let i = 0; i + 1 < pts.length; i++)
    lineBresenham(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fb, rgb);
  if (close && pts.length > 2) {
    const a = pts[pts.length - 1], b = pts[0];
    lineBresenham(a[0], a[1], b[0], b[1], fb, rgb);
  }
}

// ----------------------------------------------------------------- triangles
export const edge = (ax, ay, bx, by, px, py) =>
  (bx - ax) * (py - ay) - (by - ay) * (px - ax);

/** top-left bias for directed edge X->Y (y-down, total>0 convention).
 *
 * With y DOWN and total > 0, edge(A,B,P) > 0 means P is on the VISUAL RIGHT
 * of A->B (e.g. A=(0,0), B=(1,0), P=(0,1): E = +1, P is below = right of an
 * eastward walk). So every triangle is walked CLOCKWISE on screen, interior
 * on the right:
 *   top edge  = horizontal, walked EAST  (dy == 0 && dx > 0), interior below
 *   left edge = walked UP the screen     (dy < 0),            interior to its east
 * STUDENT FIX: the shipped version tested (dx < 0) and (dy > 0) -- that is
 * the mirrored BOTTOM-RIGHT rule. Still watertight (any consistent tie-break
 * is), but a quad over [1.5,3.5)^2 lit pixels 2..3 instead of 1..2, i.e. it
 * implemented (x0,x1] and contradicted the half-open [x0,x1) convention of
 * section 14.3. The old behaviour stays available as opts.rule="bottom-right"
 * so the report can show the difference. */
function topLeftBias(xx, xy, yx, yy, rule = "top-left") {
  const dx = yx - xx, dy = yy - xy;
  if (rule === "bottom-right") return (dy === 0 && dx < 0) || dy > 0 ? 0 : -1;
  const isTop = dy === 0 && dx > 0;   // horizontal, walked east, interior below
  const isLeft = dy < 0;              // walked up the screen, interior to its east
  return isTop || isLeft ? 0 : -1;
}

/**
 * Fill triangle A,B,C (each [x,y]) with rgb.
 * opts.topLeft (default true): apply the top-left rule.
 * opts.strictGreater (default false): use ">" instead of ">=" (the crack bug).
 * opts.onFragment(x,y,wA,wB,wC): called per covered pixel (for coverage tests).
 * opts.rule: "top-left" (default, fixed) | "bottom-right" (the shipped mirror).
 */
export function triangle(fb, A, B, C, rgb = [255, 255, 255], opts = {}) {
  const { topLeft = true, strictGreater = false, onFragment = null, rule = "top-left" } = opts;
  const canDraw = !!(fb && typeof fb.set === "function");
  const W = fb ? fb.w : Infinity, H = fb ? fb.h : Infinity;
  const minX = Math.max(0, Math.floor(Math.min(A[0], B[0], C[0])));
  const maxX = Math.min(W - 1, Math.ceil(Math.max(A[0], B[0], C[0])));
  const minY = Math.max(0, Math.floor(Math.min(A[1], B[1], C[1])));
  const maxY = Math.min(H - 1, Math.ceil(Math.max(A[1], B[1], C[1])));
  const bBC = topLeft ? topLeftBias(B[0], B[1], C[0], C[1], rule) : 0;
  const bCA = topLeft ? topLeftBias(C[0], C[1], A[0], A[1], rule) : 0;
  const bAB = topLeft ? topLeftBias(A[0], A[1], B[0], B[1], rule) : 0;
  const pass = strictGreater ? (v) => v > 0 : (v) => v >= 0;
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      const px = x + 0.5, py = y + 0.5;                 // SAMPLE CENTRE
      const wA = edge(B[0], B[1], C[0], C[1], px, py) + bBC;
      const wB = edge(C[0], C[1], A[0], A[1], px, py) + bCA;
      const wC = edge(A[0], A[1], B[0], B[1], px, py) + bAB;
      if (pass(wA) && pass(wB) && pass(wC)) {
        if (canDraw) fb.set(x, y, rgb);
        if (onFragment) onFragment(x, y, wA, wB, wC);
      }
    }
  }
}

/** Barycentric coords of P in triangle A,B,C (unbiased). Sum to 1. */
export function barycentric(A, B, C, P) {
  const total = edge(A[0], A[1], B[0], B[1], C[0], C[1]);
  const wA = edge(B[0], B[1], C[0], C[1], P[0], P[1]) / total;
  const wB = edge(C[0], C[1], A[0], A[1], P[0], P[1]) / total;
  const wC = edge(A[0], A[1], B[0], B[1], P[0], P[1]) / total;
  return [wA, wB, wC];
}

/**
 * Coverage map for a set of triangles: how many times each pixel is filled.
 * Returns { once, twice, gaps, counts } where `gaps` counts pixels that are
 * inside the exact geometric union (unbiased >=0 test) but filled 0 times.
 */
export function coverage(w, h, tris, opts = {}) {
  const counts = new Int32Array(w * h);
  for (const [A, B, C] of tris)
    triangle({ w, h }, A, B, C, null, {
      ...opts,
      onFragment: (x, y) => { counts[y * w + x]++; },
    });
  // geometric union: unbiased, non-strict, no top-left rule
  const union = new Uint8Array(w * h);
  for (const [A, B, C] of tris)
    triangle({ w, h }, A, B, C, null, {
      topLeft: false, strictGreater: false,
      onFragment: (x, y) => { union[y * w + x] = 1; },
    });
  let once = 0, twice = 0, gaps = 0;
  for (let i = 0; i < counts.length; i++) {
    if (counts[i] === 1) once++;
    else if (counts[i] >= 2) twice++;
    if (union[i] && counts[i] === 0) gaps++;
  }
  return { once, twice, gaps, counts };
}

// =====================================================================
// Lab 2.4 -- pitfall-driven fixes (student work)
// =====================================================================

/** Signed total 2*area with this file's convention (y-down). */
export const total2 = (A, B, C) => edge(A[0], A[1], B[0], B[1], C[0], C[1]);

/**
 * PITFALL "Winding Tidak Konsisten" -- fix: auto-flip.
 * A triangle passed in the other order has total < 0, so all three edge
 * functions are <= 0 inside it and triangle() lights NOTHING. This wrapper
 * swaps B and C when needed (and skips degenerate total == 0), so either
 * winding fills -- and, because the top-left bias is recomputed for the
 * flipped edges, shared edges stay watertight.
 */
export function triangleAnyWinding(fb, A, B, C, rgb, opts = {}) {
  const t = total2(A, B, C);
  if (t === 0) return 0;                       // degenerate: zero area, no pixels
  if (t < 0) [B, C] = [C, B];
  triangle(fb, A, B, C, rgb, opts);
  return t < 0 ? -1 : 1;
}

/**
 * PITFALL "Overdraw dari Bounding Box yang Longgar" -- the BAD version, kept
 * only to measure the cost: tests every pixel of the framebuffer instead of
 * the triangle's clamped bounding box. Same pixels, same top-left rule.
 */
export function triangleNoBBox(fb, A, B, C, rgb) {
  const bBC = topLeftBias(B[0], B[1], C[0], C[1]), bCA = topLeftBias(C[0], C[1], A[0], A[1]),
    bAB = topLeftBias(A[0], A[1], B[0], B[1]);
  for (let y = 0; y < fb.h; y++)
    for (let x = 0; x < fb.w; x++) {
      const px = x + 0.5, py = y + 0.5;
      if (edge(B[0], B[1], C[0], C[1], px, py) + bBC >= 0 &&
          edge(C[0], C[1], A[0], A[1], px, py) + bCA >= 0 &&
          edge(A[0], A[1], B[0], B[1], px, py) + bAB >= 0) fb.set(x, y, rgb);
    }
}

// ---- sRGB transfer (same formulas as Module 1 srgb.py) ----------------
export const srgbToLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
export const linearToSrgb = (l) => {
  l = Math.min(1, Math.max(0, l));
  return l <= 0.0031308 ? 12.92 * l : 1.055 * l ** (1 / 2.4) - 0.055;
};

/** Blend rgb over the pixel with coverage a in [0,1].
 *  linear=true : decode -> mix -> encode (correct, Module 1)
 *  linear=false: mix the sRGB codes directly (the dark-fringe bug). */
export function blendPixel(fb, x, y, rgb, a, linear = true) {
  if (!fb.inside(x, y) || a <= 0) return;
  const i = (y * fb.w + x) * 3;
  for (let k = 0; k < 3; k++) {
    const d = fb.data[i + k] / 255, s = rgb[k] / 255;
    const o = linear
      ? linearToSrgb(srgbToLinear(s) * a + srgbToLinear(d) * (1 - a))
      : s * a + d * (1 - a);
    fb.data[i + k] = Math.round(o * 255);
  }
}

/**
 * Xiaolin Wu (1991) anti-aliased line. Endpoints are pixel-CENTRE
 * coordinates in this file's convention (integer (x,y) = centre of pixel
 * (x,y)), so an integer horizontal line lands exactly on one pixel row with
 * coverage 1 -- identical to Bresenham there. Each step splits coverage
 * between the two pixels straddling the ideal line, in proportion to
 * distance; blendPixel decides linear vs naive mixing.
 * Returns the summed coverage ("ink"), ~ the line length for any slope.
 */
export function lineWu(x0, y0, x1, y1, fb, rgb = [255, 255, 255], { linear = true } = {}) {
  const steep = Math.abs(y1 - y0) > Math.abs(x1 - x0);
  if (steep) [x0, y0, x1, y1] = [y0, x0, y1, x1];
  if (x0 > x1) [x0, y0, x1, y1] = [x1, y1, x0, y0];
  const dx = x1 - x0, dy = y1 - y0;
  const g = dx === 0 ? 1 : dy / dx;
  let ink = 0;
  const plot = (x, y, a) => {
    ink += a;
    if (fb) steep ? blendPixel(fb, y, x, rgb, a, linear) : blendPixel(fb, x, y, rgb, a, linear);
  };
  const xs = Math.round(x0), xe = Math.round(x1);
  for (let x = xs; x <= xe; x++) {
    const y = y0 + g * (x - x0);
    const yi = Math.floor(y), f = y - yi;
    plot(x, yi, 1 - f);
    if (f > 0) plot(x, yi + 1, f);
  }
  return ink;
}
