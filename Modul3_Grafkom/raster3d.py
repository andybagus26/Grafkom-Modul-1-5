"""
raster3d.py
Rasteriser 3D dari nol (NumPy saja):
    MVP -> near clip (clip space) -> bagi w -> viewport -> z-buffer barycentric (top-left rule)
        -> texture bilinear perspective-correct (opsional mipmap trilinear) -> Lambert satu light

Konvensi (lihat transforms.py): column vector, P @ V @ M @ p; kamera menghadap -z; NDC [-1,1]^3 dengan
near di z=-1; viewport membalik y; CCW (di NDC) = front face; v texture dibalik sekali saat load OBJ.

Pakai:
    python3 raster3d.py --scene temple  --w 512 --h 512      # candi starter, cocokkan ref/
    python3 raster3d.py --scene mymodel --w 512 --h 512      # model sendiri (Lab 1)
    python3 raster3d.py --scene temple --cull                # back-face culling (Lab 2 langkah 5)
"""

import argparse
import os
import time
from dataclasses import dataclass, field

import numpy as np

import transforms as T
from colorspace import linear_to_srgb, srgb_to_linear
from objio import load_obj
from ppm_io import read_ppm, write_ppm

# ---------------------------------------------------------------------------
# Scene yang dipakai bersama raster3d.py, raytrace.py, dan web/ (Lab 3)
# ---------------------------------------------------------------------------
SCENES = {
    # Parameter scene candi disamakan dengan studi kasus modul, supaya frame bisa dicocokkan dengan
    # ref/temple_ref.ppm. Kamera/light ini angka dari modul, bukan pilihan bebas.
    "temple": dict(obj="data/pusaka_model.obj", tex="data/relief.ppm",
                   model=lambda: T.rot_y_deg(35) @ T.scale(1.4, 1.4, 1.4),
                   eye=(2.6, 2.0, 3.4), target=(0.0, 0.7, 0.0), fovy_deg=45.0, near=1.0, far=14.0,
                   light_dir=(0.4, 0.9, 0.6), ambient=0.15),
    # Model sendiri (mymodel.obj). Kamera sama dengan web/viewer.js.
    "mymodel": dict(obj="mymodel.obj", tex="texture.ppm",
                    model=lambda: T.rot_y_deg(35),
                    eye=(0.0, 1.2, 3.8), target=(0.0, 0.0, 0.0), fovy_deg=50.0, near=0.1, far=30.0,
                    light_dir=(0.5, 0.8, 0.6), ambient=0.25),
}


def scene_kwargs(name):
    """Argumen kamera/light/model untuk render() dari nama scene."""
    s = dict(SCENES[name])
    s.pop("obj"); s.pop("tex")
    s["model"] = s["model"]()
    return s


