"""
broken_scene.py
Lab 2 langkah 2: diagnosis-dan-perbaiki tiga scene rusak. Tiap bug diperbaiki dengan SATU perubahan.

    python3 broken_scene.py --bug inside-out   # winding terbalik + back-face culling
    python3 broken_scene.py --bug zfight       # near = 1e-3 pada depth buffer 16-bit
    python3 broken_scene.py --bug stretched    # urutan perkalian matriks model tertukar
    python3 broken_scene.py --all

Untuk tiap bug skrip ini mencetak BUKTI (angka depth, matriks, jumlah fragment), menulis render rusak,
render diperbaiki, dan citra depth keduanya ke out/, lalu membuktikan perbaikan dengan SSIM/PSNR
terhadap referensi (sebelum vs sesudah). Untuk z-fighting juga ditulis histogram depth.
Diagnosis tertulis ada di laporan Lab 2 (dikumpulkan terpisah).
"""

import argparse
import os

import numpy as np

import raster3d as R
import transforms as T
from metrics import fmt_psnr, psnr, ssim_global
from objio import Mesh
from ppm_io import read_ppm, write_ppm
from validate_obj import check_winding

W = H = 512


def save(name, bad, fixed):
    os.makedirs("out", exist_ok=True)
    write_ppm(f"out/bug_{name}_bad.ppm", bad.color)
    write_ppm(f"out/bug_{name}_fixed.ppm", fixed.color)
    write_ppm(f"out/bug_{name}_bad_depth.ppm", R.depth_image(bad.depth))
    write_ppm(f"out/bug_{name}_fixed_depth.ppm", R.depth_image(fixed.depth))


def report(name, bad, fixed, ref):
    sb, sf = ssim_global(bad.color, ref), ssim_global(fixed.color, ref)
    pb, pf = psnr(bad.color, ref), psnr(fixed.color, ref)
    print(f"  SSIM ke referensi: sebelum {sb:.3f} -> sesudah {sf:.3f}   "
          f"PSNR: sebelum {fmt_psnr(pb)} dB -> sesudah {fmt_psnr(pf)} dB")
    print(f"  tulis out/bug_{name}_{{bad,fixed}}.ppm dan out/bug_{name}_{{bad,fixed}}_depth.ppm")
    return sb, sf


# ---------------------------------------------------------------------------
# Bug 1: inside-out
# ---------------------------------------------------------------------------
def bug_inside_out():
    print("\n== BUG: inside-out ==")
    # Scene rusak: data/pusaka_model.obj APA ADANYA, dirender dengan back-face culling ON.
    # Temuan: OBJ candi dari make_model.py starter ternyata ber-winding CW dilihat dari luar
    # (contoh: face atas (4,5,6) normalnya -y), walau komentarnya bilang "CCW-front". Selama render
    # tanpa culling + shading dua sisi, bug ini tersembunyi. Begitu culling dinyalakan, ia muncul.
    mesh, tex = R.load_scene("temple")
    kw = R.scene_kwargs("temple")
    broken = mesh

    bad = R.render(broken, W, H, tex_u8=tex, cull_back=True, **kw)
    # PERBAIKAN (satu perubahan): susun ulang winding semua face menjadi CCW-dari-luar
    fixed = R.render(broken.flipped_winding(), W, H, tex_u8=tex, cull_back=True, **kw)
    ref = read_ppm("ref/temple_ref_512.ppm")

    both = np.isfinite(bad.depth) & np.isfinite(fixed.depth)
    print("  bukti:")
    print(f"    segitiga di-cull: rusak {bad.tris_culled} / {broken.n_tris}  vs  diperbaiki {fixed.tris_culled} / {broken.n_tris}")
    print(f"    fragment: rusak {bad.fragments}  vs  diperbaiki {fixed.fragments}")
    print(f"    depth NDC rata-rata di piksel yang sama: rusak {bad.depth[both].mean():.4f}  vs  "
          f"diperbaiki {fixed.depth[both].mean():.4f}  (lebih besar = lebih JAUH)")
    for label, m in (("rusak", broken), ("diperbaiki", broken.flipped_winding())):
        dup, _, vol = check_winding(m.positions.tolist(), m.faces.tolist())
        print(f"    signed volume mesh {label}: {vol:+.4f}  (negatif = normal CCW menunjuk ke dalam)")
    save("inside-out", bad, fixed)
    return report("inside-out", bad, fixed, ref)


