/* Module 2 -- load a floor plan (metres, y-up) and render it as 2D primitives.
 * The single worldToScreen() has the y-flip and origin baked in -- unit-tested
 * in tests.mjs on a known point. */
import { readFileSync } from "node:fs";
import { Framebuffer, polyline, triangle } from "./raster.mjs";

export const CATEGORY_RGB = {
  // viridis 5-step ramp (luminance varies -> CVD- and grayscale-safe, Module 1)
  wall:   [68, 1, 84],
  cella:  [59, 82, 139],
  stair:  [33, 145, 140],
  shrine: [94, 201, 98],
  axis:   [253, 231, 37],
};

export function loadPlan(path = "pusaka_plan.json") {
  return JSON.parse(readFileSync(path, "utf8"));
}

/** metres (y-up) -> screen pixels (y-down), given the plan's scale + origin
 * and the framebuffer height. Deterministic; the ONLY place the flip lives. */
export function makeWorldToScreen(plan, H) {
  const s = plan.scale_px_per_m;
  const [ox, oy] = plan.origin_m;
  return ([xm, ym]) => [
    Math.round((xm + ox) * s),
    Math.round(H - 1 - (ym + oy) * s),
  ];
}

export function renderPlan(fb, plan, { fillSilhouette = false } = {}) {
  const w2s = makeWorldToScreen(plan, fb.h);
  if (fillSilhouette && plan.silhouette) {
    const p = plan.silhouette.points.map(w2s);
    // fan-triangulate the (convex) footprint
    for (let i = 1; i + 1 < p.length; i++) {
      let A = p[0], B = p[i], C = p[i + 1];
      // ensure total > 0 for our convention; swap B,C if not
      const tot = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
      if (tot < 0) [B, C] = [C, B];
      triangle(fb, A, B, C, [230, 236, 245]);
    }
  }
  let segs = 0;
  for (const pl of plan.polylines) {
    const pts = pl.points.map(w2s);
    const rgb = CATEGORY_RGB[pl.category] || [255, 255, 255];
    polyline(fb, pts, rgb, !!pl.closed);
    segs += pl.points.length - 1 + (pl.closed ? 1 : 0);
  }
  return segs;
}

export function newFramebufferForPlan(plan, w, h) {
  const fb = new Framebuffer(w, h, [18, 18, 22]);
  return fb;
}
