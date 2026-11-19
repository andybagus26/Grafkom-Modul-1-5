"""Module 1 -- JPG / PNG / WebP / AVIF size + artefact comparison.

This is the "decision defended with a prediction" task (MASTER plan 3.2.4):
you WRITE your expected ordering first (Example E8), then run this and
reconcile.

Pillow IS used here -- it is the codec under test, not a from-scratch
substitute. Formats Pillow cannot encode on this machine are SKIPPED with a
note (never counted as zero).

Reproduces: Fully Worked Example Step 5 -- a table of bytes / ratio / PSNR for
the relief crop. Exact bytes depend on the installed codec versions; the
ORDER (PNG/WebP-lossless > JPG q92 > JPG q40) and the PSNR trend are the
lesson.

Run:
  python format_compare.py --image data/crop_hifreq.ppm --out report/
  python format_compare.py --image data/crop_smooth.ppm --out report/
"""
from __future__ import annotations

import argparse
import io
import os

import numpy as np

from ppm_io import read_ppm
from metrics import psnr


def _encode(img: np.ndarray, fmt: str, **kw):
    """Return (nbytes, decoded_back) or (None, None) if the codec is missing."""
    try:
        from PIL import Image
    except ImportError:
        return None, None
    try:
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format=fmt, **kw)
        data = buf.getvalue()
        back = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
        return len(data), back
    except (KeyError, OSError, ValueError):
        return None, None


CASES = [
    ("PNG",  "PNG",  dict(optimize=True)),
    ("WebP-lossless", "WEBP", dict(lossless=True)),
    ("JPG q92", "JPEG", dict(quality=92)),
    ("WebP q92", "WEBP", dict(quality=92)),
    ("JPG q75", "JPEG", dict(quality=75)),
    ("WebP q75", "WEBP", dict(quality=75)),
    ("JPG q60", "JPEG", dict(quality=60)),
    ("JPG q40", "JPEG", dict(quality=40)),
    ("AVIF q75", "AVIF", dict(quality=75)),
    ("AVIF q40", "AVIF", dict(quality=40)),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", default="report")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    img = read_ppm(args.image)
    if img.ndim == 2:
        img = np.dstack([img, img, img])
    decoded_bytes = img.size
    print(f"image {os.path.basename(args.image)}  {img.shape[1]}x{img.shape[0]}  "
          f"decoded = {decoded_bytes:,} bytes\n")
    print(f"{'format':16s} {'bytes':>10s} {'ratio':>8s} {'PSNR vs original':>18s}")
    rows = []
    for label, fmt, kw in CASES:
        n, back = _encode(img, fmt, **kw)
        if n is None:
            print(f"{label:16s} {'--':>10s} {'--':>8s} {'(codec not available)':>18s}")
            continue
        p = psnr(img, back) if back is not None and back.shape == img.shape else float("nan")
        ptxt = "inf" if p == float("inf") else f"{p:.1f} dB"
        print(f"{label:16s} {n:>10,} {decoded_bytes / n:>7.2f}x {ptxt:>18s}")
        rows.append((label, n, decoded_bytes / n, p))
        if label == "JPG q40":          # keep the decoded q40 so the report can SHOW the ringing
            from ppm_io import write_ppm
            stem = os.path.splitext(os.path.basename(args.image))[0]
            write_ppm(os.path.join(args.out, f"{stem}_jpg_q40.ppm"), back.astype(np.uint8))

    md = os.path.join(args.out, f"formats_{os.path.splitext(os.path.basename(args.image))[0]}.md")
    with open(md, "w") as f:
        f.write(f"# Format comparison -- {os.path.basename(args.image)}\n\n")
        f.write(f"decoded original = {decoded_bytes:,} bytes\n\n")
        f.write("| format | bytes | ratio | PSNR vs original |\n|---|---|---|---|\n")
        for label, n, r, p in rows:
            ptxt = "inf" if p == float("inf") else (f"{p:.1f} dB" if p == p else "n/a")
            f.write(f"| {label} | {n:,} | {r:.2f}x | {ptxt} |\n")
    print(f"\nwrote {md}")


if __name__ == "__main__":
    main()
