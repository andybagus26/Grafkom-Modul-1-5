"""
colorspace.py
Fungsi transfer sRGB <-> linear light (IEC 61966-2-1).
Semua operasi yang merata-rata, mem-filter, atau memberi pencahayaan pada warna dikerjakan di
linear light, lalu di-encode lagi ke sRGB (Modul 1).
"""

import numpy as np


def srgb_to_linear(c):
    """c: float di [0, 1] (kode sRGB / 255) -> intensitas cahaya linear di [0, 1]."""
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    """x: cahaya linear di [0, 1] -> kode sRGB float di [0, 1]."""
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1.0 / 2.4) - 0.055)
