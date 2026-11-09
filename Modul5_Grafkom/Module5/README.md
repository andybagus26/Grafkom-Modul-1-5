# Module 5 -- AI Graphics: NeRF, World Models & AR

Grafika Komputer, S1 Informatika UM Surabaya -- **Andy Bagus, NIM 20241337033**.
Built on the course starter repo (`Module5_EN.pdf`). The preliminary study
(Q1-Q5) and the report (A1-A5) are submitted separately, not through this repo;
`tools/figures_m5.py` regenerates their figures into `docs/figures/`.

**Rule kept from the starter:** the ray generator, the compositing formula and
the whole differentiable renderer are NumPy only -- no autograd; the backward
pass is derived by hand and checked against finite differences in `tests.py`.
The AR app (`ar_app/`) is a static page (`<model-viewer>` + vanilla JS).

**Provenance (every asset in this repo):**
`gapura_bentar.glb` -- procedural 1:50 model in the style of Gapura Wringin
Lawang (Trowulan), geometry authored by Andy Bagus with `make_gapura_glb.py`,
2026, CC0, no third-party or AI-generated geometry; facts in its hotspots from
the sources listed inside `assets/gapura_bentar.json`. `pusaka_temple.glb` --
course starter, procedural (`make_temple_glb.py`), CC0-equivalent.
`data/*_capture/` -- synthetic, rendered by `capture.py` from analytic scenes.

## Quick start

```bash
python -m pip install -r requirements.txt
python ray_generator.py               # E1: ray through pixel (400,240)
python volume_render.py               # E2: composite 3 samples -> 1 pixel
python capture.py                     # data/pusaka_capture/ (8 views of the module scene)
python capture.py --scene andy        # data/andy_capture/   (8 views of MY scene: + candi bentar)
python fit_nerf_toy.py                # train on the PPMs; train/novel PSNR
python fit_nerf_toy.py --scene andy --init -1
python nerf_bug.py                    # diagnose-and-fix: 2 clustered vs 8 spread views
python lab2_improve.py                # Lab 2.4: init sweep, 3rd view, count vs coverage (~90 s)
python focal_from_exif.py PHOTO.jpg [u v]   # Lab 1.4: phone focal length in px + ray
python tests.py                       # -> ALL CHECKS PASSED (34 ok), ~10 s

cd ar_app
python make_temple_glb.py             # module temple (stupa winding fixed)
python make_gapura_glb.py             # my model + 6 bilingual hotspots
python -m http.server 8743            # http://localhost:8743/ (?model=gapura|pusaka&lang=en|id)
pip install playwright==1.64.1
python verify_ar_app.py               # -> ALL CHECKS PASSED (17 ok)
python occlusion_test.py              # Lab 3.2: hotspot visibility over a full orbit

python tools/figures_m5.py            # (from Module5/) every figure in docs/
```

## Unit table

| File | Job | Lab / report |
|---|---|---|
| `ray_generator.py` | pinhole pixel -> ray (unchanged) | E1, Q1, A1 |
| `volume_render.py` | alpha + front-to-back compositing (unchanged) | E2, Q2, A2 |
| `nerf_toy.py` | scenes (`pusaka`, **`andy`**), voxel grid, **stable backward** (+ module `v1` and 3 deliberately broken variants), training | Lab 2.1-2.2, A2 |
| `capture.py` | deterministic ring capture, `--scene`, PPM save **and load** | Lab 1.2, 2.1 |
| `fit_nerf_toy.py` | trains on the **PPM files** (`--targets analytic` = starter behaviour), `--scene`, `--init` | A2, A3 |
| `nerf_bug.py` | 2 clustered vs 8 spread views (unchanged) | Lab 2.3, A3 |
| `lab2_improve.py` | **new**: init sweep, 3rd-view sweep, 8 packed vs 8 spread; scored on 24 held-out views | Lab 2.4, A3 |
| `focal_from_exif.py` | **new**: f in px from a phone photo's EXIF, then the ray through a chosen pixel | Lab 1.4, A1 |
| `tests.py` | 34 checks (starter 17 + 17 new, list in its docstring) | A2, A5 |
| `ar_app/make_temple_glb.py` | module temple; **stupa winding fixed**; generic GLB/hotspot writers | Lab 3 |
| `ar_app/make_gapura_glb.py` | **new**: my candi bentar model + hotspots computed from the same part table | Lab 3.1 |
| `ar_app/index.html`, `app.js`, `style.css` | model switcher, EN/ID for all UI, **language fix**, **real hotspot occlusion** | Lab 3, A4 |
| `ar_app/verify_ar_app.py` | 17 headless-browser checks over both models | A4 |
| `ar_app/occlusion_test.py` | **new**: model-viewer vs my app vs a Python ray-box reference, every 5 deg | Lab 3.2, A4 |
| `tools/figures_m5.py` | all report figures | docs |

## Notes on fixes and findings (details + numbers in the submitted report)

