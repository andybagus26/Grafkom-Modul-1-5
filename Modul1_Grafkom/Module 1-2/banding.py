"""Module 1 -- Lab 2.3: quantisation, banding, and dithering (NumPy only).

Job:
  1. Build a 512-px black->white ramp from a CONTINUOUS value v in [0,1]
     (not from already-rounded 8-bit codes -- that would quantise twice).
  2. Quantise it to 8 bits and to 5 bits:  code = round(v * (L-1)).
  3. MEASURE the band widths in pixels (run-lengths of equal codes) and check
     them against Example E2:  8-bit -> 2 px, 5-bit -> 16 px.
  4. Dither the 5-bit version with a deterministic 8x8 Bayer (ordered) matrix
     -- no RNG, so the result reproduces byte-for-byte -- and show what changes:
     the histogram is identical in shape (still only 32 levels), but the
     longest flat run collapses and the local mean tracks the true ramp.

Run:
  python banding.py                 # prints the measurements
  python banding.py --out report/   # also writes the ramps as PGM
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from ppm_io import write_ppm

W = 512


def ramp(w: int = W) -> np.ndarray:
    """Continuous intensities, one sample per pixel centre: v = (c+0.5)/w."""
    return (np.arange(w, dtype=np.float64) + 0.5) / w


def quantise(v: np.ndarray, bits: int) -> np.ndarray:
    """code = round(v*(L-1)) -- the formula from section 'Pixel Grid, Bit Depth'."""
    L = 2 ** bits
    return np.round(np.clip(v, 0, 1) * (L - 1)).astype(np.int64)


def bayer(n: int = 8) -> np.ndarray:
    """Recursive Bayer index matrix, normalised to thresholds in (-0.5, 0.5)."""
    m = np.array([[0, 2], [3, 1]], dtype=np.int64)
    while m.shape[0] < n:
        k = m.shape[0]
        m = np.block([[4 * m + 0, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
        assert m.shape[0] == 2 * k
    return (m + 0.5) / (n * n) - 0.5


def quantise_dithered(v2d: np.ndarray, bits: int) -> np.ndarray:
    """Ordered dither: add a sub-step threshold BEFORE rounding."""
    L = 2 ** bits
    h, w = v2d.shape
    t = bayer(8)
    tile = np.tile(t, (h // 8 + 1, w // 8 + 1))[:h, :w]
    return np.clip(np.round(v2d * (L - 1) + tile), 0, L - 1).astype(np.int64)


def run_lengths(row: np.ndarray) -> np.ndarray:
    """Lengths of maximal runs of equal values along a 1-D array."""
    change = np.flatnonzero(np.diff(row) != 0) + 1
    edges = np.concatenate([[0], change, [row.size]])
    return np.diff(edges)


def to_u8(code: np.ndarray, bits: int) -> np.ndarray:
    L = 2 ** bits
    return np.round(code / (L - 1) * 255).astype(np.uint8)


def measure(h: int = 64) -> dict:
    v = ramp()
    res = {}
    for bits in (8, 5):
        c = quantise(v, bits)
        rl = run_lengths(c)
        res[bits] = dict(levels=int(np.unique(c).size), q=1 / (2 ** bits - 1),
                         median_band=float(np.median(rl)), mean_band=float(rl.mean()), min_band=int(rl.min()),
                         max_band=int(rl.max()), predicted=W / 2 ** bits)
    # dithered 5-bit, 2-D (dither needs the second dimension)
    v2 = np.repeat(v[None, :], h, axis=0)
    plain = np.repeat(quantise(v, 5)[None, :], h, axis=0)
    dith = quantise_dithered(v2, 5)
    L = 31
    true_codes = v2 * L
    # local mean over an 8x8 window = what the eye integrates
    def block_mean(a):
        return a.reshape(h // 8, 8, W // 8, 8).mean(axis=(1, 3))
    err_plain = np.abs(block_mean(plain) - block_mean(true_codes)).mean()
    err_dith = np.abs(block_mean(dith) - block_mean(true_codes)).mean()
    res["dither"] = dict(
        levels=int(np.unique(dith).size),
        longest_run_plain=int(run_lengths(plain[0]).max()),
        longest_run_dith=int(max(run_lengths(r).max() for r in dith)),
        local_mean_err_plain=float(err_plain),
        local_mean_err_dith=float(err_dith),
        hist_plain=np.bincount(plain.ravel(), minlength=32),
        hist_dith=np.bincount(dith.ravel(), minlength=32),
    )
    res["images"] = dict(g8=np.repeat(to_u8(quantise(v, 8), 8)[None, :], h, 0),
                         g5=to_u8(plain, 5), g5d=to_u8(dith, 5))
    return res


def _selftest() -> None:
    r = measure()
    assert r[8]["levels"] == 256 and r[8]["mean_band"] == 2.0, r[8]
    assert r[5]["levels"] == 32 and r[5]["mean_band"] == 16.0, r[5]
    d = r["dither"]
    assert d["longest_run_dith"] < d["longest_run_plain"]
    assert d["local_mean_err_dith"] < d["local_mean_err_plain"]
    print(f"banding self-test OK  (8-bit 256 levels / 2 px bands; 5-bit 32 levels / "
          f"16 px bands; dither longest run {d['longest_run_plain']} -> "
          f"{d['longest_run_dith']} px, local-mean error "
          f"{d['local_mean_err_plain']:.3f} -> {d['local_mean_err_dith']:.3f} codes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    r = measure()
    for bits in (8, 5):
        m = r[bits]
        print(f"{bits}-bit: L={2**bits:3d} levels, q=1/{2**bits-1} = {m['q']:.4f}; "
              f"distinct greys={m['levels']}; band width mean={m['mean_band']:.1f} px, "
              f"median={m['median_band']:.1f} px "
              f"(min {m['min_band']}, max {m['max_band']}); predicted {W}/{2**bits} = "
              f"{m['predicted']:.0f} px")
    d = r["dither"]
    print(f"5-bit + 8x8 Bayer dither: distinct levels={d['levels']}, longest flat run "
          f"{d['longest_run_plain']} px -> {d['longest_run_dith']} px, "
          f"8x8 local-mean error vs true ramp {d['local_mean_err_plain']:.3f} -> "
          f"{d['local_mean_err_dith']:.3f} codes")
    print("histogram (5-bit plain)   :", d["hist_plain"].tolist())
    print("histogram (5-bit dithered):", d["hist_dith"].tolist())
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for k, im in r["images"].items():
            p = os.path.join(args.out, f"banding_{k}.pgm")
            write_ppm(p, im)
            print(f"wrote {p}")


if __name__ == "__main__":
    main()
