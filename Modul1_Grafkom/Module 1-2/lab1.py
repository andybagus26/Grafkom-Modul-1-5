"""Module 1 -- Lab 1: toolchain record, input manifest, budget, decode vs on-disk.

  1. Toolchain : OS, Python, NumPy, Pillow (+ WebP/AVIF support), date
                 -> report/toolchain.md
  2. Input     : if photos/ holds your own JPG/PNG/HEIC shots, they are
                 listed in photos/manifest.csv (filename, W, H, on-disk bytes,
                 format, note). Pillow is used ONLY to read the header size.
                 If photos/ is empty the documented fallback is `make data`
                 (data/manifest.csv) and the report SAYS SO.
  3. Budget    : for the real resolution (your photos, or the assumed 12 MP
                 4000x3000 phone camera when using the fallback): bytes per
                 decoded RGB888 image, working set of a 15-image set in MiB,
                 and a hypothetical 10 s @ 30 fps uncompressed flythrough
                 (GB + GiB, MB/s + Mbit/s).
  4. Decode vs on-disk : for 3 images, compressed size vs decoded array.
                 Fallback: the synthetic images are stored as raw PPM (ratio
                 1.00x), so we encode them as JPEG q92 -- what a phone camera
                 writes -- and measure that (Pillow = the codec under test).

Run:  python lab1.py            # writes report/toolchain.md + report/lab1.md
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import io
import os
import platform
import sys

import numpy as np

import budget as B
from ppm_io import read_ppm

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff")
FALLBACK_W, FALLBACK_H, N_SET = 4000, 3000, 15


def toolchain() -> dict:
    info = {"date": dt.date.today().isoformat(),
            "os": f"{platform.system()} {platform.mac_ver()[0] or platform.release()} "
                  f"({platform.machine()})",
            "python": sys.version.split()[0], "numpy": np.__version__}
    try:
        import PIL
        from PIL import features
        info.update(pillow=PIL.__version__, webp=bool(features.check("webp")),
                    avif=bool(features.check("avif")))
    except ImportError:
        info.update(pillow="not installed", webp=False, avif=False)
    return info


def own_photos(folder: str = "photos") -> list[dict]:
    files = sorted(f for f in glob.glob(os.path.join(folder, "*"))
                   if f.lower().endswith(PHOTO_EXT))
    if not files:
        return []
    from PIL import Image
    rows = []
    for f in files:
        with Image.open(f) as im:
            w, h = im.size
            fmt = im.format
        rows.append(dict(filename=os.path.basename(f), width=w, height=h,
                         on_disk_bytes=os.path.getsize(f), format=fmt, note=""))
    notes = os.path.join(folder, "notes.csv")         # optional: filename,note
    if os.path.exists(notes):
        nmap = {r[0]: r[1] for r in csv.reader(open(notes)) if len(r) >= 2}
        for r in rows:
            r["note"] = nmap.get(r["filename"], "")
    with open(os.path.join(folder, "manifest.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    return rows


def jpeg_bytes(img: np.ndarray, q: int = 92) -> int | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=q)
    return len(buf.getvalue())


def main() -> None:
    os.makedirs("report", exist_ok=True)
    tc = toolchain()
    with open("report/toolchain.md", "w") as f:
        f.write("# Toolchain (Lab 1.1)\n\n| item | value |\n|---|---|\n")
        for k, v in tc.items():
            f.write(f"| {k} | {v} |\n")
    print("toolchain:", tc)

    photos = own_photos()
    out = ["# Lab 1 -- input, budget, decode vs on-disk\n"]
    if photos:
        w, h = photos[0]["width"], photos[0]["height"]
        n = len(photos)
        out.append(f"Input: **{n} own photos** in `photos/` (see `photos/manifest.csv`).\n")
    else:
        w, h, n = FALLBACK_W, FALLBACK_H, N_SET
        out.append("Input: **no own photos were available -> fallback `make data`** "
                   "(21 deterministic synthetic images, `data/manifest.csv`). The budget "
                   f"below assumes a typical 12 MP phone camera ({w}x{h}) and a "
                   f"{n}-image capture set, the Lab 1 minimum.\n")

    bpi = B.bytes_per_frame(w, h, 24)
    ws = bpi * n
    clip = bpi * 30 * 10
    bw = bpi * 30
    lines = [
        f"bytes / decoded image (RGB888) = {w} x {h} x 3 = {bpi:,} B "
        f"= {bpi / B.MB:.2f} MB (10^6) = {bpi / B.MiB:.2f} MiB (2^20)",
        f"working set, {n} images         = {ws:,} B = {ws / B.MiB:.1f} MiB (2^20)",
        f"flythrough 10 s @ 30 fps        = {clip:,} B = {clip / B.GB:.2f} GB (10^9) "
        f"= {clip / B.GiB:.2f} GiB (2^30)",
        f"bandwidth                       = {bw:,} B/s = {bw / B.MB:.1f} MB/s "
        f"= {bw * 8 / B.MB:.1f} Mbit/s (10^6)",
    ]
    out += ["## Budget at the real resolution\n", "```", *lines, "```\n"]
    print("\n".join(lines))

    out.append("## Decode vs on-disk (3 images)\n")
    out.append("| image | content | decoded B | on-disk B | format | effective ratio |\n|---|---|---|---|---|---|")
    if photos:
        for r in photos[:3]:
            dec = r["width"] * r["height"] * 3
            out.append(f"| {r['filename']} | {r['note']} | {dec:,} | {r['on_disk_bytes']:,} | "
                       f"{r['format']} | {dec / r['on_disk_bytes']:.1f}x |")
    else:
        for name, what in (("crop_smooth.ppm", "plain sky-like gradient"),
                           ("silhouette.pgm", "flat temple silhouette"),
                           ("relief.ppm", "busy carved relief (foliage-like)")):
            img = read_ppm(os.path.join("data", name))
            if img.ndim == 2:
                img = np.dstack([img] * 3)
            dec = img.size
            disk_ppm = os.path.getsize(os.path.join("data", name))
            jb = jpeg_bytes(img)
            out.append(f"| {name} (PPM as stored) | {what} | {dec:,} | {disk_ppm:,} | "
                       f"raw PPM | {dec / disk_ppm:.2f}x |")
            if jb:
                out.append(f"| {name} -> JPEG q92 | {what} | {dec:,} | {jb:,} | "
                           f"JPEG (camera-like) | {dec / jb:.1f}x |")
                print(f"{name:16s} decoded {dec:7,} B   JPEG q92 {jb:6,} B   ratio {dec / jb:5.1f}x")
    with open("report/lab1.md", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote report/toolchain.md and report/lab1.md")


if __name__ == "__main__":
    main()
