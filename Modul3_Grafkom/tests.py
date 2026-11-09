#!/usr/bin/env python3
"""
tests.py
Tes otomatis Lab 1 + Lab 2. Setiap tes MENCETAK angkanya (bukan hanya "passed").

    python3 tests.py          (exit code 0 = semua lulus)
"""

import contextlib
import io
import math
import os
import sys

import numpy as np

import raster3d as R
import raytrace as RT
import transforms as T
import validate_obj
import worked_example as we
from metrics import fmt_psnr, psnr
from objio import Mesh
from ppm_io import read_ppm

FAILED = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def v(x, n=4):
    return "(" + ", ".join(f"{c:.{n}g}" for c in x) + ")"


# ---------------------------------------------------------------------------
# Lab 1
# ---------------------------------------------------------------------------
def lab1():
    print("\n--- Lab 1 ---")
    check("mymodel.obj valid (>=200 segitiga, UV, triangulated, winding CCW konsisten)",
          quiet(validate_obj.validate_obj, "mymodel.obj"))
    M, V, P, Vp = we.build_matrices()
    p = np.append(we.load_positions("mymodel.obj")[we.VERTEX_INDEX - 1], 1.0)
    pw, pv = M @ p, V @ M @ p
    check("object->world = hitungan tangan", np.allclose(pw[:3], [0.692820, -0.7, -1.4], atol=5e-4), v(pw[:3], 6))
    check("world->view = hitungan tangan", np.allclose(pv[:3], [0.692820, -1.084652, -5.260564], atol=5e-4), v(pv[:3], 6))
    pc = P @ pv
    check("w_clip == -z_view", math.isclose(pc[3], -pv[2], rel_tol=1e-12), f"w={pc[3]:.6f}")
    check("cek handedness scene Lab 1 lulus", quiet(we.handedness_checks, M, V, P, Vp))
    mirror = T.scale(-1.0, 1.0, 1.0)
    check("uji negatif: model dicerminkan terdeteksi", not quiet(we.handedness_checks, M @ mirror, V, P, Vp))
    check("uji negatif: kamera dicerminkan terdeteksi", not quiet(we.handedness_checks, M, mirror @ V, P, Vp))
    vp = Vp.copy(); vp[1, 1] = -Vp[1, 1]
    check("uji negatif: viewport tanpa flip y terdeteksi", not quiet(we.handedness_checks, M, V, P, vp))


# ---------------------------------------------------------------------------
# Lab 2: contoh E1..E5 dari modul
# ---------------------------------------------------------------------------
def e1():
    p = np.array([2.0, 3.0, 4.0, 1.0])
    Tm, Ry = T.translate(1, 0, -1), T.rot_y_deg(90)
    a = Ry @ Tm @ p                         # T dulu, lalu Ry  (kanan ke kiri)
    b = Tm @ Ry @ p                         # urutan lain
    d = T.perspective_divide_2d(a, 2.0)
    check("E1  (2,3,4) -T(1,0,-1)-> lalu Ry(90) = (3,3,-3)", np.allclose(a[:3], [3, 3, -3]), v(a[:3]))
    check("E1  bagi perspektif d=2 -> (2,2)", np.allclose(d, [2, 2]), v(d))
    # Catatan: modul hlm. 13 menulis (4,3,-4) untuk urutan ini, padahal di situ Ry diterapkan ke (3,3,3)
    # (titik yang SUDAH ditranslasi). Ry(90)(2,3,4) = (4,3,-2), lalu +(1,0,-1) = (5,3,-3), sesuai hlm. 22.
    check("E1  urutan terbalik (Ry dulu, lalu T) = (5,3,-3), titik berbeda", np.allclose(b[:3], [5, 3, -3]), v(b[:3]))


def e2():
    p = np.array([5.0, 0.0, 0.0, 1.0])
    cam = T.look_at((1, 0, 0), (1, 0, -1), (0, 1, 0)) @ p     # kamera +1 di x, menghadap -z
    mod = T.translate(-1, 0, 0) @ p                             # model -1 di x
    check("E2  kamera +1 di x == model -1 di x", np.allclose(cam, mod) and np.allclose(cam[:3], [4, 0, 0]),
          f"kamera {v(cam[:3])}  model {v(mod[:3])}")


def e3():
    P = T.perspective_deg(60, 1.0, 1.0, 9.0)
    out = []
    for z in (-1.0, -9.0, -3.0):
        c = P @ np.array([0, 0, z, 1.0])
        out.append(c[2] / c[3])
    check("E3  n=1,f=9: z=-1 -> -1, z=-9 -> +1, z=-3 -> 0.5", np.allclose(out, [-1, 1, 0.5]),
          f"A={P[2, 2]:.4g} B={P[2, 3]:.4g}  ndc z = {v(out)}")