# ---------------------------------------------------------------------------
# Bug 2: z-fighting
# ---------------------------------------------------------------------------
def zfight_scene():
    """Dua quad besar yang hampir coplanar dan saling MENYILANG, jauh dari kamera (jarak ~15):
    A datar di z=-10; B = A diputar 1 derajat terhadap sumbu x di tengahnya (y=1), jadi bagian atas B
    sedikit di depan A dan bagian bawahnya sedikit di belakang. Garis potongnya horizontal di y=1.
    Kebenaran: di atas garis B (biru) menang, di bawah garis A (oranye) menang."""
    A = np.array([[-3.0, -1.0, 0.0], [3.0, -1.0, 0.0], [3.0, 3.0, 0.0], [-3.0, 3.0, 0.0]])
    a = np.radians(1.0)
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    B = (A - [0, 1.0, 0]) @ Rx.T + [0, 1.0, 0]
    pos = np.vstack([A, B]) + [0, 0, -10.0]
    faces = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
    return Mesh(pos, np.zeros((0, 2)), faces, None)


ZF_COLORS = [(230, 130, 40), (230, 130, 40), (60, 120, 210), (60, 120, 210)]
ZF_CAM = dict(model=np.eye(4), eye=(0.0, 1.0, 5.0), target=(0.0, 1.0, -1.0), fovy_deg=45.0, far=100.0,
              light_dir=(0.0, 0.2, 1.0), ambient=0.15)


def depth_code_histogram(mesh, near, bits=16):
    """Untuk tiap piksel tempat kedua quad menutupi: selisih kode depth 16-bit (B - A).
    Selisih 0 = kedua quad jatuh ke kode yang sama -> uji z tidak bisa memutuskan -> z-fight."""
    da = R.render(Mesh(mesh.positions, mesh.uvs, mesh.faces[:2], None), W, H, near=near, depth_bits=bits, **ZF_CAM).depth
    db = R.render(Mesh(mesh.positions, mesh.uvs, mesh.faces[2:], None), W, H, near=near, depth_bits=bits, **ZF_CAM).depth
    both = np.isfinite(da) & np.isfinite(db)
    q = 2 ** bits - 1
    ca = np.round((da[both] * 0.5 + 0.5) * q).astype(np.int64)
    cb = np.round((db[both] * 0.5 + 0.5) * q).astype(np.int64)
    return cb - ca


