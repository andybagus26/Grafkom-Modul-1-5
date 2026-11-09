"""Module 1 -- histogram from raw arrays, from scratch (NumPy only).

Job: count how many pixels fall in each intensity bin, WITHOUT calling a
histogram function, then prove it matches numpy.histogram exactly.

Reproduces: Fully Worked Example Step 2 -- "sum of bins = W*H",
            "max err vs numpy.histogram = 0".

Run:
  python histogram.py --image data/relief.ppm --channel luma --bins 16
  python histogram.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from ppm_io import read_ppm


def to_luma_codes(img: np.ndarray) -> np.ndarray:
    """Quick Rec.601 luma on codes -- only for BINNING/visualisation, not a
    colour-correct conversion (see luma.py for that)."""
    if img.ndim == 2:
        return img
    w = np.array([0.299, 0.587, 0.114])
    return np.round(img.astype(np.float64) @ w).clip(0, 255).astype(np.uint8)


def histogram_from_scratch(values_u8: np.ndarray, bins: int) -> np.ndarray:
    """Count uint8 values (0..255) into `bins` equal-width bins. Pure loops
    over the 256 possible codes -- no np.histogram, no np.bincount."""
    if 256 % bins != 0:
        raise ValueError("use a bin count that divides 256 (2,4,8,16,32,...)")
    width = 256 // bins
    flat = values_u8.reshape(-1)
    counts = np.zeros(bins, dtype=np.int64)
    # tally each of the 256 codes, then fold into bins
    per_code = np.zeros(256, dtype=np.int64)
    for code in flat:                       # explicit: this is the "from scratch" part
        per_code[code] += 1
    for code in range(256):
        counts[code // width] += per_code[code]
    return counts


def _print_hist(counts: np.ndarray) -> None:
    bins = len(counts)
    width = 256 // bins
    scale = max(1, counts.max() // 40)
    for b, c in enumerate(counts):
        lo, hi = b * width, b * width + width - 1
        print(f"bin {b:2d} [{lo:3d}-{hi:3d}]: {c:8d}  {'#' * int(c // scale)}")
    print(f"sum of bins = {counts.sum()}")


def _selftest() -> None:
    rng_free = (np.arange(64, dtype=np.uint8).reshape(8, 8) * 4)   # 0,4,...,252
    for bins in (2, 4, 8, 16, 32):
        mine = histogram_from_scratch(rng_free, bins)
        ref, _ = np.histogram(rng_free, bins=bins, range=(0, 256))
        err = int(np.max(np.abs(mine - ref)))
        assert err == 0, f"mismatch at bins={bins}: {mine} vs {ref}"
        assert mine.sum() == rng_free.size
    print("histogram self-test OK  (max err vs numpy.histogram = 0 for bins 2..32)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--channel", default="luma", choices=["luma", "r", "g", "b", "gray"])
    ap.add_argument("--bins", type=int, default=16)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest or not args.image:
        _selftest()
        return

    img = read_ppm(args.image)
    if args.channel in ("luma", "gray") or img.ndim == 2:
        vals = to_luma_codes(img)
    else:
        vals = img[..., "rgb".index(args.channel)]

    mine = histogram_from_scratch(vals, args.bins)
    ref, _ = np.histogram(vals, bins=args.bins, range=(0, 256))
    _print_hist(mine)
    print(f"W*H = {vals.size}   max err vs numpy.histogram = "
          f"{int(np.max(np.abs(mine - ref)))}")


if __name__ == "__main__":
    main()
