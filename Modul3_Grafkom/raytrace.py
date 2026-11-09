"""
raytrace.py
Ray tracer satu frame (arah "mundur"/image-order): satu ray pinhole per piksel, Moller-Trumbore ke
setiap segitiga, ambil hit terdekat, lalu texture + Lambert dengan aturan yang SAMA dengan raster3d.py.
Dua renderer yang ditulis independen harus menghasilkan frame yang sama; selisih yang besar berarti
ada transform, pembagian w, atau barycentric yang salah di salah satunya.

Pakai:
    python3 raytrace.py --scene temple  --w 512 --h 512
    python3 raytrace.py --scene mymodel --w 512 --h 512
"""

import argparse
import os
import time

import numpy as np

import transforms as T
from colorspace import linear_to_srgb, srgb_to_linear
from ppm_io import write_ppm
from raster3d import SCENES, load_scene, sample_bilinear, scene_kwargs


def moller_trumbore(orig, dirs, v0, v1, v2, eps=1e-9):
    """Ray (orig + t*dir) vs segitiga (v0,v1,v2), tervektorisasi atas semua ray dirs (N,3).
    Selesaikan orig + t d = (1-b1-b2) v0 + b1 v1 + b2 v2 dengan aturan Cramer:
        e1 = v1-v0, e2 = v2-v0, p = d x e2, det = e1.p
        s = orig - v0, b1 = s.p/det, q = s x e1, b2 = d.q/det, t = e2.q/det
    Tanpa culling (det boleh negatif), sama seperti raster3d tanpa --cull.
    Mengembalikan (t, b1, b2) dengan t = inf untuk yang tidak kena."""
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(dirs, e2)
    det = p @ e1
    ok = np.abs(det) > eps
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = orig - v0
    b1 = (p @ s) * inv
    q = np.cross(s, e1)
    b2 = (dirs @ q) * inv
    t = (q @ e2) * inv
    hit = ok & (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1) & (t > eps)
    return np.where(hit, t, np.inf), b1, b2


def occluded(origins, L, tris, eps=1e-9):
    """Shadow ray: dari tiap titik (N,3) ke arah light directional L (satu arah untuk semua).
    Karena arah sama, p = L x e2 dan det cukup dihitung sekali per segitiga. True = ada penghalang."""
    hit = np.zeros(len(origins), dtype=bool)
    for v0, v1, v2 in tris:
        e1, e2 = v1 - v0, v2 - v0
        p = np.cross(L, e2)
        det = float(p @ e1)
        if abs(det) <= eps:
            continue
        s = origins - v0
        b1 = (s @ p) / det
        q = np.cross(s, e1)
        b2 = (q @ L) / det
        t = (q @ e2) / det
        hit |= (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1) & (t > 1e-6)
    return hit


def render(mesh, w, h, *, model, eye, target, fovy_deg, near, far, light_dir, ambient,
           up=(0.0, 1.0, 0.0), tex_u8=None, flat_from=None, shadows=False):
    world = (model @ T.to_homogeneous(mesh.positions).T).T[:, :3]
    tris = world[mesh.faces]
    tuv = mesh.triangle_uvs()

    # Basis kamera dari matriks view yang SAMA dengan rasteriser: baris V = kanan, atas, belakang.
    V = T.look_at(eye, target, up)
    right, upv, back = V[0, :3], V[1, :3], V[2, :3]
    eye = np.asarray(eye, dtype=np.float64)
    th = np.tan(np.radians(fovy_deg) / 2.0)
    j, i = np.meshgrid(np.arange(w), np.arange(h))
    ndc_x = (j + 0.5) / w * 2.0 - 1.0                      # pusat piksel -> NDC (kebalikan viewport)
    ndc_y = 1.0 - (i + 0.5) / h * 2.0                       # y layar ke bawah, NDC ke atas
    dirs = (ndc_x[..., None] * (th * w / h) * right + ndc_y[..., None] * th * upv - back).reshape(-1, 3)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)

    best_t = np.full(len(dirs), np.inf)
    best_f = np.full(len(dirs), -1)
    best_uv = np.zeros((len(dirs), 2))
    for fi, (v0, v1, v2) in enumerate(tris):
        t, b1, b2 = moller_trumbore(eye, dirs, v0, v1, v2)
        closer = t < best_t
        if closer.any():
            best_t[closer] = t[closer]
            best_f[closer] = fi
            b0 = 1.0 - b1[closer] - b2[closer]
            # barycentric di WORLD space: otomatis perspective-correct, tanpa trik u/w
            best_uv[closer] = (b0[:, None] * tuv[fi, 0] + b1[closer, None] * tuv[fi, 1] + b2[closer, None] * tuv[fi, 2])

    L = np.asarray(light_dir, dtype=np.float64)
    L /= np.linalg.norm(L)
    tex_lin = None if tex_u8 is None else srgb_to_linear(tex_u8.astype(np.float64) / 255.0)
    # normal datar per segitiga, diarahkan ke kamera (aturan dua sisi yang sama dengan raster3d)
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    fn *= np.where(np.einsum("ij,ij->i", fn, eye - tris[:, 0]) < 0, -1.0, 1.0)[:, None]

    hitm = best_f >= 0
    f = best_f[hitm]
    ndotl = np.maximum(0.0, fn[f] @ L)
    shade = ambient + (1.0 - ambient) * ndotl
    if shadows:
        # SEMUA shadow ray sekaligus (satu panggilan): titik kena + offset kecil di sepanjang normal
        # (mencegah ray mengenai segitiganya sendiri = versi ray dari shadow acne)
        lit = ndotl > 0
        pts = eye + dirs[hitm][lit] * best_t[hitm][lit, None] + fn[f[lit]] * 1e-5
        blocked = np.zeros(len(f), dtype=bool)
        blocked[np.nonzero(lit)[0]] = occluded(pts, L, tris)
        shade = np.where(blocked, ambient, shade)

    base = np.full((len(f), 3), 0.7)
    if tex_lin is not None:
        textured = np.ones(len(f), dtype=bool) if flat_from is None else f < flat_from
        base[textured] = sample_bilinear(tex_lin, best_uv[hitm][textured, 0], best_uv[hitm][textured, 1])
    col = np.zeros((len(dirs), 3))
    col[hitm] = np.clip(base * shade[:, None], 0.0, 1.0)
    img = np.clip(linear_to_srgb(col) * 255.0, 0, 255).astype(np.uint8).reshape(h, w, 3)
    return img, best_t.reshape(h, w)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", choices=list(SCENES), default="temple")
    ap.add_argument("--model")
    ap.add_argument("--tex")
    ap.add_argument("--w", type=int, default=512)
    ap.add_argument("--h", type=int, default=512)
    ap.add_argument("--out")
    args = ap.parse_args()
    mesh, tex = load_scene(args.scene, args.model, args.tex)
    out = args.out or f"out/{args.scene}_rt.ppm"
    t0 = time.perf_counter()
    img, t = render(mesh, args.w, args.h, tex_u8=tex, **scene_kwargs(args.scene))
    dt = time.perf_counter() - t0
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    write_ppm(out, img)
    print(f"scene={args.scene} segitiga={mesh.n_tris} frame={args.w}x{args.h} "
          f"piksel-kena={int(np.isfinite(t).sum())}/{args.w * args.h}")
    print(f"waktu render {dt:.3f} s")
    print(f"tulis {out}")


if __name__ == "__main__":
    main()
