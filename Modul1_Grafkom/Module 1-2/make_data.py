"""Module 1 -- deterministic synthetic "heritage" image set.

Job: produce a fixed set of ~20 images with NO randomness (one optional
fixed-seed dither demo aside) and NO binary assets committed to Git. This is
this module's analog of a seeded generator (MASTER plan section 9.2). Your
graded input is your OWN building's photos; this set is the documented
fallback and the thing make test / the Case Study run against.

Writes to data/ :
  patch8.pgm            8x8 running example (Example E1) -- mean 54 by hand
  gradient.ppm          512x64 black->white ramp, 8-bit (Example E2a, 2 px bands)
  gradient5.pgm         512x64 same ramp quantised to 5-bit (Example E2b, 16 px)
  checker.pgm           256x256 2x2 black/white checker (gamma-blend demo)
  silhouette.pgm        256x256 Prambanan-style stepped-temple silhouette
  silhouette_flip.pgm   horizontal flip of the above
  relief.ppm            256x256 procedural sandstone relief (high-frequency)
  relief_rot90.ppm      relief rotated 90 deg
  crop_smooth.ppm       128x128 smooth sub-region (for format_compare)
  crop_hifreq.ppm       128x128 busy relief sub-region (for format_compare)
  thumb_buggy.ppm       128x128 -- relief downscaled 2x IN sRGB SPACE (the bug
                        artifact for gamma_resize_bug.py to diagnose)
  photo_00.ppm .. photo_09.ppm   relief with 10 different phases/tints
                        (stand-ins for 10 angle shots of one subject)
  manifest.csv          filename,width,height,channels,on_disk_bytes,note

Run:  python make_data.py            # writes everything to ./data
      python make_data.py --out X    # writes to ./X
"""
from __future__ import annotations

import argparse
import csv
import os

import numpy as np

from ppm_io import write_ppm
from srgb import srgb_to_linear, linear_to_srgb, to_u8


# ---- Example E1: the 8x8 running patch -----------------------------------
def running_patch() -> np.ndarray:
    """P[r,c] for the 8x8 patch. Block (i,j) base a_ij = 16*(i+j); the four
    pixels in a block add 0,4,8,12 (TL,TR,BL,BR)."""
    P = np.zeros((8, 8), dtype=np.uint8)
    offset = np.array([[0, 4], [8, 12]])          # dr,dc -> add
    for i in range(4):
        for j in range(4):
            a = 16 * (i + j)
            P[2 * i:2 * i + 2, 2 * j:2 * j + 2] = a + offset
    return P


def gradient(w=512, h=64) -> np.ndarray:
    ramp = np.round(np.linspace(0, 255, w)).astype(np.uint8)   # 0..255 inclusive
    g = np.repeat(ramp[None, :], h, axis=0)
    return np.dstack([g, g, g])


def quantise_bits(gray_rgb: np.ndarray, bits: int) -> np.ndarray:
    L = 2 ** bits
    f = gray_rgb[..., 0].astype(np.float64) / 255.0
    code = np.round(f * (L - 1))
    back = np.round(code / (L - 1) * 255).astype(np.uint8)
    return back


