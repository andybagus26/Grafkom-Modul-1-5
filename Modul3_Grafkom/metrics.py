"""
metrics.py
PSNR dan SSIM global (satu jendela = seluruh citra), sesuai definisi yang dikutip modul.
Catatan: SSIM "asli" (Wang dkk. 2004) memakai jendela Gaussian 11x11 yang digeser. Versi global ini
cukup untuk memeringkat "seberapa beda" dua frame, tetapi lebih longgar terhadap selisih lokal.
"""

import numpy as np


def psnr(a, b, peak=255.0):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"ukuran beda: {a.shape} vs {b.shape}")
    mse = np.mean((a - b) ** 2)
    return float("inf") if mse == 0 else float(10.0 * np.log10(peak * peak / mse))


def ssim_global(a, b, peak=255.0):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"ukuran beda: {a.shape} vs {b.shape}")
    c1, c2 = (0.01 * peak) ** 2, (0.03 * peak) ** 2
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(), b.var()
    cov = np.mean((a - ma) * (b - mb))
    return float((2 * ma * mb + c1) * (2 * cov + c2) / ((ma * ma + mb * mb + c1) * (va + vb + c2)))


def fmt_psnr(p):
    return "inf" if np.isinf(p) else f"{p:.1f}"