def e4():
    t = 0.5
    uL, wL, uR, wR = 0.0, 1.0, 1.0, 9.0
    naive = (1 - t) * uL + t * uR
    corr = ((1 - t) * uL / wL + t * uR / wR) / ((1 - t) / wL + t / wR)
    # (render lantai sungguhan dengan rasteriser ada di perspective_check.py)
    check("E4  u di tengah layar: naif 0.5, perspective-correct 0.1", math.isclose(naive, 0.5) and math.isclose(corr, 0.1),
          f"naif {naive:.4f}  benar {corr:.4f}")


def e5():
    z = 0.25 * 0.20 + 0.25 * 0.50 + 0.50 * 0.90
    check("E5  depth barycentric 0.20/0.50/0.90 di (.25,.25,.5) = 0.625", math.isclose(z, 0.625), f"{z:.4f}")


def module2_edge():
    A, B, C = (1, 1), (6, 2), (3, 7)
    area = R.edge(A, B, *C)
    e = [R.edge(B, C, 3, 3), R.edge(C, A, 3, 3), R.edge(A, B, 3, 3)]
    out1 = [R.edge(B, C, 5, 5), R.edge(C, A, 5, 5), R.edge(A, B, 5, 5)]
    out2 = [R.edge(B, C, 1, 4), R.edge(C, A, 1, 4), R.edge(A, B, 1, 4)]
    check("Modul 2: edge(A,B,C)=28; (3,3) di dalam; (5,5),(1,4) di luar",
          area == 28 and min(e) > 0 and min(out1) < 0 and min(out2) < 0,
          f"area={area}, (3,3)->{e}, (5,5)->{out1}, (1,4)->{out2}")
    lam = np.array(e) / area
    check("Modul 2: barycentric di (3,3) berjumlah 1", math.isclose(lam.sum(), 1.0), v(lam))


def near_clip():
    # segitiga yang menembus near plane: satu vertex di belakang kamera
    P = T.perspective_deg(60, 1.0, 1.0, 50.0)
    pts = np.array([[-1.0, -0.5, -3.0], [1.0, -0.5, -3.0], [0.0, -0.5, 2.0]])     # vertex ke-3 di BELAKANG kamera
    clip = (P @ T.to_homogeneous(pts).T).T
    pieces = R.clip_near(clip, np.zeros((3, 2)))
    ok = len(pieces) == 2 and all((vc[:, 2] + vc[:, 3] >= -1e-12).all() and (vc[:, 3] > 0).all() for vc, _ in pieces)
    check("near clip: 1 vertex di belakang kamera -> 2 segitiga, semua w > 0", ok,
          f"{len(pieces)} potongan, w min {min(vc[:, 3].min() for vc, _ in pieces):.3f}")
    m = Mesh(pts, np.zeros((0, 2)), np.array([[0, 1, 2]]), None)
    r = R.render(m, 64, 64, model=np.eye(4), eye=(0, 0, 0), target=(0, 0, -1), fovy_deg=60, near=1.0, far=50,
                 light_dir=(0, 1, 0), ambient=1.0)
    rows = np.nonzero(np.isfinite(r.depth).any(axis=1))[0]
    check("near clip: render tidak 'mencoreng' ke atas layar (hanya separuh bawah terisi)",
          len(rows) > 0 and rows.min() >= 32, f"baris terisi {rows.min()}..{rows.max()}")


def pipeline_shapes():
    # Modul memakai perspective(60deg, aspect=1, 1, 50) walau frame-nya 800x600. Angka (589,158) hanya
    # keluar dengan aspect=1 itu. Dengan aspect yang benar (4/3), x layar = 541.7 (lihat baris kedua).
    V = T.look_at((0, 0, 8), (0, 0, 0), (0, 1, 0))
    M = T.rot_y_deg(90) @ T.translate(1, 0, -1)
    clip, ndc = T.project(T.perspective_deg(60, 1.0, 1, 50), V, M, [[2, 3, 4]])
    s = T.viewport_points(ndc, 800, 600)
    check("Contoh terpandu (aspect=1 seperti modul): clip (5.196,5.196,9.408,11), layar (589,158), depth 0.855",
          np.allclose(clip[0], [5.196, 5.196, 9.408, 11], atol=1e-3) and np.allclose(s[0, :2], [589, 158], atol=1)
          and abs(ndc[0, 2] - 0.855) < 1e-3, f"clip {v(clip[0])} ndc {v(ndc[0])} layar ({s[0, 0]:.1f}, {s[0, 1]:.1f})")
    _, ndc43 = T.project(T.perspective_deg(60, 800 / 600, 1, 50), V, M, [[2, 3, 4]])
    s43 = T.viewport_points(ndc43, 800, 600)
    check("Contoh terpandu dengan aspect benar 4/3: x layar 541.7 (y tetap 158.3)",
          np.allclose(s43[0, :2], [541.7, 158.3], atol=0.1), f"layar ({s43[0, 0]:.1f}, {s43[0, 1]:.1f})")


