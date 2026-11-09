"""Module 5 test suite. Run: python tests.py -> ALL CHECKS PASSED (N ok), ~20 s

Starter checks (unchanged): E1 ray, E2 compositing, analytic-vs-finite-
difference gradient, view-coverage diagnose-and-fix.

Added by me (Andy Bagus, 20241337033) -- each one guards a change or a finding
written up in the report:
  * the gradient check only probes voxels a ray actually touches and uses a
    RELATIVE error (an untouched voxel has gradient 0 on both sides and
    "passes" for free; an absolute 1e-6 tolerance passes anything small);
  * the stable backward (R recurrence, cached T) equals the module's v1 where
    v1 is valid, and stays right where v1 is wrong (alpha < 1e-8);
  * break-it-on-purpose: three deliberately wrong backward passes are each
    caught by the same check (the test has teeth);
  * my scene extension, the PPM loader, the crushed-gradient pitfall;
  * the AR models: no inward-facing triangles (the starter stupa had 6),
    real-world size, and hotspots that sit on the surface they describe.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from ray_generator import running_example as ray_running_example
from volume_render import running_example as vr_running_example
from nerf_toy import (VoxelGrid, render_grid, backward_grid, ring_camera, scene_density_color, train,
                      render_analytic)
import nerf_bug

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ar_app"))

_checks = 0


def _count():
    global _checks
    _checks += 1


def check(name, got, want, tol=1e-6):
    ok = abs(got - want) <= tol
    print(f"[{'ok' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")
    assert ok, f"{name}: got {got!r}, want {want!r}"
    _count()


def check_true(name, cond):
    print(f"[{'ok' if cond else 'FAIL'}] {name}")
    assert cond, name
    _count()


def check_vec(name, got, want, tol=1e-3):
    for g, w in zip(got, want):
        check(f"{name} ({w})", float(g), w, tol)


# --------------------------------------------------------------------------- starter
def test_ray_generator():
    dir_cam, norm_dir = ray_running_example()
    check_vec("E1 pinhole ray, camera-space (unnormalised)", dir_cam, (0.8, 0.0, -1.0))
    check_vec("E1 pinhole ray, normalised", norm_dir, (0.625, 0.0, -0.781), tol=1e-3)
    check("E1 normalised ray has unit length", float(np.linalg.norm(norm_dir)), 1.0, tol=1e-9)


def test_volume_render():
    final_color, weights, transmittance, bg_weight = vr_running_example()
    check_vec("E2 volume-render weights", weights, (0.5, 0.25, 0.25))
    check("E2 background weight", float(bg_weight), 0.0, tol=1e-9)
    check("E2 weights + background sum to 1", float(weights.sum() + bg_weight), 1.0, tol=1e-9)
    check_vec("E2 final pixel colour", final_color, (0.5, 0.25, 0.25))


# --------------------------------------------------------------------------- gradient
W_G, H_G, FOV_G = 4, 3, 50.0
CAM_G, C2W_G = ring_camera(30.0, radius=3.0, height=1.0)
TARGET_G = np.random.default_rng(4).uniform(0, 1, size=(H_G, W_G, 3))


def _grid(sigma_init=None):
    g = VoxelGrid(resolution=4, seed=1)
    rng = np.random.default_rng(2)
    g.sigma_raw = rng.normal(0, 1, size=g.sigma_raw.shape) if sigma_init is None \
        else np.full(g.sigma_raw.shape, float(sigma_init))
    g.color_raw = rng.normal(0, 1, size=g.color_raw.shape)
    return g


def _loss(g):
    image, cache = render_grid(g, W_G, H_G, FOV_G, CAM_G, C2W_G, near=1.0, far=5.0, n_samples=8)
    return float(np.sum((image - TARGET_G) ** 2)), image, cache


def gradcheck(g, variant="stable", eps=1e-4):
    """Worst RELATIVE error |a - n| / (|a| + |n|) between the analytic gradient
    and a central finite difference, over every voxel (density) and every
    colour channel that at least one ray touches. Returns (err, n_probed)."""
    _, image, cache = _loss(g)
    g.zero_grad()
    backward_grid(g, cache, 2.0 * (image - TARGET_G), variant)
    a_sig, a_col = g.sigma_grad.copy(), g.color_grad.copy()
    touched = sorted({tuple(int(v) for v in np.unravel_index(i, g.sigma_raw.shape))
                      for i in cache["flat_idx"].reshape(-1)})
    worst, n = 0.0, 0
    for arr, grad, idxs in ((g.sigma_raw, a_sig, touched),
                            (g.color_raw, a_col, [t + (c,) for t in touched for c in range(3)])):
        for idx in idxs:
            o = arr[idx]
            arr[idx] = o + eps
            lp = _loss(g)[0]
            arr[idx] = o - eps
            lm = _loss(g)[0]
            arr[idx] = o
            num = (lp - lm) / (2 * eps)
            denom = abs(num) + abs(grad[idx])
            if denom > 1e-12:          # both ~0: nothing to compare
                worst = max(worst, abs(num - grad[idx]) / denom)
            n += 1
    return worst, n


def test_backward_matches_finite_difference():
    err, n = gradcheck(_grid())
    print(f"[{'ok' if err < 1e-6 else 'FAIL'}] analytic vs finite-difference gradient over all {n} touched "
          f"parameters, max relative err = {err:.2e}")
    assert err < 1e-6
    _count()


def test_stable_equals_v1_where_v1_is_valid():
    g = _grid()
    _, image, cache = _loss(g)
    d = 2.0 * (image - TARGET_G)
    g.zero_grad(); backward_grid(g, cache, d, "stable"); s = (g.sigma_grad.copy(), g.color_grad.copy())
    g.zero_grad(); backward_grid(g, cache, d, "v1"); v = (g.sigma_grad.copy(), g.color_grad.copy())
    diff = max(np.abs(s[0] - v[0]).max(), np.abs(s[1] - v[1]).max())
    check_true(f"stable backward == module's v1 backward at ordinary densities (max diff {diff:.1e})", diff < 1e-12)


def test_low_density_regime():
    # sigma_raw = -20 -> sigma ~ 2e-9, alpha ~ 1e-9 < 1e-8: v1 recovers T = w / clip(alpha, 1e-8)
    # and gets T wrong; the stable version caches T from the forward pass. FD step 1e-2:
    # the gradients here are ~1e-9, so a 1e-4 step drowns in round-off.
    e_s, _ = gradcheck(_grid(-20.0), "stable", eps=1e-2)
    e_v, _ = gradcheck(_grid(-20.0), "v1", eps=1e-2)
    check_true(f"near-empty voxels (sigma_raw=-20): stable rel err {e_s:.1e} < 1e-2", e_s < 1e-2)
    check_true(f"near-empty voxels (sigma_raw=-20): module v1 rel err {e_v:.1e} > 0.1 (the latent bug)", e_v > 0.1)


def test_check_has_teeth():
    for variant in ("drop_suffix", "drop_bg", "no_softplus"):
        err, _ = gradcheck(_grid(), variant)
        check_true(f"break on purpose [{variant}]: gradient check fails loudly (max rel err {err:.2f} >> 1e-6)",
                   err > 0.1)


# --------------------------------------------------------------------------- reconstruction
def test_view_coverage_diagnose_and_fix():
    result = nerf_bug.diagnose_and_fix()
    gap = result["fixed_novel_psnr"] - result["buggy_novel_psnr"]
    check_true(f"8-view vs 2-view novel-view PSNR gap = {gap:.2f} dB (want > 1.0 dB)", gap > 1.0)


def test_crushed_gradient_pitfall():
    views = [ring_camera(a, 3.0, 1.0) for a in (0, 90, 180, 270)]
    targets = [render_analytic(20, 16, 50.0, c, r) for c, r in views]
    drops = {}
    for init in (-8.0, 0.0):
        g = VoxelGrid(12, seed=0, init_sigma_raw=init)
        h = train(g, views, 20, 16, 50.0, targets, lr=100.0, n_iters=40, log_every=39)
        drops[init] = 1 - h[-1][1] / h[0][1]
    check_true(f"crushed gradient: init -8 lowers MSE by {drops[-8.0]:.2%} in 40 iters, init 0 by "
               f"{drops[0.0]:.1%}", drops[-8.0] < 0.01 and drops[0.0] > 0.3)


def test_my_scene():
    pts = np.array([[0.78, -0.3, 0.0],     # in the gateway passage: empty
                    [0.78, -0.3, 0.3],     # inside one half: brick
                    [0.78, 0.2, 0.3],      # top step
                    [0.0, 0.0, 0.0],       # temple body: same in both scenes
                    [0.95, 0.0, 0.0]])     # outside everything
    s_p, c_p = scene_density_color(pts, "pusaka")
    s_a, c_a = scene_density_color(pts, "andy")
    check_true("my scene: passage empty, both halves + top step solid red brick",
               s_a[0] == 0 and s_a[1] > 0 and s_a[2] > 0 and np.allclose(c_a[1], (0.66, 0.30, 0.20)))
    check_true("my scene: temple and empty space identical to the module scene",
               s_a[3] == s_p[3] and np.allclose(c_a[3], c_p[3]) and s_a[4] == s_p[4] == 0)


def test_ppm_roundtrip():
    from capture import save_ppm, load_ppm
    img = np.random.default_rng(0).uniform(0, 1, (5, 7, 3))
    path = os.path.join(HERE, "out", "_roundtrip.ppm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_ppm(path, img)
    back = load_ppm(path)
    os.remove(path)
    check_true(f"PPM save/load round trip within half a code value (max err {np.abs(back - img).max():.5f})",
               back.shape == img.shape and np.abs(back - img).max() <= 0.5 / 255 + 1e-12)


# --------------------------------------------------------------------------- AR assets
def _glb_triangles(path):
    import pygltflib
    g = pygltflib.GLTF2().load_binary(path)
    blob = g.binary_blob()

    def acc(i, comps, dtype):
        a = g.accessors[i]
        bv = g.bufferViews[a.bufferView]
        n = a.count * comps
        return np.frombuffer(blob[bv.byteOffset: bv.byteOffset + n * np.dtype(dtype).itemsize],
                             dtype=dtype).reshape(-1, comps)
    out = []
    for m in g.meshes:
        pr = m.primitives[0]
        P = acc(pr.attributes.POSITION, 3, "<f4")
        N = acc(pr.attributes.NORMAL, 3, "<f4")
        I = acc(pr.indices, 1, "<u2").reshape(-1, 3)
        out.append((m.name, P, N, I))
    return out


def _bad_triangles(meshes):
    bad = 0
    for _, P, N, I in meshes:
        c = P.mean(axis=0)
        for t in I:
            a, b, d = P[t]
            gn = np.cross(b - a, d - a)
            if gn @ N[t[0]] <= 0 or gn @ ((a + b + d) / 3 - c) <= 0:
                bad += 1
    return bad


def test_ar_models():
    import make_temple_glb as mt
    import make_gapura_glb as mg
    assets = os.path.join(HERE, "ar_app", "assets")
    for glb, n_parts, height in (("pusaka_temple.glb", 6, 0.42), ("gapura_bentar.glb", len(mg.PARTS), 15.5 / 50)):
        meshes = _glb_triangles(os.path.join(assets, glb))
        top = max(float(P[:, 1].max()) for _, P, _, _ in meshes)
        check_true(f"{glb}: {len(meshes)} meshes, every triangle faces outward ({_bad_triangles(meshes)} bad), "
                   f"height {top:.3f} m", len(meshes) == n_parts and _bad_triangles(meshes) == 0
                   and abs(top - height) < 1e-3)
    # the starter's pyramid() winding, for the record: its side triangles were
    # (p0, p1, apex) with the normal from that order -- i.e. the fixed ones with
    # the first two vertices swapped and the normal negated. All inward.
    P, N, I = mt.pyramid((0, 0.30, 0), 0.03, 0.12)
    sides = I.reshape(-1, 3)[:4]
    P_old, N_old = P.copy(), N.copy()
    for t in sides:
        P_old[t[0]], P_old[t[1]] = P[t[1]].copy(), P[t[0]].copy()
        N_old[t] = -N[t]
    stupa_c = np.array([0, 0.30 + 0.12 / 4, 0])
    inward = sum(float(np.cross(P_old[t[1]] - P_old[t[0]], P_old[t[2]] - P_old[t[0]])
                       @ (P_old[t].mean(axis=0) - stupa_c)) < 0 for t in sides)
    check_true(f"starter stupa winding (p0, p1, apex) reproduced: {inward}/4 sides face inward; fixed: "
               f"{_bad_triangles([('new', P, N, I.reshape(-1, 3))])} bad", inward == 4
               and _bad_triangles([("new", P, N, I.reshape(-1, 3))]) == 0)

    # hotspots: generated file == generator (no drift), and each one sits 1 mm off a face of its part
    with open(os.path.join(assets, "gapura_bentar.json"), encoding="utf-8") as f:
        on_disk = json.load(f)["hotspots"]
    check_true("gapura_bentar.json matches make_gapura_glb.py (regenerated, no drift)",
               json.dumps(on_disk, sort_keys=True) == json.dumps(mg.HOTSPOTS, sort_keys=True))
    ok = True
    for h in mg.HOTSPOTS:
        spec = mg.PARTS[h["part"]]
        c, hh, p, n = (np.array(spec["center"]), np.array(spec["half"]), np.array(h["position"]),
                       np.array(h["normal"]))
        k = int(np.argmax(np.abs(n)))
        on_face = abs((p[k] - c[k]) * np.sign(n[k]) - hh[k] - 0.001) < 1e-4
        inside = all(abs(p[j] - c[j]) <= hh[j] + 1e-9 for j in range(3) if j != k)
        ok &= bool(on_face and inside)
    check_true(f"all {len(mg.HOTSPOTS)} candi bentar hotspots sit 1 mm off the face they name", ok)
    check_true("both models' bilingual text is complete (name/text in EN and ID for every hotspot)",
               all(all(h.get(f"{f}_{l}") for f in ("name", "text") for l in ("en", "id"))
                   for h in mg.HOTSPOTS + mt.HOTSPOTS))


def test_provenance_lint():
    """Lab 1 item 5(c): the automated check that would have caught a missing
    provenance line. Every model shipped in ar_app/assets/ must be named in
    README.md's provenance paragraph together with a licence."""
    with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    block = readme.split("**Provenance", 1)[1].split("## ", 1)[0] if "**Provenance" in readme else ""
    glbs = sorted(f for f in os.listdir(os.path.join(HERE, "ar_app", "assets")) if f.endswith(".glb"))
    missing = []
    for g in glbs:
        i = block.find(g)
        if i < 0 or "CC0" not in block[i: i + 400] and "CC BY" not in block[i: i + 400]:
            missing.append(g)
    check_true(f"provenance lint: every shipped model {glbs} has a README provenance line with a licence "
               f"(missing: {missing})", not missing and bool(glbs))


if __name__ == "__main__":
    test_ray_generator()
    test_volume_render()
    test_backward_matches_finite_difference()
    test_stable_equals_v1_where_v1_is_valid()
    test_low_density_regime()
    test_check_has_teeth()
    test_view_coverage_diagnose_and_fix()
    test_crushed_gradient_pitfall()
    test_my_scene()
    test_ppm_roundtrip()
    test_ar_models()
    test_provenance_lint()
    print(f"\nALL CHECKS PASSED ({_checks} ok)")
