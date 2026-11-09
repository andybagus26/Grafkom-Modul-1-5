"""Lab 2 item 4 -- improvements driven by the pitfalls in Module5 Sec 12.
I ran BOTH options the lab offers, plus one extra control:

  A. Crushed-gradient pitfall: initialise sigma_raw at several values and
     record how fast the training MSE drops (8 spread views, same lr).
  B. Add a 3rd viewing angle to the buggy 2-view set [0, 20] and measure how
     much the held-out novel view (190 deg) recovers -- for several choices of
     the 3rd angle, not just one.
  C. Count vs coverage (Sec 12.3): 8 views packed into 21 deg vs the same 8
     views spread every 45 deg. Same number of photos, different spread.

    python lab2_improve.py          -> out/lab2_improve.json  (~2 min)

Metric. One held-out view is an anecdote: my first run of part B scored the
3rd view only on the 190 deg novel view and "found" that a 3rd view at 10 deg
(inside the cluster!) helped most. Scored on a RING of 24 held-out views
(7.5, 22.5, ..., 352.5 deg -- none equal to any training angle) the picture is
the expected one. So every run below reports: the 190 deg view (the module's),
the ring mean, the ring minimum, and the ring mean over views >= 30 deg away
from every training view ("far").

Everything is deterministic (fixed seeds, fixed sample depths), so the numbers
in the report are exactly what this prints.
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

import nerf_bug as nb
from nerf_toy import VoxelGrid, render_analytic, render_grid, ring_camera, psnr, train

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def _views(angles):
    v = [ring_camera(a, radius=nb.RADIUS, height=nb.CAM_HEIGHT) for a in angles]
    t = [render_analytic(nb.W, nb.H, nb.FOV, c, r, nb.NEAR, nb.FAR, nb.N_SAMPLES) for c, r in v]
    return v, t


def _novel():
    c, r = ring_camera(nb.NOVEL_ANGLE_DEG, radius=nb.RADIUS, height=nb.CAM_HEIGHT)
    return c, r, render_analytic(nb.W, nb.H, nb.FOV, c, r, nb.NEAR, nb.FAR, nb.N_SAMPLES)


RING = [7.5 + 15 * k for k in range(24)]
_RING_T = {}


def _ring_targets():
    if not _RING_T:
        for a in RING:
            c, r = ring_camera(a, radius=nb.RADIUS, height=nb.CAM_HEIGHT)
            _RING_T[a] = (c, r, render_analytic(nb.W, nb.H, nb.FOV, c, r, nb.NEAR, nb.FAR, nb.N_SAMPLES))
    return _RING_T


def _ang_dist(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def fit(angles, n_iters=nb.N_ITERS, init=None, log_every=None):
    views, targets = _views(angles)
    grid = VoxelGrid(resolution=12, seed=0)
    if init is not None:
        grid.sigma_raw[:] = init
    hist = train(grid, views, nb.W, nb.H, nb.FOV, targets, nb.NEAR, nb.FAR, nb.N_SAMPLES,
                 lr=nb.LR, n_iters=n_iters, log_every=log_every or n_iters - 1)
    tr = float(np.mean([psnr(render_grid(grid, nb.W, nb.H, nb.FOV, c, r, nb.NEAR, nb.FAR, nb.N_SAMPLES)[0], t)
                        for (c, r), t in zip(views, targets)]))
    nc, nr, nt = _novel()
    nv = psnr(render_grid(grid, nb.W, nb.H, nb.FOV, nc, nr, nb.NEAR, nb.FAR, nb.N_SAMPLES)[0], nt)
    ring = {a: psnr(render_grid(grid, nb.W, nb.H, nb.FOV, c, r, nb.NEAR, nb.FAR, nb.N_SAMPLES)[0], t)
            for a, (c, r, t) in _ring_targets().items()}
    far = [p for a, p in ring.items() if min(_ang_dist(a, x) for x in angles) >= 30]
    return dict(angles=list(angles), train_psnr=tr, novel_psnr=float(nv),
                ring_mean=float(np.mean(list(ring.values()))), ring_min=float(min(ring.values())),
                far_mean=float(np.mean(far)) if far else None, far_n=len(far),
                ring={str(a): float(p) for a, p in ring.items()},
                history=[(int(i), float(m)) for i, m in hist])


def _f(x):
    return "  n/a " if x is None else f"{x:6.2f}"


def part_a():
    print("A. sigma_raw initialisation sweep (8 spread views, lr=100, 500 iters)")
    print("   init  softplus'  sigma0   MSE@0    MSE@50   MSE@499  | 190deg  ring-mean ring-min (dB)")
    rows = []
    for init in (-8.0, -5.0, -3.0, -2.0, -1.0, -0.5, 0.0, 1.0, 3.0):
        r = fit(nb.FIXED_ANGLES, init=init, log_every=10)
        h = dict(r["history"])
        sp = 1.0 / (1.0 + np.exp(-init))
        print(f"   {init:4.1f}  {sp:.4f}    {np.logaddexp(0, init):.4f}  {h[0]:.5f}  {h[50]:.5f}  {h[499]:.5f}"
              f"  | {r['novel_psnr']:6.2f}  {r['ring_mean']:6.2f}    {r['ring_min']:6.2f}")
        rows.append(dict(init=init, softplus_grad=float(sp), **r))
    return rows


def part_b():
    print("\nB. buggy pair [0, 20] + one 3rd view; novel view at 190 deg (500 iters)")
    rows = []
    print("   views           train | 190deg  ring-mean ring-min  far-mean (n)   (dB)")
    base = fit(nb.BUGGY_ANGLES)
    rows.append(dict(third=None, **base))
    for third in (None, 10, 45, 90, 135, 180, 270):
        r = base if third is None else fit([0, 20, third])
        lab = "[0, 20]       " if third is None else f"[0, 20, {third:3d}]  "
        print(f"   {lab}  {r['train_psnr']:5.2f} | {r['novel_psnr']:6.2f}  {r['ring_mean']:6.2f}    {r['ring_min']:6.2f}"
              f"   {_f(r['far_mean'])} ({r['far_n']})")
        if third is not None:
            rows.append(dict(third=third, **r))
    return rows


def part_c():
    print("\nC. count vs coverage: 8 views either way (500 iters)")
    rows = []
    for label, angles in (("8 views packed in 21 deg", [0, 3, 6, 9, 12, 15, 18, 21]),
                          ("8 views every 45 deg", nb.FIXED_ANGLES)):
        r = fit(angles)
        print(f"   {label:26s} train {r['train_psnr']:.2f} | 190deg {r['novel_psnr']:.2f}"
              f"  ring-mean {r['ring_mean']:.2f}  ring-min {r['ring_min']:.2f}  (dB)")
        rows.append(dict(label=label, **r))
    return rows


if __name__ == "__main__":
    t0 = time.time()
    res = dict(A=part_a(), B=part_b(), C=part_c())
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "lab2_improve.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote out/lab2_improve.json  ({time.time() - t0:.0f} s)")