def checker(n=256, block=2) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n]
    c = ((xx // block + yy // block) % 2) * 255
    return c.astype(np.uint8)


def temple_silhouette(n=256) -> np.ndarray:
    """A stepped-pyramid (candi) outline: bright shape on a darker sky, pure
    geometry, deterministic."""
    img = np.full((n, n), 40, dtype=np.uint8)          # sky
    cx = n // 2
    # (top_y frac, bottom_y frac, half-width frac) for each stacked tier
    tiers = [(0.78, 0.92, 0.46), (0.64, 0.78, 0.40), (0.50, 0.64, 0.32),
             (0.36, 0.50, 0.24), (0.22, 0.36, 0.15), (0.10, 0.22, 0.07)]
    for ty, by, hw in tiers:
        y0, y1 = int(ty * n), int(by * n)
        w = int(hw * n)
        img[y0:y1, cx - w:cx + w] = 210
    img[int(0.04 * n):int(0.10 * n), cx - 6:cx + 6] = 230   # finial
    img[int(0.92 * n):, :] = 70                             # ground line
    return img


def relief(n=256, phase=0.0, tint=(1.00, 0.82, 0.60)) -> np.ndarray:
    """Procedural sandstone relief: near-periodic diagonal ridges + a slower
    modulation + two carved horizontal bands. Built in LINEAR light, tinted,
    then encoded to sRGB for storage (it is a 'photo')."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    fx = 0.37                                   # ~0.37 cycles/pixel -- high frequency
    # near-square-wave chisel ridges: strong local contrast in every 2x2 block
    raw = np.sin(2 * np.pi * fx * (x + 0.6 * y) + phase)
    ridges = 0.5 + 0.46 * np.tanh(3.0 * raw)
    fine = 0.06 * np.sin(2 * np.pi * 0.44 * (x - 0.3 * y))       # secondary detail
    slow = 0.10 * np.sin(2 * np.pi * 0.012 * x) * np.cos(2 * np.pi * 0.009 * y)
    lum = np.clip(ridges + fine + slow, 0.02, 0.99)
    # two carved bands: a step down in luminance
    lum[int(0.30 * n):int(0.34 * n), :] *= 0.55
    lum[int(0.66 * n):int(0.70 * n), :] *= 0.55
    lin = np.dstack([lum * tint[0], lum * tint[1], lum * tint[2]])
    return to_u8(linear_to_srgb(np.clip(lin, 0, 1)))


def box_downscale_2x_naive(img_u8: np.ndarray) -> np.ndarray:
    """THE BUG: average 2x2 blocks directly on sRGB codes (no decode)."""
    f = img_u8.astype(np.float64)
    h, w = f.shape[:2]
    f = f.reshape(h // 2, 2, w // 2, 2, -1).mean(axis=(1, 3))
    return np.round(f).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    p = lambda name: os.path.join(args.out, name)

    manifest: list[tuple] = []

    def emit(name, img, note):
        nbytes = write_ppm(p(name), img)
        h, w = img.shape[:2]
        ch = 1 if img.ndim == 2 else 3
        manifest.append((name, w, h, ch, nbytes, note))

    emit("patch8.pgm", running_patch(), "Example E1 running patch; mean 54 by hand")
    grad = gradient()
    emit("gradient.ppm", grad, "8-bit black->white ramp; 2 px bands (E2a)")
    emit("gradient5.pgm", quantise_bits(grad, 5), "5-bit ramp; 16 px bands (E2b)")
    emit("checker.pgm", checker(), "2x2 b/w checker; gamma-blend downscale demo")
    sil = temple_silhouette()
    emit("silhouette.pgm", sil, "stepped-temple silhouette; pure geometry")
    emit("silhouette_flip.pgm", sil[:, ::-1].copy(), "silhouette, horizontal flip")
    rel = relief()
    emit("relief.ppm", rel, "procedural sandstone relief; high-frequency ridges")
    emit("relief_rot90.ppm", np.rot90(rel).copy(), "relief rotated 90 deg")
    emit("crop_smooth.ppm", _smooth_crop(), "smooth sub-region for format_compare")
    emit("crop_hifreq.ppm", rel[64:192, 64:192].copy(), "busy relief crop for format_compare")
    emit("thumb_buggy.ppm", box_downscale_2x_naive(rel), "relief 2x downscaled IN sRGB SPACE (bug artifact)")

    tints = [(1.00, 0.82, 0.60), (0.98, 0.80, 0.58), (1.00, 0.85, 0.64),
             (0.95, 0.78, 0.55), (1.00, 0.80, 0.62), (0.97, 0.83, 0.60),
             (1.00, 0.79, 0.57), (0.96, 0.81, 0.61), (1.00, 0.84, 0.63),
             (0.99, 0.80, 0.59)]
    for k in range(10):
        emit(f"photo_{k:02d}.ppm", relief(phase=k * 0.7, tint=tints[k]),
             f"stand-in angle shot {k} of one subject")

    with open(p("manifest.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["filename", "width", "height", "channels", "on_disk_bytes", "note"])
        wr.writerows(manifest)

    total = sum(m[4] for m in manifest)
    print(f"wrote {len(manifest)} images + manifest.csv to {args.out}/  "
          f"({total} bytes on disk)")


def _smooth_crop() -> np.ndarray:
    """A genuinely smooth 118x118 RGB region: a gentle radial gradient."""
    n = 118
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    r = np.sqrt((x - n / 2) ** 2 + (y - n / 2) ** 2) / (n / 2)
    lum = np.clip(0.85 - 0.5 * r, 0.05, 0.95)
    lin = np.dstack([lum * 0.95, lum * 0.90, lum * 1.00])
    return to_u8(linear_to_srgb(np.clip(lin, 0, 1)))


if __name__ == "__main__":
    main()
