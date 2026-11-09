# Module 2 -- Rendering Pipeline & 2D Primitives (reference repo)

Course: *Grafika Komputer / Computer Graphics* (`25MP7716G030`), S1 Informatika
semester 5. Companion to `../../Module2_EN.tex`.

**Rule:** the from-scratch rasteriser (`raster.mjs`) is **plain JavaScript,
run with Node** -- no framework, no `<canvas>`. The framebuffer is a
`Uint8ClampedArray`; the same functions drive a browser `<canvas>` via
`ctx.putImageData`. The **library** side (`web/`) is Three.js, and is the
GitHub Pages deliverable.

**Convention** (stated once in `raster.mjs`, never mixed): `y` is DOWN; a
pixel `(x,y)` is a point sample at `(x+0.5, y+0.5)`; triangle vertices are
passed so the total `edge(A,B,C) > 0`; "inside" = all three edge functions
`>= 0`, and the top-left rule decides the exactly-on-edge case.

## Quick start

```bash
cd Module2
npm install                    # only three@0.160.0 + serve@14.2.7 (pinned)
node tests.mjs                 # -> ALL CHECKS PASSED (16 ok)
node lab2.mjs                  # every Lab 2 measurement in one run
node draw_square.mjs --mode fill      # the Fully Worked Example
node triangle_gap_bug.mjs            # diagnose-and-fix: shared-edge cracks/doubles
node draw_plan.mjs --w 800 --h 600 --fill    # the Pusaka3D plan, from scratch
node bench.mjs                       # forward vs backward timing
npm run serve       # zero-dependency server -> http://localhost:3000/web/
npm run capture     # headless Chrome renders web/ -> out/plan_three_*.ppm
npm run compare     # pixel diff from-scratch vs Three.js
```

`npm install` is only needed for the web viewer's dev server (`three` is
loaded from a CDN in `web/index.html`; `serve` is optional).

## Unit table

| File | Job | Reproduces |
|---|---|---|
| `raster.mjs` | Framebuffer, `lineDDA`, `lineBresenham` (8 octants), `edge`, `triangle` (+ top-left rule), `barycentric`, `coverage`, PPM r/w | E1-E5, watertightness |
| `metrics.mjs` | `psnr`, global `ssim`, `pixelStats` | Step 4, Case Study diff |
| `plan.mjs` | load `pusaka_plan.json`; the single `worldToScreen` (y-flip); `renderPlan` | Case Study |
| `pusaka_plan.json` | committed Prambanan-style floor plan (metres, y-up) | Case Study input (fallback) |
| `draw_plan.mjs` | render the plan headless -> `out/plan_scratch.ppm` | Case Study step 2 |
| `draw_square.mjs` | Fully Worked Example: 6x6 square, outline / fill / coverage | Steps 1-4 |
| `triangle_gap_bug.mjs` | diagnose-and-fix: shared-edge cracks/doubles, coverage image, proof | Lab 2 |
| `bench.mjs` | forward (rasterise) vs backward (per-pixel) at zoom 1x / 10x | Lab 3 decision |
| `compare.mjs` | diff two rasters (PPM; PNG if `pngjs` installed): identical %, PSNR, SSIM, max\|diff\|, diff image | Step 4, Case Study |
| `tests.mjs` | every from-scratch check; `npm test` entry point | MASTER 11.2 |
| `ref/make_refs.mjs` | **independent** reference rasteriser (exact integers on doubled coords, no bbox, explicit tie-break) -> `ref/tri_ref.ppm`, `ref/square_fill_ref.ppm` | Lab 2.1 reference match |
| `lab2.mjs` | hand-checked pixels, top-left fixed vs shipped, sample-centre + bilinear blit, 24-spoke asterisk, Wu AA linear vs naive, auto-winding, bbox speed-up | Lab 2.1-2.5, A2 |
| `legend_check.mjs` | 5-category legend distance under deuteranopia / protanopia / grayscale (linear RGB, same matrices as the SVG filters) | Lab 3.4, A5 |
| `tools/capture_three.mjs` | serves the repo, renders `web/` in headless Chrome (4 variants: line offset 0.5/0, MSAA on/off), writes `out/plan_three_*.ppm` | Lab 3.1-3.2 |
| `tools/serve.mjs` | zero-dependency static server | Lab 3.5-3.6 |
| `web/index.html`, `web/viewer.mjs`, `web/cvd.css` | Three.js plan viewer + accessible legend + SVG deuteranopia/protanopia toggles + PPM export | Lab 3 deliverable |

## What `node tests.mjs` asserts

- **E2 / E3** -- `lineDDA` and `lineBresenham` on `(2,1)->(9,5)` both give
  `[(2,1),(3,2),(4,2),(5,3),(6,3),(7,4),(8,4),(9,5)]`; all 8 octants give the
  right length.
- **E4** -- `edge(A,B,C)=28` for `A(1,1) B(6,2) C(3,7)`; edge values at
  `(3,3)` are `(8,12,8)` (inside); `(5,5)` and `(1,4)` are outside.
- **E5** -- `barycentric` sums to 1; interpolating `10/20/40` at
  `(0.5,0.25,0.25)` gives `20`.
- **top-left rule** -- the 6x6 square split on `y=x`: `once=36, twice=0,
  gaps=0` with the rule; `twice=6` without it; `gaps=6` with `">0"`.
