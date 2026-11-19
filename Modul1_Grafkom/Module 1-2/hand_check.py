"""Module 1 -- Analysis A2: reproduce ONE output unit of resample.py by hand.

Takes the 2x2 block of data/relief.ppm at rows 14-15, cols 130-131 (the block
where naive and linear downscales disagree the most -- output pixel (7, 65))
and recomputes its gamma-correct downscale value step by step with plain
Python floats and the scalar sRGB formulas (an independent code path from the
vectorised srgb.py), then checks it against resample.box_downscale_2x to the
code level.

Run:  python hand_check.py
"""
from __future__ import annotations

import numpy as np

from ppm_io import read_ppm
from resample import box_downscale_2x

R0, C0 = 14, 130


def lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def enc(l: float) -> float:
    return 12.92 * l if l <= 0.0031308 else 1.055 * l ** (1 / 2.4) - 0.055


def by_hand(verbose: bool = True):
    img = read_ppm("data/relief.ppm")
    blk = img[R0:R0 + 2, C0:C0 + 2]
    out_lin, out_naive = [], []
    for ch, name in enumerate("RGB"):
        codes = [int(v) for v in blk[..., ch].ravel()]
        cs = [v / 255 for v in codes]
        ls = [lin(c) for c in cs]
        mean_l = sum(ls) / 4
        e = enc(mean_l)
        # NumPy's np.round (used by to_u8) rounds HALF TO EVEN; so does Python's
        # round(). floor(x+0.5) would give 145 for 144.5 and miss by one code.
        code = round(e * 255)
        naive = round(sum(codes) / 4)
        out_lin.append(code)
        out_naive.append(naive)
        if verbose:
            print(f"{name}: codes {codes}")
            print(f"   /255      -> {[round(c, 5) for c in cs]}")
            print(f"   decode    -> {[round(l, 5) for l in ls]}")
            print(f"   mean lin  -> {mean_l:.5f}")
            print(f"   encode    -> {e:.5f}  x255 = {e * 255:.2f}  -> code {code}")
            print(f"   naive     -> ({' + '.join(map(str, codes))})/4 = {sum(codes) / 4:.2f}"
                  f" -> code {naive} (half-to-even)")
    return out_lin, out_naive


def _selftest() -> None:
    hand, naive = by_hand(verbose=False)
    img = read_ppm("data/relief.ppm")
    tool = box_downscale_2x(img, True)[R0 // 2, C0 // 2].tolist()
    tool_n = box_downscale_2x(img, False)[R0 // 2, C0 // 2].tolist()
    assert hand == tool, f"hand {hand} != resample.py {tool}"
    assert naive == tool_n, f"hand naive {naive} != resample.py naive {tool_n}"
    print(f"hand-check OK  (block rows {R0}-{R0+1}, cols {C0}-{C0+1}: hand linear {hand} "
          f"== resample.py {tool}; hand naive {naive} == {tool_n})")


if __name__ == "__main__":
    h, n = by_hand()
    img = read_ppm("data/relief.ppm")
    print(f"\nby hand  : linear {h}   naive {n}")
    print(f"resample : linear {box_downscale_2x(img, True)[R0 // 2, C0 // 2].tolist()}   "
          f"naive {box_downscale_2x(img, False)[R0 // 2, C0 // 2].tolist()}")
