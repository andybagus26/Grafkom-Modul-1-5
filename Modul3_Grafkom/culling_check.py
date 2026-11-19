"""
culling_check.py
Lab 2 langkah 5 (perbaikan yang didorong pitfall): back-face culling.
Ukur jumlah segitiga yang di-raster, jumlah fragment, dan waktu, tanpa vs dengan culling. Pada mesh
TERTUTUP dengan winding konsisten, citranya harus identik (PSNR inf): yang dibuang hanya segitiga
yang memang tertutup oleh sisi depan.

Candi dari starter di-rewind dulu (lihat bug inside-out): culling hanya benar kalau winding benar.

    python3 culling_check.py
"""

import time

import numpy as np

import raster3d as R
from metrics import fmt_psnr, psnr

W = H = 512


def run(label, mesh, tex, kw, repeats=3):
    out = {}
    for cull in (False, True):
        best = np.inf
        for _ in range(repeats):
            t0 = time.perf_counter()
            r = R.render(mesh, W, H, tex_u8=tex, cull_back=cull, **kw)
            best = min(best, time.perf_counter() - t0)
        out[cull] = (r, best)
    (a, ta), (b, tb) = out[False], out[True]
    print(f"\n{label} ({mesh.n_tris} segitiga, {W}x{H}, waktu = terbaik dari {repeats} run)")
    print(f"  {'':14} {'di-raster':>10} {'di-cull':>8} {'fragment':>10} {'waktu (s)':>10}")
    print(f"  {'tanpa culling':14} {mesh.n_tris - a.tris_culled:10d} {a.tris_culled:8d} {a.fragments:10d} {ta:10.3f}")
    print(f"  {'dengan culling':14} {mesh.n_tris - b.tris_culled:10d} {b.tris_culled:8d} {b.fragments:10d} {tb:10.3f}")
    print(f"  fragment turun {a.fragments - b.fragments} ({100 * (a.fragments - b.fragments) / a.fragments:.1f}%), "
          f"waktu turun {100 * (ta - tb) / ta:.1f}%, citra identik? PSNR {fmt_psnr(psnr(a.color, b.color))} dB")


def main():
    mesh, tex = R.load_scene("mymodel")
    run("mymodel.obj (pilar, model sendiri)", mesh, tex, R.scene_kwargs("mymodel"))
    mesh, tex = R.load_scene("temple")
    run("data/pusaka_model.obj (candi, setelah rewind)", mesh.flipped_winding(), tex, R.scene_kwargs("temple"))


if __name__ == "__main__":
    main()
