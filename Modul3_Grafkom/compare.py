"""
compare.py
Bandingkan dua frame PPM: PSNR, SSIM global, rata-rata dan maksimum |selisih|, jumlah piksel beda,
dan (opsional) citra selisih yang diperkuat. Juga melaporkan di mana selisihnya berada:
di TEPI siluet (wajar: anti-aliasing / tie-breaking) atau di BAGIAN DALAM (tanda bug transform).

    python3 compare.py A.ppm B.ppm [--diff out/diff.ppm --scale 6]
"""

import argparse
import sys

import numpy as np

from metrics import fmt_psnr, psnr, ssim_global
from ppm_io import read_ppm, write_ppm


def silhouette_mask(img, bg_tol=0):
    """Piksel tepi = piksel yang punya tetangga 4-arah dengan status latar/objek berbeda.
    Latar = hitam pekat (kedua renderer from-scratch memakai latar 0)."""
    obj = img.max(axis=2) > bg_tol
    edge = np.zeros_like(obj)
    edge[1:, :] |= obj[1:, :] != obj[:-1, :]
    edge[:-1, :] |= obj[1:, :] != obj[:-1, :]
    edge[:, 1:] |= obj[:, 1:] != obj[:, :-1]
    edge[:, :-1] |= obj[:, 1:] != obj[:, :-1]
    return edge


def compare(a_path, b_path, diff_path=None, scale=6.0):
    A, B = read_ppm(a_path), read_ppm(b_path)
    if A.shape != B.shape:
        print(f"ukuran beda: {A.shape} vs {B.shape} -- render keduanya dengan w/h sama (setPixelRatio(1))")
        sys.exit(2)
    d = np.abs(A.astype(np.int32) - B.astype(np.int32))
    p, s = psnr(A, B), ssim_global(A, B)
    differ = d.max(axis=2) > 0
    edge = silhouette_mask(A) | silhouette_mask(B)
    print(f"ukuran {A.shape[1]}x{A.shape[0]}  PSNR {fmt_psnr(p)} dB  SSIM {s:.4f}  "
          f"mean|diff| {d.mean():.3f}  max|diff| {int(d.max())}")
    print(f"piksel beda {int(differ.sum())} (di tepi siluet {int((differ & edge).sum())}, "
          f"di bagian dalam {int((differ & ~edge).sum())})")
    if diff_path:
        write_ppm(diff_path, np.clip(d * scale, 0, 255).astype(np.uint8))
        print(f"tulis {diff_path} (|A-B| x{scale:g})")
    return p, s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--diff")
    ap.add_argument("--scale", type=float, default=6.0)
    args = ap.parse_args()
    compare(args.a, args.b, args.diff, args.scale)