def bug_zfight():
    print("\n== BUG: zfight ==")
    m = zfight_scene()
    bad = R.render(m, W, H, near=1e-3, depth_bits=16, tri_colors=ZF_COLORS, **ZF_CAM)
    # PERBAIKAN (satu perubahan): near 1e-3 -> 1.0
    fixed = R.render(m, W, H, near=1.0, depth_bits=16, tri_colors=ZF_COLORS, **ZF_CAM)
    truth = R.render(m, W, H, near=1.0, depth_bits=None, tri_colors=ZF_COLORS, **ZF_CAM)   # depth float64

    def fighting(r):
        return int((np.abs(r.color.astype(int) - truth.color.astype(int)).max(axis=2) > 60).sum())

    print("  bukti:")
    print(f"    piksel salah warna vs depth float: near=1e-3 -> {fighting(bad)};  near=1.0 -> {fighting(fixed)}")
    lines = ["# Histogram selisih kode depth 16-bit (B - A) di piksel tempat kedua quad bertumpuk",
             "# selisih 0 berarti kedua quad mendapat kode depth yang sama -> z-fight"]
    hists = {}
    for near in (1e-3, 1.0):
        d = depth_code_histogram(m, near)
        vals, counts = np.unique(np.clip(d, -6, 6), return_counts=True)
        hists[near] = (vals, counts, d)
        zero = int((d == 0).sum())
        print(f"    near={near:g}: {zero}/{len(d)} piksel ({100 * zero / len(d):.1f}%) kode depth A == B; "
              f"rentang selisih kode [{d.min()}, {d.max()}]")
        lines.append(f"\nnear = {near:g}  (n piksel = {len(d)}; nilai di luar [-6,6] dijepit ke ujung)")
        for v, c in zip(vals, counts):
            lines.append(f"  {v:+3d} {'<=' if v == -6 else '>=' if v == 6 else '  '} {c:7d}  {'#' * int(60 * c / counts.max())}")
    # Presisi teoretis: lebar satu kode 16-bit dalam world unit di jarak 15
    for near in (1e-3, 1.0):
        f, z = ZF_CAM["far"], 15.0
        step = (1.0 / (2 ** 16 - 1)) * (f - near) * z * z / (f * near)
        print(f"    lebar 1 kode depth 16-bit di jarak {z:g}: near={near:g} -> {step:.4f} world unit")
        lines.append(f"# lebar 1 kode 16-bit di jarak 15, near={near:g}: {step:.4f} unit")
    os.makedirs("logs", exist_ok=True)
    with open("logs/lab2_zfight_histogram.txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
    write_hist_png(hists, "out/bug_zfight_histogram.png")
    print("  tulis logs/lab2_zfight_histogram.txt dan out/bug_zfight_histogram.png")
    save("zfight", bad, fixed)
    return report("zfight", bad, fixed, truth.color)


def write_hist_png(hists, path):
    """Diagram batang sederhana (digambar dengan NumPy, disimpan lewat Pillow kalau ada)."""
    panel_w, panel_h, pad = 390, 240, 30
    img = np.full((panel_h + 2 * pad, 2 * panel_w + 3 * pad, 3), 255, np.uint8)
    for k, (near, (vals, counts, _)) in enumerate(sorted(hists.items())):
        ox = pad + k * (panel_w + pad)
        img[pad + panel_h, ox:ox + panel_w] = 0
        bw = panel_w // 13
        for v, c in zip(vals, counts):
            x = ox + (int(v) + 6) * bw
            hgt = int(panel_h * c / counts.max())
            col = (200, 40, 40) if v == 0 else (60, 120, 210)
            img[pad + panel_h - hgt:pad + panel_h, x + 2:x + bw - 2] = col
    try:
        from PIL import Image, ImageDraw
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        for k, near in enumerate(sorted(hists)):
            ox = pad + k * (panel_w + pad)
            dr.text((ox, 8), f"near = {near:g}: selisih kode depth 16-bit (B - A), merah = 0 (z-fight)", fill=(0, 0, 0))
            for v in (-6, -3, 0, 3, 6):
                dr.text((ox + (v + 6) * (panel_w // 13) + 8, pad + panel_h + 6), f"{v:+d}", fill=(0, 0, 0))
        im.save(path)
    except ImportError:
        write_ppm(path.replace(".png", ".ppm"), img)


# ---------------------------------------------------------------------------
# Bug 3: stretched
# ---------------------------------------------------------------------------
S_LOCAL = T.scale(1.5, 1.0, 1.0)   # candi sengaja dibuat 1.5x lebih panjang di sumbu x LOKAL-nya


def bug_stretched():
    print("\n== BUG: stretched ==")
    mesh, tex = R.load_scene("temple")
    kw = R.scene_kwargs("temple")
    good_M = T.rot_y_deg(35) @ S_LOCAL      # benar: scale dulu (di frame lokal), lalu putar
    bad_M = S_LOCAL @ T.rot_y_deg(35)       # rusak: urutan tertukar -> scale di frame WORLD setelah diputar
    kw.pop("model")
    bad = R.render(mesh, W, H, tex_u8=tex, model=bad_M, **kw)
    # PERBAIKAN (satu perubahan): tukar kembali urutan perkalian -> R @ S
    fixed = R.render(mesh, W, H, tex_u8=tex, model=good_M, **kw)

    def describe(label, M):
        c = M[:3, :3]
        print(f"    M {label} (3x3):\n" + "\n".join("      " + np.array2string(r, precision=3, suppress_small=True) for r in c))
        print(f"      panjang kolom (x,y,z lokal) = {np.linalg.norm(c, axis=0).round(3)}   "
              f"kolom0.kolom2 = {c[:, 0] @ c[:, 2]:+.3f}   "
              f"sudut antara sumbu x dan z lokal = {np.degrees(np.arccos(c[:, 0] @ c[:, 2] / (np.linalg.norm(c[:, 0]) * np.linalg.norm(c[:, 2])))):.1f} deg")
    print("  bukti (matriks dicetak):")
    describe("rusak  = S @ R", bad_M)
    describe("benar  = R @ S", good_M)
    save("stretched", bad, fixed)
    return report("stretched", bad, fixed, fixed.color)


BUGS = {"inside-out": bug_inside_out, "zfight": bug_zfight, "stretched": bug_stretched}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bug", choices=list(BUGS))
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    for name in (BUGS if args.all or not args.bug else [args.bug]):
        BUGS[name]()


if __name__ == "__main__":
    main()
