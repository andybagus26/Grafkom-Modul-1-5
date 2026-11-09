"""Module 1 -- RGB -> grayscale, done correctly (NumPy only).

Correct recipe:  decode sRGB -> linear ; Rec.709 weights ; encode -> sRGB.

Reproduces: Example E5 -- for RGB (200,100,50):
  correct (gamma-2 hand version) ~= 126
  naive Rec.709 weighted sum on codes ~= 118
  plain average ~= 117

Run:
  python luma.py --selftest
  python luma.py --image data/relief.ppm --out report/relief_grey.pgm
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from ppm_io import read_ppm, write_ppm
from srgb import (srgb_to_linear, linear_to_srgb, srgb_to_linear_g2,
                  linear_to_srgb_g2, to_float, to_u8)

REC709 = np.array([0.2126, 0.7152, 0.0722])
REC601 = np.array([0.299, 0.587, 0.114])


def rgb_to_grey(img_u8: np.ndarray, approx: bool = False) -> np.ndarray:
    """Correct luminance grey. approx=True uses the gamma-2 curve (hand math);
    approx=False uses the real sRGB curve (ship this)."""
    f = to_float(img_u8)
    dec = srgb_to_linear_g2 if approx else srgb_to_linear
    enc = linear_to_srgb_g2 if approx else linear_to_srgb
    lin = dec(f)
    y = lin @ REC709
    return to_u8(enc(y))


def rgb_to_grey_naive_weights(img_u8: np.ndarray) -> np.ndarray:
    """The common bug: Rec.709 weights applied straight to sRGB codes."""
    return np.round(to_float(img_u8) @ REC709 * 255).clip(0, 255).astype(np.uint8)


def rgb_to_grey_average(img_u8: np.ndarray) -> np.ndarray:
    return np.round(img_u8.astype(np.float64).mean(axis=2)).clip(0, 255).astype(np.uint8)


def _selftest() -> None:
    px = np.array([[[200, 100, 50]]], dtype=np.uint8)
    correct = int(rgb_to_grey(px, approx=True)[0, 0])
    naive_w = int(rgb_to_grey_naive_weights(px)[0, 0])
    avg = int(rgb_to_grey_average(px)[0, 0])
    assert 124 <= correct <= 128, f"E5 correct grey {correct} not ~126"
    assert 116 <= naive_w <= 120, f"E5 naive-weights grey {naive_w} not ~118"
    assert avg == 117, f"E5 average {avg} != 117"

    # a flat grey must map to (about) itself
    g = np.full((4, 4, 3), 128, dtype=np.uint8)
    out = int(rgb_to_grey(g)[0, 0])
    assert abs(out - 128) <= 1, f"grey of flat 128 -> {out}"
    print(f"luma self-test OK  (E5: correct~{correct}, naive-weights~{naive_w}, "
          f"avg={avg}; flat 128 -> {out})")


def _cross_check_pillow(path: str) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed -- skipping cross-check")
        return
    img = read_ppm(path)
    mine = rgb_to_grey(img)                       # real sRGB curve
    ref = np.asarray(Image.fromarray(img).convert("L"))
    # Pillow's "L" uses Rec.601 luma on GAMMA values -> expect a systematic gap
    d = np.abs(mine.astype(int) - ref.astype(int))
    print(f"vs Pillow convert('L'): mean |diff| = {d.mean():.2f}, "
          f"max = {int(d.max())}  (gap is expected: Pillow = Rec.601 luma in "
          f"gamma space; ours = correct linear-light luminance)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cross-check", action="store_true")
    args = ap.parse_args()
    if args.selftest or not args.image:
        _selftest()
        return
    img = read_ppm(args.image)
    grey = rgb_to_grey(img)
    if args.out:
        write_ppm(args.out, grey)
        print(f"wrote {args.out}")
    if args.cross_check:
        _cross_check_pillow(args.image)


if __name__ == "__main__":
    main()