1. **Stupa rendered as a see-through shell.** `pyramid()` wound its side
   triangles `(p0, p1, apex)` -- inward. glTF culls back faces, so from outside
   you saw the far inner faces (visible in the starter's own screenshots). Now
   `(p1, p0, apex)`; `tests.py` checks every triangle of both GLBs faces out.
2. **Language toggle left an open panel in the old language.** The starter
   check re-tapped the hotspot after toggling, which hid it. `app.js` now keeps
   the panel state and re-renders it; `verify_ar_app.py` checks without a
   re-tap and fails on the starter app (`docs/evidence/verify_original_app.txt`).
3. **Occluded hotspots were never hidden.** The starter CSS styled a `.hidden`
   class nothing sets, and buttons lacked `data-visibility-attribute`, so
   model-viewer never marked any hotspot. With that fixed it turned out that
   model-viewer only tests whether a hotspot's *normal faces the camera*,
   never whether the model is in the way: the step on the far side of my gate
   stayed "visible" from all 72 angles. `app.js` now raycasts the model at
   each hotspot's pixel (`queryHotspot` + `positionAndNormalFromPoint`) and
   dims it if a nearer surface is hit -- 0 disagreements with an independent
   Python ray-box reference for the inner-face and step hotspots, against 20
   and 34 for model-viewer alone (`docs/evidence/occlusion.txt`).
4. **Latent gradient bug.** The starter backward recovered `T = w / clip(alpha,
   1e-8)`, wrong once `alpha < 1e-8` (`sigma_raw` below about -18: 88 %
   error at -20). Training here never goes there (`sigma_raw` stays in
   [-4.5, 6.6]), so every printed number is unchanged, but the new form
   `dC/da_i = T_i (c_i - R_i)` with `R` from a back-to-front recurrence uses
   the forward pass's `T`, has no division, and needs no `alpha == 1` special
   case. Identical to 1e-16 where the old one was valid.
5. **The gradient test could pass without testing.** It probed 6 random voxels
   (one received no ray: gradient 0 on both sides) with an absolute `1e-6`
   tolerance (passes anything tiny). Now: every touched parameter (176),
   relative error, plus three broken backward passes that must fail.
6. **`fit_nerf_toy.py` never read the capture.** It re-rendered the targets
   from the analytic scene, so "bring your own capture" could not work. It now
   loads the PPMs (8-bit quantisation changes training PSNR by 0.01 dB);
   `--targets analytic` reproduces the module's 20.69 / 14.44 dB exactly.
7. **Initialisation has two sides.** The module's pitfall (`-5` crushes the
   gradient) reproduces, but `0` is not best: starting fog makes the
   transmittance in front of each sample shrink its gradient. `-1` gives
   19.2 dB mean over 24 held-out views vs 14.6 dB at `0` (500 iters); on the
   module's own novel view 20.25 vs 14.44 dB (800 iters). Default left at 0 so
   the module's numbers still reproduce; `--init -1` to use it.
8. **One held-out view is an anecdote.** Scored only at 190 deg, a 3rd view at
   10 deg (inside the cluster) looked best. Over 24 held-out views, spread 3rd
   views help more, and 8 views packed into 21 deg score 11.0 dB vs 14.6 dB for
   the same 8 views spread around the ring.

## Known deviations

1. **No nerfstudio/COLMAP/GPU run** (no CUDA GPU here) -- same as the starter;
   the toy pipeline is what runs. Lab 1.3 is a reading of nerfstudio's camera
   docs, as the lab asks ("read, don't run").
2. **Capture: the documented fallback.** No real 15-30 photo capture yet; the
   synthetic ring (`capture.py`) and my extended scene are used, as Lab 1.2
   allows. The phone focal length in A1 uses a typical phone main camera
   (26 mm-equivalent, 4032 x 3024) until a real photo of mine is run through
   `focal_from_exif.py`.
3. **AR on a physical phone: not yet tested.** The app is published (see
   Verified); everything up to the AR handoff is verified headlessly against
   the live URL (`verify_ar_app.py`).
4. Nearest-voxel lookup, not trilinear (starter choice, kept).
5. The candi bentar is a *style* model at 1:50, not a measured replica.

## Verified

| Item | Result | Date | Toolchain |
|---|---|---|---|
| starter repo, unmodified | 17 ok; E1/E2 and 20.69/14.44, 9.30/12.02 dB reproduced | 2026-11-09 | macOS 27.2, Python 3.14.7, NumPy 2.5.4 |
| `python tests.py` | **ALL CHECKS PASSED (34 ok)**, ~10 s | 2026-11-09 | same |
| clean copy -> fresh venv -> `pip install -r requirements.txt` -> both `make_*_glb.py` -> `capture.py` -> `tests.py` | 34 ok; GLBs, JSON, PPMs byte-identical to the repo | 2026-11-09 | same, pygltflib 1.16.5, matplotlib 3.11.2, Pillow 12.3.0 |
| `ar_app/verify_ar_app.py` | **ALL CHECKS PASSED (17 ok)** | 2026-11-09 | Playwright 1.64.1, Google Chrome 156 headless (SwiftShader) |
| `ar_app/occlusion_test.py` | inner-face hotspot visible 22 % of the orbit (predicted ~22 %) | 2026-11-09 | same |
| real phone AR (Scene Viewer / Quick Look) | **not yet** -- see Known deviations 3 | -- | -- |
| GitHub Pages: https://andybagus26.github.io/Grafkom-Modul-1-5/Modul5_Grafkom/Module5/ar_app/ | `verify_ar_app.py <that URL>` -> **ALL CHECKS PASSED (17 ok)** | 2026-11-10 | same; deployed by the root workflow of https://github.com/andybagus26/Grafkom-Modul-1-5 |

Evidence transcripts (copies of out/*.txt, kept in git): docs/evidence/