def one_triangle():
    pos = np.array([[-0.8, -0.6, -2.0], [0.9, -0.7, -2.0], [-0.2, 0.9, -2.0]])
    m = Mesh(pos, np.zeros((0, 2)), np.array([[0, 1, 2]]), None)
    r = R.render(m, 64, 64, model=np.eye(4), eye=(0, 0, 0), target=(0, 0, -1), fovy_deg=60, near=1.0, far=50,
                 light_dir=(0, 0, 1), ambient=0.2)
    fin = np.isfinite(r.depth)
    check("1 segitiga datar: mengisi region wajar, depth seragam",
          300 < fin.sum() < 2500 and np.ptp(r.depth[fin]) < 1e-9, f"{int(fin.sum())} piksel, depth {r.depth[fin].mean():.4f}")


def overlap():
    front = [[-0.7, -0.7, -1.5], [0.7, -0.7, -1.5], [0.0, 0.7, -1.5]]
    back = [[-0.2, -0.7, -3.0], [1.2, -0.7, -3.0], [0.5, 0.7, -3.0]]
    kw = dict(model=np.eye(4), eye=(0, 0, 0), target=(0, 0, -1), fovy_deg=60, near=1.0, far=50, light_dir=(0, 0, 1), ambient=1.0)
    cols = [(255, 0, 0), (0, 0, 255)]
    for order, name in (([0, 1], "depan dulu"), ([1, 0], "belakang dulu")):
        pos = np.array([front, back][order[0]] + [front, back][order[1]])
        m = Mesh(pos, np.zeros((0, 2)), np.array([[0, 1, 2], [3, 4, 5]]), None)
        r = R.render(m, 64, 64, tri_colors=[cols[order[0]], cols[order[1]]], **kw)
        blue_over_red = int(((r.color[..., 2] > 0) & np.isfinite(r.depth) &
                             (np.abs(r.depth - r.depth.min()) < 1e-9)).sum())
        check(f"z-buffer: dua segitiga bertumpuk, urutan gambar {name}: belakang tidak pernah menang di depan",
              blue_over_red == 0, f"piksel biru di depth depan = {blue_over_red}")


def reference_frame():
    if not os.path.exists("ref/temple_ref.ppm"):
        check("frame candi vs ref/temple_ref.ppm", False, "ref/temple_ref.ppm tidak ada"); return
    mesh, tex = R.load_scene("temple")
    col = R.render(mesh, 160, 160, tex_u8=tex, **R.scene_kwargs("temple")).color
    ref = read_ppm("ref/temple_ref.ppm")
    p = psnr(col, ref)
    check("frame candi 160x160 vs ref/temple_ref.ppm (PSNR >= 60 dB)", p >= 60, f"PSNR {fmt_psnr(p)} dB, "
          f"{int((np.abs(col.astype(int) - ref).max(axis=2) > 0).sum())} piksel beda")


def raster_vs_raytrace():
    for scene in ("temple", "mymodel"):
        mesh, tex = R.load_scene(scene)
        kw = R.scene_kwargs(scene)
        a = R.render(mesh, 128, 128, tex_u8=tex, **kw).color
        b, _ = RT.render(mesh, 128, 128, tex_u8=tex, **kw)
        p = psnr(a, b)
        check(f"raster vs raytrace ({scene}, 128x128) PSNR >= 60 dB", p >= 60, f"PSNR {fmt_psnr(p)} dB")


def lab2():
    print("\n--- Lab 2 ---")
    for f in (e1, e2, e3, e4, e5, module2_edge, near_clip, pipeline_shapes, one_triangle, overlap,
              reference_frame, raster_vs_raytrace):
        f()


if __name__ == "__main__":
    lab1()
    lab2()
    print("-" * 70)
    if FAILED:
        print(f"{len(FAILED)} tes GAGAL: {FAILED}")
        sys.exit(1)
    print("Semua tes lulus.")
