"""Lab 3 item 2 -- decision with a written prediction: which hotspot of MY
model will <model-viewer> hide (occlusion-cull) most often, and over which
camera angles?

PREDICTION (written before running this; also in the report, A4):
  The hardest hotspot is "celah", on the INNER face of the east half
  (point x = +0.034, y = 0.115, z = 0; normal -x, i.e. it faces the west
  half across the 7 cm passage). It can only be seen if
    (1) the camera is on the -x side of that face (facing test), and
    (2) the line of sight escapes the passage before the walls end: the
        passage is 0.069 m wide (from the point to the west wall) and the
        body is 2 x 0.085 m deep, so the ray may lean at most
        atan(0.069 / 0.085) ~ 39 deg away from the passage axis (z).
  model-viewer's azimuth theta is 0 at +z and 90 at +x, so the prediction is
        visible only for theta in [-39, 0] U [180, 219] deg
  -> about 2 x 39 / 360 ~ 22 % of a full orbit, hidden ~78 %. Every other
  hotspot sits on an outer face and should be visible about half the orbit
  (its face looks at one side) or always ("nama", top face, camera above).
  The polar angle is held at 75 deg (camera slightly above the model) -- the
  default framing.

The test: orbit the camera every 5 deg at the fixed polar angle and record,
per hotspot and angle, three answers to "can the user see this hotspot?":
  mv    -- model-viewer's own data-visible attribute;
  app   -- what the app finally shows (data-visible AND not .occluded, the
           raycast test I added to app.js after the first run);
  truth -- an independent reference computed HERE in Python: exact
           ray/box (slab) intersection of the segment camera -> hotspot
           against the same PARTS boxes make_gapura_glb.py builds the mesh
           from, using the camera position model-viewer reports.
Then: each hotspot's visible fraction under all three, the angles where mv or
app disagree with truth, and the measured window for "celah".

Run (app served on :8743):  python occlusion_test.py  -> out/occlusion.json
"""
from __future__ import annotations

import json
import os

import numpy as np

from make_gapura_glb import PARTS
from verify_ar_app import BASE_URL, launch, set_orbit, sync_playwright, wait_ready

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
STEP = 5

STATE_JS = """() => {
  const v = document.querySelector('model-viewer');
  const o = v.getCameraOrbit(), c = v.getCameraTarget(), s = Math.sin(o.phi);
  const cam = [c.x + o.radius * s * Math.sin(o.theta), c.y + o.radius * Math.cos(o.phi),
               c.z + o.radius * s * Math.cos(o.theta)];
  const spots = {};
  for (const b of document.querySelectorAll('.hotspot')) {
    spots[b.dataset.id] = { mv: b.hasAttribute('data-visible'),
                            app: b.hasAttribute('data-visible') && !b.classList.contains('occluded'),
                            pos: b.dataset.position.split(' ').map(parseFloat) };
  }
  return { cam, spots, theta_actual: o.theta * 180 / Math.PI };
}"""


def segment_blocked(cam, p, boxes, eps=1e-9):
    """True if the open segment cam -> p passes through any axis-aligned box."""
    cam, p = np.asarray(cam, float), np.asarray(p, float)
    d = p - cam
    for lo, hi in boxes:
        t0, t1 = 0.0, 1.0
        ok = True
        for k in range(3):
            if abs(d[k]) < eps:
                if cam[k] < lo[k] or cam[k] > hi[k]:
                    ok = False
                    break
            else:
                a, b = (lo[k] - cam[k]) / d[k], (hi[k] - cam[k]) / d[k]
                t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
                if t0 > t1:
                    ok = False
                    break
        if ok and t0 < 1.0 - 1e-6:
            return True
    return False


BOXES = [(np.subtract(s["center"], s["half"]), np.add(s["center"], s["half"])) for s in PARTS.values()]


def windows(thetas):
    """Contiguous runs of azimuths (deg, multiples of STEP), wrapping at 360,
    reported in (-180, 180] so a run through 0 deg reads naturally."""
    s = set(thetas)
    if not s:
        return []
    if len(s) == 360 // STEP:
        return [[0, 360]]
    start = next(a for a in range(0, 360, STEP) if a not in s)
    runs, cur = [], None
    for k in range(1, 360 // STEP + 1):
        a = (start + k * STEP) % 360
        if a in s:
            cur = [a, a] if cur is None else [cur[0], a]
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    norm = lambda x: x - 360 if x > 180 else x
    return [[norm(a), norm(b)] for a, b in runs]


def main():
    res = {}
    with sync_playwright() as p:
        browser, which = launch(p)
        page = browser.new_page(viewport={"width": 390, "height": 800})
        for model, n, radius in (("gapura", 6, "0.85m"), ("pusaka", 5, "1.2m")):
            page.goto(f"{BASE_URL}/index.html?model={model}", wait_until="networkidle")
            wait_ready(page, n)
            rows = []
            for theta in range(0, 360, STEP):
                set_orbit(page, f"{theta}deg 75deg {radius}")
                st = page.evaluate(STATE_JS)
                for i, v in st["spots"].items():
                    v["truth"] = (not segment_blocked(st["cam"], v["pos"], BOXES)) if model == "gapura" else None
                # label each row by the angle the camera was ACTUALLY at when the
                # state was read (can lag the requested one by a few degrees in
                # a headless tab), snapped to the 5 deg grid
                act = st["theta_actual"] % 360
                rows.append(dict(theta=int(round(act / STEP) * STEP) % 360, theta_requested=theta,
                                 theta_actual=act, cam=st["cam"], spots=st["spots"]))
            res[model] = rows
            lag = max(abs((r["theta_actual"] - r["theta_requested"] + 180) % 360 - 180) for r in rows)
            print(f"\n[{model}] max |actual - requested| camera azimuth = {lag:.1f} deg")
            ids = list(rows[0]["spots"])
            print(f"\n{model}: visible fraction over a full orbit (polar 75 deg, every {STEP} deg)")
            print("  hotspot   model-viewer   app (mine)   truth (Python)   mv wrong at   app wrong at")
            for i in ids:
                mv = [r["theta"] for r in rows if r["spots"][i]["mv"]]
                ap = [r["theta"] for r in rows if r["spots"][i]["app"]]
                if model == "gapura":
                    tr = [r["theta"] for r in rows if r["spots"][i]["truth"]]
                    mv_bad = len(set(mv) ^ set(tr))
                    ap_bad = len(set(ap) ^ set(tr))
                    print(f"  {i:8s}  {len(mv) * STEP / 360:10.1%}   {len(ap) * STEP / 360:10.1%}   "
                          f"{len(tr) * STEP / 360:12.1%}     {mv_bad:3d} angles    {ap_bad:3d} angles")
                else:
                    print(f"  {i:8s}  {len(mv) * STEP / 360:10.1%}   {len(ap) * STEP / 360:10.1%}        (no reference: pyramid)")
        browser.close()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "occlusion.json"), "w") as f:
        json.dump(dict(step_deg=STEP, polar_deg=75, browser=which, rows=res), f, indent=1)
    g = res["gapura"]
    for i in ("celah", "tangga"):
        print(f"\n'{i}' windows (deg):")
        for key, lab in (("mv", "model-viewer"), ("app", "app (mine)"), ("truth", "truth")):
            th = [r["theta"] for r in g if r["spots"][i][key]]
            print(f"  {lab:13s} {windows(th)}  ({len(th) * STEP / 360:.0%})")
    print("\npredicted 'celah' window: [-39, 0] and [180, 219] deg (~22 %)")
    print("wrote out/occlusion.json")
    return res


if __name__ == "__main__":
    main()
