"""Module 1 -- the "washed-out downscale" DIAGNOSE-AND-FIX artifact.

The repo ships data/thumb_buggy.ppm : relief.ppm downscaled 2x by averaging
2x2 blocks DIRECTLY ON sRGB CODES (make_data.box_downscale_2x_naive). It looks
washed-out / muddy / dark.

Your Lab 2 task:
  1. WITHOUT reading the fix, show from the pixel values that thumb_buggy is
     systematically darker than a correct downscale, and by how much.
  2. State the root cause.
  3. Apply the one-line fix (decode to linear before averaging).
  4. PROVE it: difference image + PSNR before/after.

This script does the measurement for you once you have written your diagnosis.

Run:
  python gamma_resize_bug.py --diagnose          # evidence only, no fix
  python gamma_resize_bug.py --fix --out report/ # writes correct + diff + metrics
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from ppm_io import read_ppm, write_ppm
from resample import box_downscale_2x
from metrics import psnr, ssim


def load_inputs():
    orig = read_ppm("data/relief.ppm")
    buggy = read_ppm("data/thumb_buggy.ppm")
    return orig, buggy


def luma_hist(img: np.ndarray, bins: int = 16) -> np.ndarray:
    """Histogram of (Rec.601-on-codes) luma, from scratch -- for the
    'histogram shift' plot of the diagnosis."""
    from histogram import histogram_from_scratch, to_luma_codes
    return histogram_from_scratch(to_luma_codes(img), bins)


def diagnose(orig, buggy) -> None:
    correct = box_downscale_2x(orig, gamma_correct=True)
    d = correct.astype(int) - buggy.astype(int)          # + means buggy too dark
    print("== evidence (no fix applied) ==")
    print(f"buggy mean code    : {buggy.mean():.2f}")
    print(f"correct mean code  : {correct.mean():.2f}")
    print(f"correct - buggy    : mean {d.mean():+.2f},  "
          f"min {d.min():+d},  max {d.max():+d}")
    frac_darker = float((d > 0).mean())
    print(f"fraction of pixels where buggy is darker : {frac_darker:.1%}")
    print(f"PSNR(buggy vs correct) : {psnr(buggy, correct):.1f} dB   "
          f"SSIM : {ssim(buggy, correct):.3f}")
    hb, hc = luma_hist(buggy), luma_hist(correct)
    print("\nluma histogram shift (16 bins of 16 codes):")
    print(f"{'bin':>9s} {'buggy':>7s} {'correct':>8s}")
    for b in range(16):
        print(f"{b*16:3d}-{b*16+15:3d}  {hb[b]:7d} {hc[b]:8d}")
    print("\nWrite your one-paragraph diagnosis now, THEN run with --fix.")


def fix(orig, buggy, out: str) -> None:
    os.makedirs(out, exist_ok=True)
    correct = box_downscale_2x(orig, gamma_correct=True)
    naive = box_downscale_2x(orig, gamma_correct=False)   # == thumb_buggy, recomputed
    assert np.abs(naive.astype(int) - buggy.astype(int)).max() <= 1, \
        "recomputed naive downscale should match the shipped thumb_buggy.ppm (+/-1 rounding)"

    diff = np.clip(np.abs(correct.astype(int) - naive.astype(int)) * 4, 0, 255).astype(np.uint8)
    write_ppm(os.path.join(out, "relief_naive.ppm"), naive)
    write_ppm(os.path.join(out, "relief_linear.ppm"), correct)
    write_ppm(os.path.join(out, "relief_diff.ppm"), diff)

    d = np.abs(correct.astype(int) - naive.astype(int))
    print("== after fix (decode -> average -> encode) ==")
    print(f"root cause : the 2x2 mean was taken on sRGB codes, not linear light.")
    print(f"the fix    : one line -- srgb_to_linear() before .mean(), "
          f"linear_to_srgb() after.")
    print(f"mean abs difference : {d.mean():.1f} code levels")
    print(f"max  abs difference : {int(d.max())} code levels")
    print(f"PSNR(naive vs linear) : {psnr(naive, correct):.1f} dB")
    print(f"SSIM(naive vs linear) : {ssim(naive, correct):.3f}")
    print(f"wrote report images to {out}/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--out", default="report")
    args = ap.parse_args()
    orig, buggy = load_inputs()
    if args.fix:
        fix(orig, buggy, args.out)
    else:
        diagnose(orig, buggy)


if __name__ == "__main__":
    main()