- **E1** -- the sample-centre rule lights exactly `(1,1),(2,1),(1,2),(2,2)`
  for a 2x2 rectangle at `(1,1)`.
- **plan** -- `worldToScreen` flips `y` exactly once and is invertible.
- **reference raster** -- `draw_square` fill is byte-identical to
  `ref/square_fill_ref.ppm` (regenerated on first run; commit it).

## Student changes

- **The top-left rule was mirrored.** With y-down and total > 0, `edge(A,B,P) > 0`
  is the *visual right* of A->B, so triangles are walked clockwise on screen:
  a top edge is walked east (`dy == 0 && dx > 0`) and a left edge walks up
  (`dy < 0`). The shipped `topLeftBias` used `dx < 0` / `dy > 0`, i.e. a
  **bottom-right** rule. It was still watertight (any consistent tie-break
  is), but a quad over `[1.5,3.5)^2` lit pixels 2..3 instead of 1..2 --
  `(x0,x1]`, contradicting the half-open convention of section 14.3 -- and
  the diagonal of the worked example went to the triangle for which `y = x`
  is a *right* edge. Fixed in `raster.mjs` (old behaviour: `opts.rule =
  "bottom-right"`), tested in `tests.mjs`, references regenerated with the
  independent generator.
- **Pitfall fixes (Lab 2.4):** `lineWu` + `blendPixel` (linear-light vs naive
  blend: 0.994 vs 0.654 light per column), `triangleAnyWinding` (reversed
  triangle 0 px -> 14 px, still watertight), `triangleNoBBox` to measure the
  bounding-box clamp (~700x on a 14-px triangle in 1920x1080).
- **Half-pixel in the library:** `web/viewer.mjs` offsets LINE vertices by +1/2
  (fills keep their corners). Measured: 479,990/480,000 identical pixels and
  52.3 dB with the offset vs 6,003 differing pixels and 24.0 dB without.
- Viewer: `?plan=` / `?offset=` / `?aa=` / `?dump=` / `?halo=` parameters,
  marker glyphs on the plan, Indonesian labels, grayscale toggle, display-only
  dark halo under lines (the viridis yellow is ~1.06:1 against the light fill).
- `bench.mjs` prints work counters (Bresenham steps, point-segment tests) and
  the framebuffer allocation cost (0.003 ms -- it was not distorting the timing).
- `package.json` pins `three@0.160.0`, `serve@14.2.7`; root `index.html`
  redirects to `web/` for GitHub Pages.
- Own plan: none was available, so the fallback `pusaka_plan.json` is used.
  To grade your own building, add `myplan.json` (same schema) and run
  `node draw_plan.mjs --plan myplan.json --fill` and open
  `web/?plan=../myplan.json`.

## Notes on fixes applied while verifying

- `triangle()`: the coverage helper passes a plain `{w,h}` object as the
  "framebuffer"; guarded the draw call with `typeof fb.set === "function"` so
  `coverage()` can run the same rasteriser without a real framebuffer.

## Verified

| Item | Status | Date | Toolchain |
|---|---|---|---|
| `Module2_EN.tex` compiles | **yes** -- Tectonic 0.17.0, no overfull hbox > ~10 pt | 2026-09-04 | Windows 11 |
| `node tests.mjs` | **ALL CHECKS PASSED (10 ok)** | 2026-09-04 | Node v22.19.0 |
| `draw_square` / `triangle_gap_bug` / `draw_plan` / `bench` / `compare` | **run green** -- transcripts in `Module2_EN.tex` are the actual output | 2026-09-04 | Node v22.19.0 |
| `web/` Three.js viewer | **authored, not browser-verified on this host** (no display); loads `three@0.160.0` from jsdelivr, draws the plan + legend, exports PPM for `compare.mjs` | 2026-09-04 | -- |

| `node tests.mjs` (student version) | **ALL CHECKS PASSED (16 ok)** | 2026-11-09 | macOS 27.2 arm64, Node v26.12.0, npm 11.20.0 |
| clean copy: `npm install` -> `npm test` -> `npm run capture` -> `npm run compare` | **green, no manual step**; Three.js render byte-identical to the dev run | 2026-11-09 | same + three 0.160.0 |
| `web/` viewer in a browser | **rendered in headless Chrome 156.0.8078.74** (ANGLE / SwiftShader software GL): plan, legend, deuteranopia / protanopia / grayscale toggles -- screenshots `out/viewer_*.png`. Not yet checked on a hardware-GPU browser | 2026-11-09 | three r160 |
| GitHub Pages: https://andybagus26.github.io/Grafkom-Modul-1-5/Modul2_Grafkom/Module2/ | plan + legend render from the live URL in headless Chrome 156, no JS errors, no HTTP >= 400 | 2026-11-10 | deployed by the root workflow of https://github.com/andybagus26/Grafkom-Modul-1-5 |

Before the module fully meets the MASTER Definition of Done, open `web/` in a
browser (`npx serve .` -> `/web/`), confirm the plan and 5-category legend
render, toggle the deuteranopia/protanopia filters (all five stay distinct),
click **Export PPM**, and run
`node compare.mjs out/plan_scratch.ppm plan_three.ppm` -- expect a
high-but-finite PSNR (edge anti-aliasing only). Record the browser + version.