# ---------------------------------------------------------------------------
# Texture: bilinear, mipmap
# ---------------------------------------------------------------------------
def sample_bilinear(tex_lin, u, v):
    """tex_lin (H,W,3) linear light; u, v array sembarang bentuk (wrap/repeat).
    v di sini sudah koordinat baris citra (0 = baris atas), karena objio membalik v saat load.
    Pemetaan texel: x = u*(W-1), y = v*(H-1), konvensi yang sama dengan renderer referensi,
    supaya frame bisa dicocokkan dengan ref/temple_ref.ppm."""
    H, W = tex_lin.shape[:2]
    x = np.mod(u, 1.0) * (W - 1)
    y = np.mod(v, 1.0) * (H - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    top = tex_lin[y0, x0] * (1 - fx) + tex_lin[y0, x1] * fx
    bot = tex_lin[y1, x0] * (1 - fx) + tex_lin[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def build_mipmap(tex_lin, levels=4):
    """Piramida mip: level k+1 = rata-rata box 2x2 dari level k, dikerjakan di LINEAR light
    (gamma-correct, Modul 1). tex_lin sudah linear, jadi rata-rata langsung benar."""
    pyr = [tex_lin]
    for _ in range(levels - 1):
        t = pyr[-1]
        h, w = (t.shape[0] // 2) * 2, (t.shape[1] // 2) * 2
        t = t[:h, :w]
        pyr.append(0.25 * (t[0::2, 0::2] + t[1::2, 0::2] + t[0::2, 1::2] + t[1::2, 1::2]))
    return pyr


def sample_trilinear(pyr, u, v, lod):
    """Sampling mipmap: bilinear di dua level terdekat floor(lod), floor(lod)+1, lalu dicampur."""
    lod = np.clip(lod, 0.0, len(pyr) - 1)
    l0 = np.floor(lod).astype(np.int64)
    l1 = np.minimum(l0 + 1, len(pyr) - 1)
    t = (lod - l0)[..., None]
    out = np.zeros(u.shape + (3,))
    for k in range(len(pyr)):
        m0, m1 = l0 == k, l1 == k
        if m0.any():
            out[m0] += sample_bilinear(pyr[k], u[m0], v[m0]) * (1 - t[m0])
        if m1.any():
            out[m1] += sample_bilinear(pyr[k], u[m1], v[m1]) * t[m1]
    return out


# ---------------------------------------------------------------------------
# Near-plane clipping (Sutherland-Hodgman, satu bidang) di CLIP space
# ---------------------------------------------------------------------------
def clip_near(vc, attrs):
    """vc: (3,4) vertex clip space, attrs: (3,k) atribut per vertex.
    Bidang near di clip space: z = -w, sisi dalam: d = z + w >= 0 (setara z_eye <= -near, jadi w > 0).
    Dikerjakan SEBELUM bagi w: vertex di belakang kamera (w <= 0) kalau dibagi akan terlempar ke sisi
    layar yang salah. Interpolasi linear sah di clip space karena belum ada pembagian.
    Mengembalikan list (vc', attrs') berisi 0, 1, atau 2 segitiga (urutan/winding dipertahankan)."""
    d = vc[:, 2] + vc[:, 3]
    inside = d >= 0
    if inside.all():
        return [(vc, attrs)]
    if not inside.any():
        return []
    pv, pa = [], []
    for i in range(3):
        j = (i + 1) % 3
        if inside[i]:
            pv.append(vc[i]); pa.append(attrs[i])
        if inside[i] != inside[j]:
            t = d[i] / (d[i] - d[j])
            pv.append(vc[i] + t * (vc[j] - vc[i]))
            pa.append(attrs[i] + t * (attrs[j] - attrs[i]))
    return [(np.array([pv[0], pv[k], pv[k + 1]]), np.array([pa[0], pa[k], pa[k + 1]]))
            for k in range(1, len(pv) - 1)]


# ---------------------------------------------------------------------------
# Edge function (Modul 2) dan top-left rule
# ---------------------------------------------------------------------------
def edge(p0, p1, px, py):
    """E(p0->p1, p) = (x1-x0)(py-y0) - (y1-y0)(px-x0). Untuk segitiga A,B,C: E(A->B, C) = 2x luas bertanda."""
    return (p1[0] - p0[0]) * (py - p0[1]) - (p1[1] - p0[1]) * (px - p0[0])


def is_top_left(p0, p1):
    """Untuk segitiga yang luas bertandanya POSITIF di layar y-ke-bawah (searah jarum jam di layar):
    edge 'top' = horizontal ke kanan (dy == 0, dx > 0); edge 'left' = bergerak ke atas (dy < 0).
    Piksel yang pusatnya tepat di edge hanya diambil kalau edge-nya top atau left, supaya dua segitiga
    yang berbagi edge tidak sama-sama menggambar piksel itu (tanpa retak, tanpa double-draw)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    return (dy == 0 and dx > 0) or dy < 0


# ---------------------------------------------------------------------------
# Rasteriser
# ---------------------------------------------------------------------------
@dataclass
class RenderResult:
    color: np.ndarray                 # (H,W,3) uint8 sRGB
    depth: np.ndarray                 # (H,W) z NDC, +inf = kosong
    fragments: int = 0                # fragment yang lolos uji depth (termasuk overdraw)
    tris_drawn: int = 0
    tris_culled: int = 0
    tris_clipped: int = 0             # segitiga yang dipotong near plane
    uv: np.ndarray | None = field(default=None, repr=False)


def render(mesh, w, h, *, model, eye, target, fovy_deg, near, far, light_dir, ambient,
           up=(0.0, 1.0, 0.0), tex_u8=None, tri_colors=None, cull_back=False, depth_bits=None,
           perspective_correct=True, mip_levels=0, keep_uv=False, flat_from=None, shadow_res=0,
           shadow_bias_texels=1.5):
    """flat_from: indeks face mulai dari mana face TIDAK bertexture (abu-abu 0.7, mis. lantai).
    shadow_res: >0 = hard shadow lewat shadow map berukuran shadow_res x shadow_res (Lab 3)."""
    P = T.perspective_deg(fovy_deg, w / h, near, far)
    V = T.look_at(eye, target, up)
    pos_h = T.to_homogeneous(mesh.positions)
    world = (model @ pos_h.T).T[:, :3]
    clip = (P @ V @ model @ pos_h.T).T
    eye_v = np.asarray(eye, dtype=np.float64)
    L = np.asarray(light_dir, dtype=np.float64)
    L = L / np.linalg.norm(L)

    tex_lin = pyr = None
    if tex_u8 is not None:
        tex_lin = srgb_to_linear(tex_u8.astype(np.float64) / 255.0)
        if mip_levels:
            pyr = build_mipmap(tex_lin, mip_levels)
    tuv = mesh.triangle_uvs()
    smap = build_shadow_map(world, mesh.faces, L, shadow_res) if shadow_res else None

    color = np.zeros((h, w, 3))
    depth = np.full((h, w), np.inf)
    uvbuf = np.full((h, w, 2), np.nan) if keep_uv else None
    res = RenderResult(color=None, depth=depth)
    qmax = None if depth_bits is None else float(2 ** depth_bits - 1)

    for fi, vidx in enumerate(mesh.faces):
        # Lambert dengan normal datar di world space. Normal dihitung dari posisi yang SUDAH
        # ditransformasi M, jadi tetap benar walau M punya scale tidak seragam.
        wp = world[vidx]
        n = np.cross(wp[1] - wp[0], wp[2] - wp[0])
        nl = np.linalg.norm(n)
        if nl < 1e-12:
            continue
        n /= nl
        if n @ (eye_v - wp[0]) < 0:      # shading dua sisi: arahkan normal ke sisi yang terlihat kamera
            n = -n
        ndotl = max(0.0, float(n @ L))
        shade = ambient + (1.0 - ambient) * ndotl

        vc_tri = clip[vidx]
        if np.any(vc_tri[:, 2] + vc_tri[:, 3] < 0):
            res.tris_clipped += 1
        # atribut yang ikut di-clip dan diinterpolasi perspective-correct: u, v, posisi world (x, y, z)
        pieces = clip_near(vc_tri, np.c_[tuv[fi], wp])
        for vc, attr in pieces:
            wv = vc[:, 3]
            ndc = vc[:, :3] / wv[:, None]                           # perspective divide
            scr = T.viewport_points(ndc, w, h)                      # x, y piksel; z NDC
            A, B, C = scr[:, :2]
            area = edge(A, B, C[0], C[1])                            # 2x luas bertanda di layar
            if area == 0:
                continue
            # Front face (CCW di NDC, y ke atas) jadi luas NEGATIF di layar y-ke-bawah.
            if cull_back and area > 0:
                res.tris_culled += 1
                continue
            order = [0, 1, 2] if area > 0 else [0, 2, 1]             # normalkan supaya luas > 0
            scr, attr, wv = scr[order], attr[order], wv[order]
            uv = attr[:, :2]
            A, B, C = scr[:, :2]
            area = abs(area)

            x0 = max(0, int(np.floor(scr[:, 0].min())))
            x1 = min(w - 1, int(np.ceil(scr[:, 0].max())))
            y0 = max(0, int(np.floor(scr[:, 1].min())))
            y1 = min(h - 1, int(np.ceil(scr[:, 1].max())))
            if x0 > x1 or y0 > y1:
                continue
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px, py = xs + 0.5, ys + 0.5                               # pusat piksel

            e_bc, e_ca, e_ab = edge(B, C, px, py), edge(C, A, px, py), edge(A, B, px, py)
            inside = ((e_bc > 0) | ((e_bc == 0) & is_top_left(B, C))) & \
                     ((e_ca > 0) | ((e_ca == 0) & is_top_left(C, A))) & \
                     ((e_ab > 0) | ((e_ab == 0) & is_top_left(A, B)))
            if not inside.any():
                continue
            la, lb, lc = e_bc / area, e_ca / area, e_ab / area        # barycentric, jumlah = 1

            # Depth: z NDC linear di layar, jadi diinterpolasi barycentric langsung.
            z = la * scr[0, 2] + lb * scr[1, 2] + lc * scr[2, 2]
            if qmax is not None:                                      # depth buffer integer N-bit
                z = np.round((z * 0.5 + 0.5) * qmax) / qmax * 2.0 - 1.0
            region = depth[y0:y1 + 1, x0:x1 + 1]
            win = inside & (z < region)
            if not win.any():
                continue
            region[win] = z[win]
            res.tris_drawn += 1
            res.fragments += int(win.sum())

            if tex_lin is not None or keep_uv:
                iw = 1.0 / wv

                def uv_at(qx, qy):
                    a, b, c = edge(B, C, qx, qy) / area, edge(C, A, qx, qy) / area, edge(A, B, qx, qy) / area
                    if not perspective_correct:                      # naif: u linear di layar (SALAH)
                        return a * uv[0, 0] + b * uv[1, 0] + c * uv[2, 0], a * uv[0, 1] + b * uv[1, 1] + c * uv[2, 1]
                    one_w = a * iw[0] + b * iw[1] + c * iw[2]         # 1/w linear di layar
                    u_w = a * uv[0, 0] * iw[0] + b * uv[1, 0] * iw[1] + c * uv[2, 0] * iw[2]
                    v_w = a * uv[0, 1] * iw[0] + b * uv[1, 1] * iw[1] + c * uv[2, 1] * iw[2]
                    return u_w / one_w, v_w / one_w                  # pulihkan u = (u/w)/(1/w)

                u, v = uv_at(px, py)
                if keep_uv:
                    uvbuf[y0:y1 + 1, x0:x1 + 1][win] = np.stack([u, v], -1)[win]

            pix_shade = shade
            if smap is not None and ndotl > 0:
                # posisi world per piksel (perspective-correct: (P/w) / (1/w)), lalu uji shadow map
                iw3 = 1.0 / wv
                one_w = la * iw3[0] + lb * iw3[1] + lc * iw3[2]
                pw = [(la * attr[0, k] * iw3[0] + lb * attr[1, k] * iw3[1] + lc * attr[2, k] * iw3[2]) / one_w
                      for k in (2, 3, 4)]
                lit = shadow_lookup(smap, pw[0], pw[1], pw[2], shadow_bias_texels)
                pix_shade = ambient + (1.0 - ambient) * ndotl * lit

            flat = flat_from is not None and fi >= flat_from
            if tex_lin is None or flat:
                base = np.full(win.shape + (3,), 0.7)
                if tri_colors is not None:
                    base[:] = srgb_to_linear(np.asarray(tri_colors[fi], float) / 255.0)
            elif pyr is None:
                base = sample_bilinear(tex_lin, u, v)
            else:
                # level mip: berapa texel yang dilangkahi saat bergeser 1 piksel di layar
                ux, vx = uv_at(px + 1.0, py)
                uy, vy = uv_at(px, py + 1.0)
                Ht, Wt = tex_lin.shape[:2]
                rho = np.maximum(np.hypot((ux - u) * Wt, (vx - v) * Ht), np.hypot((uy - u) * Wt, (vy - v) * Ht))
                base = sample_trilinear(pyr, u, v, np.log2(np.maximum(rho, 1e-12)))

            lit_rgb = base * (pix_shade[..., None] if np.ndim(pix_shade) else pix_shade)
            color[y0:y1 + 1, x0:x1 + 1][win] = np.clip(lit_rgb, 0.0, 1.0)[win]

    # encode ke sRGB; kuantisasi dengan pemotongan (floor), konvensi yang sama dengan frame referensi
    res.color = np.clip(linear_to_srgb(color) * 255.0, 0, 255).astype(np.uint8)
    res.uv = uvbuf
    return res


@dataclass
class ShadowMap:
    LVP: np.ndarray       # matriks light view-projection (ortografik)
    depth: np.ndarray     # (res, res) z NDC terdekat dari light
    res: int
    texel_world: float    # lebar satu texel peta dalam world unit
    z_per_world: float    # skala world unit -> z NDC light


def build_shadow_map(world, faces, L, res):
    """Pass 1 shadow mapping: render DEPTH scene dari arah light directional.
    Light directional = proyeksi ortografik (sinar sejajar) yang menutupi bola pembatas scene."""
    center = world.mean(axis=0)
    r = float(np.linalg.norm(world - center, axis=1).max()) * 1.05
    up = (0.0, 1.0, 0.0) if abs(L[1]) < 0.99 else (0.0, 0.0, 1.0)
    Vl = T.look_at(center + L * 2.0 * r, center, up)
    Pl = T.orthographic(-r, r, -r, r, 0.01 * r, 4.0 * r)
    LVP = Pl @ Vl
    ndc = (LVP @ T.to_homogeneous(world).T).T[:, :3]              # ortografik: w = 1, tanpa pembagian
    scr = T.viewport_points(ndc, res, res)
    depth = np.full((res, res), np.inf)
    for vidx in faces:
        s = scr[vidx]
        A, B, C = s[:, :2]
        area = edge(A, B, C[0], C[1])
        if area == 0:
            continue
        if area < 0:                                                # dua sisi: semua face bisa menghalangi
            s = s[[0, 2, 1]]; A, B, C = s[:, :2]; area = -area
        x0, x1 = max(0, int(np.floor(s[:, 0].min()))), min(res - 1, int(np.ceil(s[:, 0].max())))
        y0, y1 = max(0, int(np.floor(s[:, 1].min()))), min(res - 1, int(np.ceil(s[:, 1].max())))
        if x0 > x1 or y0 > y1:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        px, py = xs + 0.5, ys + 0.5
        la, lb, lc = edge(B, C, px, py) / area, edge(C, A, px, py) / area, edge(A, B, px, py) / area
        inside = (la >= 0) & (lb >= 0) & (lc >= 0)
        z = la * s[0, 2] + lb * s[1, 2] + lc * s[2, 2]
        reg = depth[y0:y1 + 1, x0:x1 + 1]
        np.minimum(reg, np.where(inside, z, np.inf), out=reg)
    return ShadowMap(LVP, depth, res, 2.0 * r / res, 2.0 / (4.0 * r - 0.01 * r))


def shadow_lookup(sm, x, y, z, bias_texels):
    """Pass 2: titik world -> ruang light -> bandingkan depth-nya dengan isi peta (texel terdekat).
    Bias (dalam lebar texel) mencegah 'shadow acne' akibat diskretisasi peta. 1.0 = terang, 0.0 = bayangan."""
    p = np.stack([x, y, z, np.ones_like(x)], -1) @ sm.LVP.T
    sx = np.clip(((p[..., 0] + 1.0) * 0.5 * sm.res).astype(np.int64), 0, sm.res - 1)
    sy = np.clip(((1.0 - p[..., 1]) * 0.5 * sm.res).astype(np.int64), 0, sm.res - 1)
    bias = bias_texels * sm.texel_world * sm.z_per_world
    return (p[..., 2] - bias <= sm.depth[sy, sx]).astype(np.float64)


def add_ground(mesh, y, half):
    """Tambah lantai persegi (2 segitiga, CCW dilihat dari atas) di ketinggian y (ruang model).
    Mengembalikan (mesh baru, indeks face pertama lantai) untuk argumen flat_from."""
    from objio import Mesh
    n = len(mesh.positions)
    quad = np.array([[-half, y, -half], [-half, y, half], [half, y, half], [half, y, -half]])
    faces = np.vstack([mesh.faces, [[n, n + 1, n + 2], [n, n + 2, n + 3]]])
    uvs = np.vstack([mesh.uvs, np.zeros((1, 2))]) if len(mesh.uvs) else np.zeros((1, 2))
    fuv = None
    if mesh.face_uvs is not None:
        k = len(uvs) - 1
        fuv = np.vstack([mesh.face_uvs, [[k, k, k], [k, k, k]]])
    return Mesh(np.vstack([mesh.positions, quad]), uvs, faces, fuv), len(mesh.faces)


def depth_image(depth):
    """Citra depth 8-bit: (z_ndc+1)/2, latar (kosong) = putih."""
    d = np.where(np.isfinite(depth), (depth + 1.0) * 0.5, 1.0)
    return (np.clip(d, 0, 1) * 255).astype(np.uint8)


def load_scene(name, obj=None, tex=None):
    s = SCENES[name]
    mesh = load_obj(obj or s["obj"])
    tpath = tex or s["tex"]
    return mesh, (read_ppm(tpath) if tpath and os.path.exists(tpath) else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", choices=list(SCENES), default="temple")
    ap.add_argument("--model", help="ganti file OBJ scene")
    ap.add_argument("--tex", help="ganti texture scene")
    ap.add_argument("--w", type=int, default=512)
    ap.add_argument("--h", type=int, default=512)
    ap.add_argument("--out", help="path citra warna (default out/<scene>_raster.ppm)")
    ap.add_argument("--cull", action="store_true", help="back-face culling")
    ap.add_argument("--mip", type=int, default=0, help="jumlah level mipmap (0 = tanpa)")
    args = ap.parse_args()

    mesh, tex = load_scene(args.scene, args.model, args.tex)
    out = args.out or f"out/{args.scene}_raster.ppm"
    t0 = time.perf_counter()
    r = render(mesh, args.w, args.h, tex_u8=tex, cull_back=args.cull, mip_levels=args.mip,
               **scene_kwargs(args.scene))
    dt = time.perf_counter() - t0
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    write_ppm(out, r.color)
    dpath = out.replace("_raster", "_depth") if "_raster" in out else out.replace(".ppm", "_depth.ppm")
    write_ppm(dpath, depth_image(r.depth))
    fin = np.isfinite(r.depth)
    print(f"scene={args.scene} model={args.model or SCENES[args.scene]['obj']} segitiga={mesh.n_tris} "
          f"frame={args.w}x{args.h} cull={args.cull} mip={args.mip}")
    print(f"segitiga digambar={r.tris_drawn} di-cull={r.tris_culled} dipotong-near={r.tris_clipped} "
          f"fragment={r.fragments} piksel-terisi={int(fin.sum())}")
    if fin.any():
        print(f"rentang depth NDC [{r.depth[fin].min():.3f}, {r.depth[fin].max():.3f}]")
    print(f"waktu render {dt:.3f} s")
    print(f"tulis {out} dan {dpath}")


if __name__ == "__main__":
    main()
