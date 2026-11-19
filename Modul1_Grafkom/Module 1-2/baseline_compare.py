"""Module 1 -- Lab 3.2 baseline: whose 2x downscale matches "correct"?

Reference = OUR gamma-correct box downscale (resample.box_downscale_2x,
gamma_correct=True). Compared against it:
  (a) our naive sRGB-space box downscale           (the bug, on purpose)
  (b) Pillow  img.resize((w/2,h/2), Image.BOX)      (library default)
  (c) Pillow  img.reduce(2)                         (library 'fast box')
  (d) Pillow BOX run per channel in mode "F" on LINEAR values that we decode
      ourselves, then re-encode                      (library + our colour mgmt)

PSNR / global SSIM from metrics.py. Run on relief.ppm (high-frequency) and
checker.pgm (the E4 black/white case).

Run:  python baseline_compare.py [--out report/]
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from metrics import psnr, ssim
from ppm_io import read_ppm
from resample import box_downscale_2x
from srgb import srgb_to_linear, linear_to_srgb, to_float, to_u8


def _pillow_variants(img: np.ndarray) -> dict:
    try:
        from PIL import Image
    except ImportError:
        return {}
    h, w = img.shape[:2]
    mode = "L" if img.ndim == 2 else "RGB"
    pim = Image.fromarray(img, mode)
    out = {
        "Pillow resize(BOX)": np.asarray(pim.resize((w // 2, h // 2), Image.BOX)),
        "Pillow reduce(2)": np.asarray(pim.reduce(2)),
    }
    lin = srgb_to_linear(to_float(img))
    chans = [lin] if img.ndim == 2 else [lin[..., k] for k in range(3)]
    res = [np.asarray(Image.fromarray(c.astype(np.float32), "F")
                      .resize((w // 2, h // 2), Image.BOX), dtype=np.float64) for c in chans]
    lin_small = res[0] if img.ndim == 2 else np.dstack(res)
    out["Pillow BOX on linear (F)"] = to_u8(linear_to_srgb(lin_small))
    return out


def checker1(n: int = 64) -> np.ndarray:
    """1-px black/white checker: every 2x2 block is exactly two 0s and two 255s
    (Example E4). data/checker.pgm uses 2-px squares, which line up with the
    2x grid so each block is uniform and NO method can go wrong -- a phase
    lesson in itself, reported alongside."""
    yy, xx = np.mgrid[0:n, 0:n]
    return (((xx + yy) % 2) * 255).astype(np.uint8)


def compare(path) -> list[tuple]:
    img = checker1() if path == "checker1" else read_ppm(path)
    ref = box_downscale_2x(img if img.ndim == 3 else img[..., None].repeat(3, 2), True)
    if img.ndim == 2:
        ref = ref[..., 0]
    cands = {"ours naive (sRGB codes)": box_downscale_2x(img, False) if img.ndim == 3
             else box_downscale_2x(img[..., None].repeat(3, 2), False)[..., 0]}
    cands.update(_pillow_variants(img))
    rows = []
    for name, im in cands.items():
        d = np.abs(im.astype(int) - ref.astype(int))
        rows.append((name, psnr(im, ref), ssim(im, ref), float(d.mean()), int(d.max()),
                     float(im.mean() - ref.mean())))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    md = ["# Baseline: 2x downscale vs our linear-correct reference\n"]
    for path in ("data/relief.ppm", "checker1", "data/checker.pgm"):
        rows = compare(path)
        print(f"\n{path if path == 'checker1' else os.path.basename(path)}  (reference = ours, linear-light box)")
        print(f"{'candidate':28s} {'PSNR':>9s} {'SSIM':>7s} {'mean|d|':>8s} {'max|d|':>7s} {'bias':>7s}")
        md.append(f"\n## {'1-px checker (E4)' if path == 'checker1' else os.path.basename(path)}\n\n| candidate | PSNR vs ref | SSIM | mean abs diff | max abs diff | mean bias |\n|---|---|---|---|---|---|")
        for n, p, s, m, mx, b in rows:
            ptxt = "inf" if p == float("inf") else f"{p:.1f} dB"
            print(f"{n:28s} {ptxt:>9s} {s:7.3f} {m:8.2f} {mx:7d} {b:+7.2f}")
            md.append(f"| {n} | {ptxt} | {s:.3f} | {m:.2f} | {mx} | {b:+.2f} |")
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "baseline.md"), "w") as f:
            f.write("\n".join(md) + "\n")
        print(f"\nwrote {os.path.join(args.out, 'baseline.md')}")


if __name__ == "__main__":
    main()
